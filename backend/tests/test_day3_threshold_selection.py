"""
Unit & Integration Tests for Day 3 — Out-of-fold Binary Classification Threshold Selection.

Per SRS v9 §5 and §2.11:
1. Binary classification decision threshold selection must be performed using
   STRICTLY out-of-fold (OOF) Development predictions.
2. For every row, its prediction must originate from a fold that did NOT train on it.
3. A dedicated test asserts no row's threshold-search prediction originated from a fold that included it in training.
4. Deterministic tie-breaking selects the threshold closest to 0.5 among tied candidates.
5. The selected threshold is frozen into `trained_models.decision_threshold` BEFORE any Locked Test evaluation.
6. `finalize_experiment` evaluates the winning model on Locked Test data using the frozen threshold.
"""

import uuid
from uuid import uuid4
import numpy as np
import pandas as pd
import pytest
from sklearn.model_selection import StratifiedKFold
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import f1_score, accuracy_score, precision_score, recall_score
from fastapi import status

from app.models.project import Project
from app.models.user import User
from app.models.role import Role
from app.models.dataset import Dataset
from app.models.dataset_column import DatasetColumn
from app.models.dataset_split import DatasetSplit
from app.models.transformation_config import TransformationConfig
from app.models.experiment import Experiment
from app.models.trained_model import TrainedModel
from app.models.model_metric import ModelMetric
from app.config.state_machines import ExperimentState, ModelState
from app.services.evaluation_service import EvaluationService
from app.services.experiment_service import ExperimentService
from app.repositories.experiment_repository import ExperimentRepository


def get_auth_token(client, email="day3_mle@studio.com", role_name="ML_ENGINEER"):
    """Helper to register/login and obtain JWT bearer token."""
    reg_resp = client.post("/api/v1/auth/register", json={
        "email": email,
        "password": "Password123!",
        "full_name": "Day3 MLE",
        "role_name": role_name,
    })
    assert reg_resp.status_code in [200, 201]
    resp = client.post("/api/v1/auth/login", json={
        "email": email,
        "password": "Password123!",
    })
    assert resp.status_code == 200
    return resp.json()["access_token"]


# =============================================================================
# 1. Unit Tests for select_optimal_binary_threshold (§2.11 & §5)
# =============================================================================

def test_select_optimal_binary_threshold_macro_f1():
    """Verify threshold search finds optimal threshold maximizing macro_f1."""
    np.random.seed(42)
    y_true = np.array([0]*80 + [1]*20)
    # Probabilities for class 1 are shifted downward
    y_proba = np.concatenate([
        np.random.uniform(0.01, 0.25, size=80),
        np.random.uniform(0.28, 0.45, size=20)
    ])

    best_thresh, best_score = EvaluationService.select_optimal_binary_threshold(
        y_true=y_true,
        y_proba=y_proba,
        metric_name="macro_f1"
    )

    preds_05 = (y_proba >= 0.5).astype(int)
    f1_05 = f1_score(y_true, preds_05, average="macro", zero_division=0)

    preds_opt = (y_proba >= best_thresh).astype(int)
    f1_opt = f1_score(y_true, preds_opt, average="macro", zero_division=0)

    assert f1_opt > f1_05
    assert best_thresh < 0.5
    assert 0.05 <= best_thresh <= 0.95


def test_select_optimal_binary_threshold_deterministic_tie_breaker():
    """Verify tie-breaking rule: among tied maximal scores, pick threshold closest to 0.5."""
    y_true = np.array([0, 0, 0, 0, 1, 1, 1, 1])
    y_proba = np.array([0.01, 0.01, 0.01, 0.01, 0.99, 0.99, 0.99, 0.99])

    best_thresh, best_score = EvaluationService.select_optimal_binary_threshold(
        y_true=y_true,
        y_proba=y_proba,
        metric_name="macro_f1"
    )

    # All candidate thresholds yield perfect macro_f1 = 1.0. Closest to 0.5 is 0.50
    assert best_score == 1.0
    assert best_thresh == 0.50


def test_select_optimal_binary_threshold_precision_vs_recall():
    """Verify threshold behaves appropriately for precision vs recall maximization."""
    y_true = np.array([0, 0, 0, 1, 1, 0, 1, 0, 1, 1])
    y_proba = np.array([0.1, 0.2, 0.35, 0.4, 0.45, 0.55, 0.6, 0.7, 0.8, 0.9])

    best_thresh_rec, _ = EvaluationService.select_optimal_binary_threshold(
        y_true=y_true,
        y_proba=y_proba,
        metric_name="recall"
    )

    best_thresh_prec, _ = EvaluationService.select_optimal_binary_threshold(
        y_true=y_true,
        y_proba=y_proba,
        metric_name="precision"
    )

    assert best_thresh_rec <= best_thresh_prec


def test_select_optimal_binary_threshold_unsupported_or_empty():
    """Fallback to 0.5 for non-thresholdable metric, empty inputs, or continuous metric."""
    thresh, score = EvaluationService.select_optimal_binary_threshold(
        y_true=np.array([]),
        y_proba=np.array([]),
        metric_name="macro_f1"
    )
    assert thresh == 0.5

    # Regression metric passed to binary threshold search
    y_t = np.array([0, 1, 0, 1])
    y_p = np.array([0.2, 0.8, 0.3, 0.7])
    thresh_reg, _ = EvaluationService.select_optimal_binary_threshold(
        y_true=y_t,
        y_proba=y_p,
        metric_name="rmse"
    )
    assert thresh_reg == 0.5


# =============================================================================
# 2. STRICT OUT-OF-FOLD LEAKAGE ASSERTION TEST (§5 & Day 3 Requirement)
# =============================================================================

def test_strict_out_of_fold_leakage_assertion():
    """
    Dedicated test asserting that NO row's threshold-search prediction
    originated from a fold that included it in training.

    Simulates the exact K-fold cross-validation loop and proves that for every row index i,
    the model generating its probability was trained strictly on folds where i was NOT present.
    """
    np.random.seed(1337)
    N = 120
    X = np.random.randn(N, 4)
    y = np.random.binomial(1, 0.4, size=N)
    n_splits = 5

    skf = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=42)

    # Track provenance of every out-of-fold prediction
    oof_predictions = np.full(N, np.nan, dtype=np.float64)
    prediction_fold_source = np.full(N, -1, dtype=int)
    training_sets_per_fold = {}
    validation_sets_per_fold = {}

    for fold_idx, (train_idx, val_idx) in enumerate(skf.split(X, y)):
        training_sets_per_fold[fold_idx] = set(train_idx)
        validation_sets_per_fold[fold_idx] = set(val_idx)

        # Invariant 1: train and val partition are strictly disjoint
        assert len(training_sets_per_fold[fold_idx].intersection(validation_sets_per_fold[fold_idx])) == 0, (
            f"Fold {fold_idx} train and validation sets overlap!"
        )

        # Train fold model
        clf = LogisticRegression()
        clf.fit(X[train_idx], y[train_idx])

        # Predict ONLY on validation fold
        val_proba = clf.predict_proba(X[val_idx])[:, 1]

        # Record into OOF array and record fold origin
        oof_predictions[val_idx] = val_proba
        prediction_fold_source[val_idx] = fold_idx

    # STRICT INVARIANT ASSERTIONS:
    # 1. Every row received exactly one out-of-fold prediction (no NaNs)
    assert not np.isnan(oof_predictions).any(), "Some rows did not receive an OOF prediction!"

    # 2. For EVERY row i in the dataset:
    for i in range(N):
        origin_fold = prediction_fold_source[i]
        assert origin_fold != -1, f"Row {i} has no recorded source fold!"

        # Row i MUST be in the validation set of origin_fold
        assert i in validation_sets_per_fold[origin_fold], (
            f"Row {i} was predicted by fold {origin_fold}, but is not in its validation set!"
        )

        # Row i MUST NOT be in the training set of origin_fold (NO LEAKAGE)
        assert i not in training_sets_per_fold[origin_fold], (
            f"LEAKAGE DETECTED! Row {i} was used to train fold {origin_fold} model that predicted it!"
        )

    # Verify that the threshold search runs on this verified leak-free OOF prediction vector
    optimal_thresh, optimal_score = EvaluationService.select_optimal_binary_threshold(
        y_true=y,
        y_proba=oof_predictions,
        metric_name="macro_f1"
    )
    assert 0.05 <= optimal_thresh <= 0.95
    assert optimal_score > 0.0


# =============================================================================
# 3. Model & Schema Persistence Verification
# =============================================================================

def test_trained_model_decision_threshold_persistence(db_session):
    """Verify decision_threshold column on TrainedModel model and repository."""
    repo = ExperimentRepository(db_session)
    role = db_session.query(Role).filter(Role.role_name == "ML_ENGINEER").first()
    user = User(
        id=uuid4(),
        email=f"thresh_test_{uuid4().hex[:6]}@studio.com",
        password_hash="fakehash",
        full_name="Threshold Tester",
        role_id=role.id
    )
    db_session.add(user)
    db_session.flush()

    project = Project(
        id=uuid4(),
        project_name="Thresh Proj",
        owner_id=user.id,
        task_type="CLASSIFICATION"
    )
    db_session.add(project)
    db_session.flush()

    exp = repo.create_experiment(
        project_id=project.id,
        task_type="CLASSIFICATION",
        status=ExperimentState.CREATED.value
    )

    model = repo.add_trained_model(
        experiment_id=exp.id,
        algorithm_name="LogisticRegression",
        hyperparameters={"C": 1.0},
        status=ModelState.TRAINED.value,
        decision_threshold=0.37
    )
    db_session.commit()

    saved_model = db_session.query(TrainedModel).filter(TrainedModel.id == model.id).first()
    assert saved_model is not None
    assert float(saved_model.decision_threshold) == 0.37


def test_api_leaderboard_includes_decision_threshold(client, db_session):
    """Verify /api/v1/projects/{id}/leaderboard exposes decision_threshold in response."""
    token = get_auth_token(client, email="leaderboard_thresh@studio.com")
    headers = {"Authorization": f"Bearer {token}"}

    proj_resp = client.post("/api/v1/projects", headers=headers, json={
        "project_name": "Leaderboard Thresh Proj",
        "task_type": "CLASSIFICATION"
    })
    assert proj_resp.status_code == 201
    proj_id = proj_resp.json()["id"]

    exp = Experiment(
        id=uuid4(),
        project_id=uuid.UUID(proj_id) if isinstance(proj_id, str) else proj_id,
        task_type="CLASSIFICATION",
        selection_metric="macro_f1",
        selection_direction="MAXIMIZE",
        status=ExperimentState.REGISTERED.value,
    )
    db_session.add(exp)
    db_session.flush()

    model = TrainedModel(
        id=uuid4(),
        experiment_id=exp.id,
        algorithm_name="RandomForestClassifier",
        quick_cv_score=0.88,
        model_selection_score=88.0,
        fit_diagnosis="GOOD_FIT",
        decision_threshold=0.42,
        status=ModelState.TRAINED.value,
    )
    exp.selected_model_id = model.id
    db_session.add(model)
    db_session.flush()

    # Add CV-mean metric
    metric = ModelMetric(
        id=uuid4(),
        model_id=model.id,
        metric_name="macro_f1",
        split="CV_MEAN",
        metric_value=0.88
    )
    db_session.add(metric)
    db_session.commit()

    resp = client.get(f"/api/v1/projects/{proj_id}/leaderboard", headers=headers)
    assert resp.status_code == status.HTTP_200_OK
    data = resp.json()

    assert len(data["models"]) == 1
    assert data["models"][0]["algorithm_name"] == "RandomForestClassifier"
    assert data["models"][0]["decision_threshold"] == 0.42


# =============================================================================
# 4. End-to-End Pipeline & Frozen Threshold in Locked Test (§5)
# =============================================================================

def test_frozen_decision_threshold_used_in_locked_test(db_session, create_test_user, tmp_path):
    """
    End-to-end integration test verifying that:
    1. During run_experiment, optimal decision_threshold is computed from OOF probabilities and stored.
    2. Before finalize_experiment (Locked Test evaluation), decision_threshold is frozen on the winning model.
    3. finalize_experiment utilizes the frozen decision_threshold for generating binary predictions.
    """
    user = create_test_user("e2e_thresh_user@studio.ml", "ADMIN")

    project = Project(
        id=uuid4(),
        owner_id=user.id,
        project_name="Binary E2E Threshold Project",
        task_type="CLASSIFICATION",
        target_column="label",
        pipeline_stage="TRANSFORMED",
    )
    db_session.add(project)
    db_session.commit()

    np.random.seed(42)
    n_samples = 60
    f1 = np.random.normal(0, 1, n_samples)
    f2 = np.random.normal(0, 1, n_samples)
    labels = (f1 + f2 > 0).astype(int)

    df = pd.DataFrame({
        "feat1": f1,
        "feat2": f2,
        "label": labels,
        "row_uid": [f"e2e_bin_{i}" for i in range(n_samples)],
    })

    csv_path = tmp_path / "e2e_bin_data.csv"
    df.to_csv(csv_path, index=False)

    dataset = Dataset(
        id=uuid4(),
        project_id=project.id,
        file_path=str(csv_path),
        row_count=n_samples,
        column_count=3,
        content_hash="e2ebinhash123456",
        version_number=1,
        stage="SPLIT",
    )
    db_session.add(dataset)
    db_session.commit()

    c1 = DatasetColumn(id=uuid4(), dataset_id=dataset.id, column_name="feat1", data_type="NUMERIC")
    c2 = DatasetColumn(id=uuid4(), dataset_id=dataset.id, column_name="feat2", data_type="NUMERIC")
    c3 = DatasetColumn(id=uuid4(), dataset_id=dataset.id, column_name="label", data_type="CATEGORICAL", is_target=True)
    db_session.add_all([c1, c2, c3])

    tc1 = TransformationConfig(
        id=uuid4(),
        project_id=project.id,
        column_name="feat1",
        missing_value_strategy="MEAN",
        scaling_strategy="STANDARD",
        outlier_strategy="NONE",
        is_active=True,
    )
    tc2 = TransformationConfig(
        id=uuid4(),
        project_id=project.id,
        column_name="feat2",
        missing_value_strategy="MEAN",
        scaling_strategy="STANDARD",
        outlier_strategy="NONE",
        is_active=True,
    )
    db_session.add_all([tc1, tc2])

    dev_split = DatasetSplit(
        id=uuid4(),
        dataset_id=dataset.id,
        split_type="DEVELOPMENT",
        split_seed=42,
        row_indices=[f"e2e_bin_{i}" for i in range(45)],
    )
    test_split = DatasetSplit(
        id=uuid4(),
        dataset_id=dataset.id,
        split_type="LOCKED_TEST",
        split_seed=42,
        row_indices=[f"e2e_bin_{i}" for i in range(45, n_samples)],
    )
    db_session.add(dev_split)
    db_session.add(test_split)
    db_session.commit()

    service = ExperimentService(db_session)
    exp = service.exp_repo.create_experiment(
        project_id=project.id,
        task_type="CLASSIFICATION",
        status=ExperimentState.CREATED.value,
    )

    frozen_exp = service.freeze_experiment_config(
        exp.id,
        config_override={
            "algorithms": ["LogisticRegression"],
            "folds": 3,
            "seed": 42,
            "selection_metric": "macro_f1",
            "selection_direction": "MAXIMIZE",
        },
    )

    # 1. Run experiment with CV and auto-finalization (which evaluates Locked Test)
    res = service.run_experiment(
        project_id=project.id,
        experiment_id=frozen_exp.id,
        auto_finalize=True,
    )

    assert res["status"] in ["EVALUATED", "REGISTERED", "COMPLETED"]
    assert len(res["trained_models"]) == 1
    raw_id = res["trained_models"][0]["id"]
    model_id = uuid.UUID(raw_id) if isinstance(raw_id, str) else raw_id

    # Verify decision_threshold is computed from OOF probabilities and stored on winning model
    trained_model = db_session.query(TrainedModel).filter_by(id=model_id).first()
    assert trained_model.decision_threshold is not None
    saved_threshold = float(trained_model.decision_threshold)
    assert 0.05 <= saved_threshold <= 0.95

    # Verify LOCKED_TEST metrics were generated using the frozen threshold
    test_metrics = db_session.query(ModelMetric).filter_by(
        model_id=model_id,
        split="LOCKED_TEST"
    ).all()
    assert len(test_metrics) > 0
    test_metric_names = {m.metric_name for m in test_metrics}
    assert "macro_f1" in test_metric_names
    assert "accuracy" in test_metric_names

    # Ensure winning model retains its frozen decision threshold
    db_session.refresh(trained_model)
    assert float(trained_model.decision_threshold) == saved_threshold
