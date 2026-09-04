import io
import uuid
from unittest.mock import patch, MagicMock
import pytest
import numpy as np
import pandas as pd
from fastapi import status, HTTPException

from app.models.dataset import Dataset
from app.models.dataset_split import DatasetSplit
from app.models.experiment import Experiment
from app.models.trained_model import TrainedModel
from app.models.model_metric import ModelMetric
from app.models.project import Project
from app.models.user import User
from app.models.role import Role
from app.services.dataset_service import DatasetService
from app.services.dataset_split_service import DatasetSplitService
from app.services.transformation_service import TransformationService
from app.services.experiment_service import ExperimentService
from app.services.evaluation_service import EvaluationService
from app.services.trainers import RegressionTrainer, ClassificationTrainer

def get_auth_token(client, email="engineer_d7@example.com", role_name="ML_ENGINEER"):
    reg_resp = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Test User D7",
            "email": email,
            "password": "password123",
            "role_name": role_name,
        },
    )
    assert reg_resp.status_code in [201, 200]
    login_resp = client.post(
        "/api/v1/auth/login",
        json={
            "email": email,
            "password": "password123",
        },
    )
    assert login_resp.status_code == 200
    return login_resp.json()["access_token"]

def create_synthetic_regression_csv(n_samples: int = 100, seed: int = 42) -> bytes:
    np.random.seed(seed)
    x1 = np.random.normal(0, 1, n_samples)
    x2 = 2.0 * x1 + np.random.normal(0, 0.5, n_samples)
    x3 = np.random.uniform(10, 50, n_samples)
    target = 3.0 * x1 + 1.5 * x2 + np.random.normal(0, 0.5, n_samples)

    df = pd.DataFrame({
        "num_x1": x1,
        "num_x2": x2,
        "num_x3": x3,
        "target": target,
    })
    buf = io.BytesIO()
    df.to_csv(buf, index=False)
    buf.seek(0)
    return buf.getvalue()

def create_synthetic_classification_csv(n_samples: int = 100, seed: int = 42) -> bytes:
    np.random.seed(seed)
    x1 = np.random.normal(0, 1, n_samples)
    x2 = 2.0 * x1 + np.random.normal(0, 0.5, n_samples)
    x3 = np.random.uniform(10, 50, n_samples)
    logits = 2.0 * x1 + 1.0 * x2 + np.random.normal(0, 0.5, n_samples)
    target = (logits > np.median(logits)).astype(int)

    df = pd.DataFrame({
        "num_x1": x1,
        "num_x2": x2,
        "num_x3": x3,
        "target": target,
    })
    buf = io.BytesIO()
    df.to_csv(buf, index=False)
    buf.seek(0)
    return buf.getvalue()


# =============================================================================
# Acceptance Check (h): Sanity-Check Adjusted R2 Formula Against Known Example
# =============================================================================

def test_acceptance_check_h_adjusted_r2_formula():
    """
    Check (h): Sanity-check Adjusted R2 against a manually computed value for one small known example,
    to catch an n/p formula mistake.
    Formula: 1 - ((1 - R2) * (n - 1)) / (n - p - 1)
    """
    # 1. Test using a clean known array where unrounded R2 is known
    # If y_true = [3, -0.5, 2, 7], y_pred = [2.5, 0.0, 2, 8]
    # mean(y_true) = 2.875
    # SS_tot = (3-2.875)^2 + (-0.5-2.875)^2 + (2-2.875)^2 + (7-2.875)^2 = 0.015625 + 11.390625 + 0.765625 + 17.015625 = 29.1875
    # SS_res = (3-2.5)^2 + (-0.5-0)^2 + (2-2)^2 + (7-8)^2 = 0.25 + 0.25 + 0 + 1 = 1.5
    # R2 = 1 - 1.5 / 29.1875 = 1 - 0.05139186295503212 = 0.9486081370449679
    # With n = 50, p = 4:
    # adj_R2 = 1 - ((1 - R2) * 49) / 45 = 1 - (0.05139186295503212 * 49) / 45 = 1 - 0.05596002855103497 = 0.944039971448965
    y_true = np.array([3.0, -0.5, 2.0, 7.0])
    y_pred = np.array([2.5, 0.0, 2.0, 8.0])
    n = 50
    p = 4

    metrics = EvaluationService.evaluate_regression(y_true, y_pred, n=n, p=p)
    raw_r2 = 1.0 - (1.5 / 29.1875)
    expected_adj_r2 = round(1.0 - ((1.0 - raw_r2) * (n - 1)) / (n - p - 1), 5)

    assert metrics["r2"] == round(raw_r2, 5)
    assert metrics["adjusted_r2"] == expected_adj_r2
    assert "mae" in metrics
    assert "mse" in metrics
    assert "rmse" in metrics
    assert metrics["rmse"] == round(np.sqrt(metrics["mse"]), 5)



# =============================================================================
# Acceptance Check (a), (d), & (e): Single Locked Test Access & Full Dev Refit
# =============================================================================

def test_acceptance_check_a_d_e_single_locked_test_and_full_dev_refit(db_session):
    """
    Check (a): Confirm get_locked_test_data() is called EXACTLY ONCE during a full
               finalize_experiment run, and only for the winning model.
    Check (d): Confirm the final refit uses ALL Development rows (not a fold subset).
    Check (e): Confirm Locked Test rows are never used in a .fit() call anywhere in this day's code.
    """
    role = db_session.query(Role).filter(Role.role_name == "ML_ENGINEER").first()
    user = User(
        id=uuid.uuid4(),
        full_name="Locked Test Auditor",
        email="auditor_d7@test.com",
        password_hash="fake",
        role_id=role.id,
    )
    db_session.add(user)

    project = Project(
        id=uuid.uuid4(),
        owner_id=user.id,
        project_name="Locked Test Isolation Project",
        task_type="REGRESSION",
        target_column="target",
        pipeline_stage="SPLIT",
    )
    db_session.add(project)
    db_session.commit()

    csv_bytes = create_synthetic_regression_csv(100, seed=42)
    ds_service = DatasetService(db_session)
    dataset = ds_service.upload(project.id, "synthetic_reg.csv", csv_bytes, uploaded_by_id=user.id)
    ds_service.detect_structural_schema(dataset.id)

    split_service = DatasetSplitService(db_session)
    split_info = split_service.create_outer_split(dataset.id, locked_test_pct=20, seed=42)
    dev_rows = split_info["development_rows"]  # 80 rows
    test_rows = split_info["locked_test_rows"]  # 20 rows

    assert dev_rows == 80
    assert test_rows == 20

    # Spy on DatasetSplitService.get_locked_test_data
    original_get_locked_test = DatasetSplitService.get_locked_test_data
    call_count = 0
    accessed_datasets = []

    def spy_get_locked_test_data(self, dataset_id):
        nonlocal call_count
        call_count += 1
        accessed_datasets.append(dataset_id)
        return original_get_locked_test(self, dataset_id)

    # Monitor all .fit() calls to assert locked test rows are NEVER passed to .fit()
    fit_row_counts = []
    original_reg_fit = RegressionTrainer.fit

    def spy_reg_fit(self, X, y):
        fit_row_counts.append(len(X))
        return original_reg_fit(self, X, y)

    with patch.object(DatasetSplitService, "get_locked_test_data", spy_get_locked_test_data), \
         patch.object(RegressionTrainer, "fit", spy_reg_fit):

        exp_service = ExperimentService(db_session)
        # Run CV without auto-finalizing first
        result = exp_service.run_experiment(
            project_id=project.id,
            algorithms=["LinearRegression", "Ridge", "RandomForestRegressor"],
            folds=5,
            seed=42,
            selection_metric="rmse",
            selection_direction="MINIMIZE",
            auto_finalize=False,
        )

        # During CV training, locked test data must NOT be touched at all
        assert call_count == 0, f"Expected 0 calls during CV, got {call_count}"

        # Now execute finalize_experiment
        finalize_result = exp_service.finalize_experiment(result["experiment_id"])

    # Check (a) Assertions:
    # 1. get_locked_test_data was called EXACTLY ONCE
    assert call_count == 1, f"Expected get_locked_test_data to be called exactly 1 time, got {call_count}"
    assert accessed_datasets[0] == dataset.id
    assert finalize_result["locked_test_consumed"] is True

    # 2. Assert metrics stored with split='LOCKED_TEST' for the winning model only
    experiment = exp_service.exp_repo.get_with_models(result["experiment_id"])
    assert experiment.selected_model_id is not None
    winning_model_id = experiment.selected_model_id

    locked_test_metrics = db_session.query(ModelMetric).filter(
        ModelMetric.split == "LOCKED_TEST"
    ).all()
    assert len(locked_test_metrics) > 0
    for m in locked_test_metrics:
        assert m.model_id == winning_model_id, "LOCKED_TEST metrics must belong ONLY to the winning model"

    # Check (d) Assertions:
    # Final refit row count equals full Development partition size (80 rows)
    assert finalize_result["development_rows_fit"] == dev_rows == 80
    assert 80 in fit_row_counts, f"Expected 80 rows in fit_row_counts, got {fit_row_counts}"

    # Check (e) Assertions:
    # 20 (locked test row count) is NEVER in fit_row_counts
    assert test_rows not in fit_row_counts, f"Leakage detected! Locked test size ({test_rows}) found in .fit() calls: {fit_row_counts}"


# =============================================================================
# Acceptance Check (b): Calling Finalize Twice Is Rejected Outright
# =============================================================================

def test_acceptance_check_b_finalize_twice_rejected(db_session):
    """
    Check (b): Call finalize_experiment twice on the same experiment_id and confirm the second call
               is rejected outright (locked_test_consumed guard fires) rather than silently
               re-evaluating and overwriting the first LOCKED_TEST metrics.
    """
    role = db_session.query(Role).filter(Role.role_name == "ML_ENGINEER").first()
    user = User(
        id=uuid.uuid4(),
        full_name="Guard Dev",
        email="guard_dev@test.com",
        password_hash="fake",
        role_id=role.id,
    )
    db_session.add(user)

    project = Project(
        id=uuid.uuid4(),
        owner_id=user.id,
        project_name="Guard Rejection Project",
        task_type="CLASSIFICATION",
        target_column="target",
        pipeline_stage="SPLIT",
    )
    db_session.add(project)
    db_session.commit()

    csv_bytes = create_synthetic_classification_csv(100, seed=42)
    ds_service = DatasetService(db_session)
    dataset = ds_service.upload(project.id, "clf_guard.csv", csv_bytes, uploaded_by_id=user.id)
    ds_service.detect_structural_schema(dataset.id)

    split_service = DatasetSplitService(db_session)
    split_service.create_outer_split(dataset.id, locked_test_pct=20, seed=42)

    exp_service = ExperimentService(db_session)
    result = exp_service.run_experiment(
        project_id=project.id,
        algorithms=["LogisticRegression", "RandomForestClassifier"],
        folds=3,
        seed=42,
        auto_finalize=False,
    )
    exp_id = result["experiment_id"]

    # First finalization call succeeds
    fin1 = exp_service.finalize_experiment(exp_id)
    assert fin1["status"] == "COMPLETED"
    assert fin1["locked_test_consumed"] is True

    # Second finalization call MUST raise HTTPException(400)
    with pytest.raises(HTTPException) as exc_info:
        exp_service.finalize_experiment(exp_id)

    assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
    assert "already been consumed" in str(exc_info.value.detail)


# =============================================================================
# Acceptance Check (c): rerun_locked_test_diagnostic Records TEST_REUSED_DIAGNOSTIC
# =============================================================================

def test_acceptance_check_c_diagnostic_rerun_and_leaderboard_isolation(client, db_session):
    """
    Check (c): Call rerun_locked_test_diagnostic after normal finalization and confirm the
               resulting rows are stored as TEST_REUSED_DIAGNOSTIC and do NOT appear in the
               GET /leaderboard response or affect selected_model_id.
    """
    mle_token = get_auth_token(client, email="diagnostic_user@studio.com", role_name="ML_ENGINEER")
    headers = {"Authorization": f"Bearer {mle_token}"}

    # 1. Create project & dataset
    proj_resp = client.post("/api/v1/projects", headers=headers, json={"project_name": "Diagnostic Test Project"})
    assert proj_resp.status_code == 201
    proj_id = proj_resp.json()["id"]

    csv_bytes = create_synthetic_classification_csv(100, seed=42)
    files = {"file": ("clf_diag.csv", io.BytesIO(csv_bytes), "text/csv")}
    upload_resp = client.post(f"/api/v1/projects/{proj_id}/datasets", headers=headers, files=files)
    assert upload_resp.status_code == 201
    dataset_id = upload_resp.json()["id"]

    client.post(f"/api/v1/datasets/{dataset_id}/split", headers=headers, json={"locked_test_pct": 20, "seed": 42})
    client.put(f"/api/v1/projects/{proj_id}", headers=headers, json={"task_type": "CLASSIFICATION", "target_column": "target"})

    # 2. Run experiment and finalize
    exp_service = ExperimentService(db_session)
    exp_res = exp_service.run_experiment(
        project_id=proj_id,
        algorithms=["LogisticRegression", "RandomForestClassifier"],
        folds=3,
        seed=42,
        selection_metric="f1_macro",
        selection_direction="MAXIMIZE",
        auto_finalize=True,
    )
    exp_id = exp_res["experiment_id"]
    initial_winner = exp_res["selected_model_id"]
    assert initial_winner is not None

    # 3. Call rerun_locked_test_diagnostic
    diag_res = exp_service.rerun_locked_test_diagnostic(exp_id)
    assert diag_res["split"] == "TEST_REUSED_DIAGNOSTIC"
    assert diag_res["selected_model_id"] == initial_winner

    # Verify database has TEST_REUSED_DIAGNOSTIC rows
    diag_metrics = db_session.query(ModelMetric).filter(
        ModelMetric.split == "TEST_REUSED_DIAGNOSTIC"
    ).all()
    assert len(diag_metrics) > 0

    # 4. Verify GET /api/v1/projects/{id}/leaderboard excludes TEST_REUSED_DIAGNOSTIC
    lb_resp = client.get(f"/api/v1/projects/{proj_id}/leaderboard", headers=headers)
    assert lb_resp.status_code == 200
    lb_data = lb_resp.json()
    assert lb_data["selected_model_id"] == str(initial_winner)

    for m in lb_data["models"]:
        for metric in m["metrics"]:
            assert metric["split"] != "TEST_REUSED_DIAGNOSTIC", "Leaderboard response must NEVER contain TEST_REUSED_DIAGNOSTIC rows"

    # 5. Verify GET /api/v1/experiments/{id}/selection endpoint
    sel_resp = client.get(f"/api/v1/experiments/{exp_id}/selection", headers=headers)
    assert sel_resp.status_code == 200
    sel_data = sel_resp.json()
    assert sel_data["selected_model_id"] == str(initial_winner)
    assert sel_data["selection_metric"] == "f1_macro"
    assert sel_data["selection_direction"] == "MAXIMIZE"
    assert sel_data["locked_test_consumed"] is True


# =============================================================================
# Acceptance Check (f): Overfit and Underfit Diagnostics
# =============================================================================

def test_acceptance_check_f_overfit_and_underfit_diagnostics():
    """
    Check (f): Deliberately construct an overfit scenario (large train-CV gap) and confirm
               POTENTIAL_OVERFIT; separately construct a near-baseline scenario (shuffled labels)
               and confirm POTENTIAL_UNDERFIT_WEAK_SIGNAL.
    """
    # 1. Overfit Scenario:
    # Train R2 = 0.98, CV Mean R2 = 0.50 (Gap = 0.48 > 0.15 threshold)
    train_metrics_overfit = {"r2": 0.98, "rmse": 0.10}
    cv_metrics_overfit = {"r2": 0.50, "rmse": 0.60}
    baseline_overfit = {"r2": 0.0, "rmse": 1.0}

    diag_overfit = EvaluationService.diagnose_fit(
        train_metrics=train_metrics_overfit,
        cv_mean_metrics=cv_metrics_overfit,
        baseline_metrics=baseline_overfit,
        metric_name="r2",
        n_val_samples=100,
    )
    assert diag_overfit == "POTENTIAL_OVERFIT"

    # 2. Underfit / Weak Signal Scenario:
    # Train Accuracy = 0.52, CV Mean Accuracy = 0.51, Baseline (majority class) = 0.50
    # CV lift = 0.01 <= 0.05 margin, Train lift = 0.02 <= 0.125
    train_metrics_underfit = {"accuracy": 0.52, "f1_macro": 0.52}
    cv_metrics_underfit = {"accuracy": 0.51, "f1_macro": 0.51}
    baseline_underfit = {"accuracy": 0.50, "f1_macro": 0.50}

    diag_underfit = EvaluationService.diagnose_fit(
        train_metrics=train_metrics_underfit,
        cv_mean_metrics=cv_metrics_underfit,
        baseline_metrics=baseline_underfit,
        metric_name="accuracy",
        n_val_samples=100,
    )
    assert diag_underfit == "POTENTIAL_UNDERFIT_WEAK_SIGNAL"

    # 3. Good Fit Scenario:
    # Train F1 = 0.88, CV Mean F1 = 0.85, Baseline = 0.40
    # Gap = 0.03 <= 0.10, lift = 0.45 >> 0.05
    train_metrics_good = {"f1_macro": 0.88}
    cv_metrics_good = {"f1_macro": 0.85}
    baseline_good = {"f1_macro": 0.40}

    diag_good = EvaluationService.diagnose_fit(
        train_metrics=train_metrics_good,
        cv_mean_metrics=cv_metrics_good,
        baseline_metrics=baseline_good,
        metric_name="f1_macro",
        n_val_samples=100,
    )
    assert diag_good == "GOOD_FIT"

    # 4. Insufficient Data Scenario (< 20 samples)
    diag_insufficient = EvaluationService.diagnose_fit(
        train_metrics=train_metrics_good,
        cv_mean_metrics=cv_metrics_good,
        baseline_metrics=baseline_good,
        metric_name="f1_macro",
        n_val_samples=15,
    )
    assert diag_insufficient == "INSUFFICIENT_DATA"


# =============================================================================
# Acceptance Check (g): Model Selection Score Never Changes Sort Order
# =============================================================================

def test_acceptance_check_g_model_selection_score_never_changes_sort_order(client, db_session):
    """
    Check (g): Confirm changing model_selection_score (or a bug that miscalculates it)
               never changes leaderboard sort order — sort strictly by selection_metric.
    """
    mle_token = get_auth_token(client, email="sort_order_test@studio.com", role_name="ML_ENGINEER")
    headers = {"Authorization": f"Bearer {mle_token}"}

    proj_resp = client.post("/api/v1/projects", headers=headers, json={"project_name": "Sort Invariance Project"})
    proj_id = proj_resp.json()["id"]

    csv_bytes = create_synthetic_regression_csv(100, seed=42)
    files = {"file": ("sort_test.csv", io.BytesIO(csv_bytes), "text/csv")}
    upload_resp = client.post(f"/api/v1/projects/{proj_id}/datasets", headers=headers, files=files)
    dataset_id = upload_resp.json()["id"]

    client.post(f"/api/v1/datasets/{dataset_id}/split", headers=headers, json={"locked_test_pct": 20, "seed": 42})
    client.put(f"/api/v1/projects/{proj_id}", headers=headers, json={"task_type": "REGRESSION", "target_column": "target"})

    exp_service = ExperimentService(db_session)
    exp_res = exp_service.run_experiment(
        project_id=proj_id,
        algorithms=["LinearRegression", "Ridge", "RandomForestRegressor"],
        folds=3,
        seed=42,
        selection_metric="rmse",
        selection_direction="MINIMIZE",
        auto_finalize=True,
    )

    models = db_session.query(TrainedModel).filter(TrainedModel.experiment_id == exp_res["experiment_id"]).all()
    assert len(models) == 3

    # Corrupt model_selection_score intentionally: assign 0.0 to best model and 100.0 to worst model
    models[0].model_selection_score = 0.0
    models[1].model_selection_score = 50.0
    models[2].model_selection_score = 100.0
    db_session.add_all(models)
    db_session.commit()

    # Query leaderboard via API
    lb_resp = client.get(f"/api/v1/projects/{proj_id}/leaderboard", headers=headers)
    assert lb_resp.status_code == 200
    lb_models = lb_resp.json()["models"]

    # Verify leaderboard is strictly monotonic by primary_metric_value (RMSE ascending)
    rmse_scores = [m["primary_metric_value"] for m in lb_models]
    assert rmse_scores == sorted(rmse_scores), f"Leaderboard not sorted by primary metric! Got {rmse_scores}"
    assert lb_models[0]["is_winner"] is True
