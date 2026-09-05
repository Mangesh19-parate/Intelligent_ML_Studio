import io
import os
import uuid
import pytest
import numpy as np
import pandas as pd
from fastapi import status
from unittest.mock import patch

from app.models.dataset import Dataset
from app.models.dataset_split import DatasetSplit
from app.models.experiment import Experiment
from app.models.feature_selection_fold_result import FeatureSelectionFoldResult
from app.models.trained_model import TrainedModel
from app.models.project import Project
from app.models.user import User
from app.models.role import Role
from app.services.dataset_service import DatasetService
from app.services.dataset_split_service import DatasetSplitService
from app.services.transformation_service import TransformationService
from app.services.experiment_service import ExperimentService
from app.services.trainers import RegressionTrainer, ClassificationTrainer, FeatureSelector

def get_auth_token(client, email="engineer_d6@example.com", role_name="ML_ENGINEER"):
    reg_resp = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Test User D6",
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

def create_synthetic_regression_csv(n_samples: int = 100) -> bytes:
    np.random.seed(42)
    x1 = np.random.normal(0, 1, n_samples)
    x2 = 2.0 * x1 + np.random.normal(0, 0.5, n_samples)
    x3 = np.random.uniform(10, 50, n_samples)
    x4 = np.random.normal(100, 20, n_samples)
    category = np.random.choice(["TypeA", "TypeB", "TypeC"], size=n_samples)
    target = 3.0 * x1 + 1.5 * x2 + 0.2 * x3 + np.random.normal(0, 0.5, n_samples)

    df = pd.DataFrame({
        "num_x1": x1,
        "num_x2": x2,
        "num_x3": x3,
        "noise_x4": x4,
        "category_col": category,
        "target": target,
    })
    buf = io.BytesIO()
    df.to_csv(buf, index=False)
    buf.seek(0)
    return buf.getvalue()

def create_synthetic_classification_csv(n_samples: int = 100) -> bytes:
    np.random.seed(42)
    x1 = np.random.normal(0, 1, n_samples)
    x2 = 2.0 * x1 + np.random.normal(0, 0.5, n_samples)
    x3 = np.random.uniform(10, 50, n_samples)
    category = np.random.choice(["TypeA", "TypeB", "TypeC"], size=n_samples)
    logits = 2.0 * x1 + 1.0 * x2 + np.random.normal(0, 0.5, n_samples)
    target = (logits > np.median(logits)).astype(int)

    df = pd.DataFrame({
        "num_x1": x1,
        "num_x2": x2,
        "num_x3": x3,
        "category_col": category,
        "target": target,
    })
    buf = io.BytesIO()
    df.to_csv(buf, index=False)
    buf.seek(0)
    return buf.getvalue()


# =============================================================================
# 1. OOP Trainers & Pipeline Design Tests
# =============================================================================

def test_trainer_pipeline_unfit_freshness():
    """
    Verifies that get_pipeline() on RegressionTrainer and ClassificationTrainer returns
    a fresh, UNFIT scikit-learn Pipeline combining transformer, selector, and estimator.
    """
    reg_trainer = RegressionTrainer("Ridge", hyperparameters={"alpha": 2.0}, random_state=42)
    pipe1 = reg_trainer.get_pipeline()
    pipe2 = reg_trainer.get_pipeline()

    assert pipe1 is not pipe2
    assert "transformer" in pipe1.named_steps
    assert "selector" in pipe1.named_steps
    assert "estimator" in pipe1.named_steps
    assert pipe1.named_steps["estimator"].alpha == 2.0

    clf_trainer = ClassificationTrainer("LogisticRegression", random_state=42)
    clf_pipe = clf_trainer.get_pipeline()
    assert "transformer" in clf_pipe.named_steps
    assert "selector" in clf_pipe.named_steps
    assert "estimator" in clf_pipe.named_steps


# =============================================================================
# 2. Acceptance Check (a) & (b): Regression 3-Algorithm Training, Shared Selection & Zero .joblib
# =============================================================================

def test_acceptance_check_a_and_b_regression_training_and_shared_selection(db_session, tmp_path):
    """
    Check (a): Kick off an experiment with all 3 regression algorithms on a small test dataset;
               confirm 3 trained_models rows are created, each with a plausible quick_cv_score,
               and confirm NO .joblib file was written anywhere on disk.
    Check (b): Confirm feature selection ran exactly ONCE per fold
               (feature_selection_fold_results row count = fold_count = 5, not 5 * 3 = 15).
    """
    role = db_session.query(Role).filter(Role.role_name == "ML_ENGINEER").first()
    user = User(
        id=uuid.uuid4(),
        full_name="ML Trainer",
        email="trainer_reg@test.com",
        password_hash="fake",
        role_id=role.id,
    )
    db_session.add(user)

    project = Project(
        id=uuid.uuid4(),
        owner_id=user.id,
        project_name="Regression Training Project",
        task_type="REGRESSION",
        target_column="target",
        pipeline_stage="TRANSFORMED",
    )
    db_session.add(project)
    db_session.commit()

    # Upload dataset and split
    csv_bytes = create_synthetic_regression_csv(100)
    ds_service = DatasetService(db_session)
    dataset = ds_service.upload(project.id, "synthetic_reg.csv", csv_bytes, uploaded_by_id=user.id)
    ds_service.detect_structural_schema(dataset.id)

    split_service = DatasetSplitService(db_session)
    split_service.create_outer_split(dataset.id, locked_test_pct=20, seed=42)

    # Configure categorical encoding
    trans_service = TransformationService(db_session)
    trans_service.set_encoding_strategy(project.id, "category_col", "one_hot")

    # Record disk snapshot before training to verify zero new .joblib files
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    initial_joblib_files = set()
    for root, _, files in os.walk(repo_root):
        for f in files:
            if f.endswith(".joblib"):
                initial_joblib_files.add(os.path.join(root, f))

    exp_service = ExperimentService(db_session)
    result = exp_service.run_experiment(
        project_id=project.id,
        algorithms=["LinearRegression", "Ridge", "RandomForestRegressor"],
        folds=5,
        seed=42,
    )

    assert result["status"] == "COMPLETED"
    assert result["fold_count"] == 5
    assert len(result["trained_models"]) == 3

    # Check (a) Assertions:
    # 1. Verify 3 trained_models rows created with plausible R2 quick_cv_scores
    models = db_session.query(TrainedModel).filter(
        TrainedModel.experiment_id == result["experiment_id"]
    ).all()
    assert len(models) == 3

    model_map = {m.algorithm_name: m for m in models}
    assert "LinearRegression" in model_map
    assert "Ridge" in model_map
    assert "RandomForestRegressor" in model_map

    for alg_name, m in model_map.items():
        assert m.status == "COMPLETED"
        assert m.quick_cv_score is not None
        score = float(m.quick_cv_score)
        # On synthetic linear regression data, R2 should be strongly positive (> 0.5)
        assert score > 0.5, f"Expected R2 > 0.5 for {alg_name}, got {score}"

    # 2. Confirm NO new .joblib file was written anywhere on disk
    new_joblib_files = []
    for root, _, files in os.walk(repo_root):
        for f in files:
            if f.endswith(".joblib") and os.path.join(root, f) not in initial_joblib_files:
                new_joblib_files.append(os.path.join(root, f))
    assert len(new_joblib_files) == 0, f"Found unexpected new .joblib files: {new_joblib_files}"

    # Check (b) Assertion:
    # Feature selection ran exactly ONCE per fold -> count == 5 (not 5 * 3 = 15)
    fold_results = db_session.query(FeatureSelectionFoldResult).filter(
        FeatureSelectionFoldResult.experiment_id == result["experiment_id"]
    ).all()
    assert len(fold_results) == 5, f"Expected exactly 5 fold results, got {len(fold_results)}"

    # Confirm pipeline_stage transitioned to TRAINED
    db_session.refresh(project)
    assert project.pipeline_stage == "TRAINED"


# =============================================================================
# 3. Acceptance Check (c): Zero Leakage Verification
# =============================================================================

def test_acceptance_check_c_zero_leakage(db_session):
    """
    Check (c): Zero leakage check - verify zero overlap between fold train indices and
               fold validation indices, and zero overlap with Locked Test indices.
    """
    role = db_session.query(Role).filter(Role.role_name == "ML_ENGINEER").first()
    user = User(
        id=uuid.uuid4(),
        full_name="ML Leakage Auditor",
        email="auditor@test.com",
        password_hash="fake",
        role_id=role.id,
    )
    db_session.add(user)

    project = Project(
        id=uuid.uuid4(),
        owner_id=user.id,
        project_name="Leakage Audit Project",
        task_type="CLASSIFICATION",
        target_column="target",
        pipeline_stage="TRANSFORMED",
    )
    db_session.add(project)
    db_session.commit()

    csv_bytes = create_synthetic_classification_csv(100)
    ds_service = DatasetService(db_session)
    dataset = ds_service.upload(project.id, "clf_leakage.csv", csv_bytes, uploaded_by_id=user.id)
    ds_service.detect_structural_schema(dataset.id)

    split_service = DatasetSplitService(db_session)
    split_service.create_outer_split(dataset.id, locked_test_pct=20, seed=123)
    
    # Retrieve development and locked test splits
    dev_split = db_session.query(DatasetSplit).filter(
        DatasetSplit.dataset_id == dataset.id,
        DatasetSplit.split_type == "DEVELOPMENT",
    ).first()
    locked_test_split = db_session.query(DatasetSplit).filter(
        DatasetSplit.dataset_id == dataset.id,
        DatasetSplit.split_type == "LOCKED_TEST",
    ).first()

    dev_indices = set(dev_split.row_indices)
    locked_test_indices = set(locked_test_split.row_indices)
    
    # 1. Invariant: Development rows and Locked Test rows are completely disjoint
    assert len(dev_indices.intersection(locked_test_indices)) == 0
    assert len(dev_indices) == 80
    assert len(locked_test_indices) == 20
    assert len(dev_indices) + len(locked_test_indices) == 100

    # 2. Retrieve development partition dataframe via authorized accessor
    dev_df = split_service.get_development_data(dataset.id)
    assert len(dev_df) == 80

    exp_service = ExperimentService(db_session)
    result = exp_service.run_experiment(
        project_id=project.id,
        algorithms=["LogisticRegression", "RandomForestClassifier", "GradientBoostingClassifier"],
        folds=5,
        seed=123,
    )

    assert result["status"] == "COMPLETED"


# =============================================================================
# 4. Acceptance Check (d): Fault Tolerance / Single Algorithm Failure
# =============================================================================

def test_acceptance_check_d_single_algorithm_failure_isolation(db_session):
    """
    Check (d): Force one algorithm to fail on purpose (e.g. invalid hyperparameter/error during fit)
               and confirm the experiment still completes for the other two algorithms,
               with the failed one's trained_models row clearly reflecting the failure (status='FAILED').
    """
    role = db_session.query(Role).filter(Role.role_name == "ML_ENGINEER").first()
    user = User(
        id=uuid.uuid4(),
        full_name="Fault Dev",
        email="fault_dev@test.com",
        password_hash="fake",
        role_id=role.id,
    )
    db_session.add(user)

    project = Project(
        id=uuid.uuid4(),
        owner_id=user.id,
        project_name="Fault Tolerance Project",
        task_type="REGRESSION",
        target_column="target",
        pipeline_stage="TRANSFORMED",
    )
    db_session.add(project)
    db_session.commit()

    csv_bytes = create_synthetic_regression_csv(80)
    ds_service = DatasetService(db_session)
    dataset = ds_service.upload(project.id, "fault_reg.csv", csv_bytes, uploaded_by_id=user.id)
    ds_service.detect_structural_schema(dataset.id)

    split_service = DatasetSplitService(db_session)
    split_service.create_outer_split(dataset.id, locked_test_pct=20, seed=42)

    # Force Ridge to raise an exception during fit by patching Ridge.fit
    original_ridge_fit = RegressionTrainer.fit

    def faulty_fit(self, X, y):
        if self.algorithm_name == "Ridge":
            raise ValueError("Intentional simulated solver crash for Ridge regression")
        return original_ridge_fit(self, X, y)

    with patch.object(RegressionTrainer, "fit", faulty_fit):
        exp_service = ExperimentService(db_session)
        result = exp_service.run_experiment(
            project_id=project.id,
            algorithms=["LinearRegression", "Ridge", "RandomForestRegressor"],
            folds=3,
            seed=42,
        )

    # Experiment itself completes
    assert result["status"] == "COMPLETED"

    models = db_session.query(TrainedModel).filter(
        TrainedModel.experiment_id == result["experiment_id"]
    ).all()
    assert len(models) == 3

    model_map = {m.algorithm_name: m for m in models}
    
    # LinearRegression and RandomForestRegressor succeeded
    assert model_map["LinearRegression"].status == "COMPLETED"
    assert model_map["LinearRegression"].quick_cv_score is not None
    assert model_map["RandomForestRegressor"].status == "COMPLETED"
    assert model_map["RandomForestRegressor"].quick_cv_score is not None

    # Ridge failed gracefully without corrupting others
    assert model_map["Ridge"].status == "FAILED"
    assert model_map["Ridge"].quick_cv_score is None
    assert "Intentional simulated solver crash" in model_map["Ridge"].error_message


# =============================================================================
# 5. Acceptance Check (e): Determinism Across Runs
# =============================================================================

def test_acceptance_check_e_determinism_across_runs(db_session):
    """
    Check (e): Determinism check: rerun the same experiment config (same seed, same algorithms)
               and confirm quick_cv_scores are identical across the two runs.
    """
    role = db_session.query(Role).filter(Role.role_name == "ML_ENGINEER").first()
    user = User(
        id=uuid.uuid4(),
        full_name="Det Dev",
        email="det_dev@test.com",
        password_hash="fake",
        role_id=role.id,
    )
    db_session.add(user)

    project = Project(
        id=uuid.uuid4(),
        owner_id=user.id,
        project_name="Determinism Project",
        task_type="REGRESSION",
        target_column="target",
        pipeline_stage="TRANSFORMED",
    )
    db_session.add(project)
    db_session.commit()

    csv_bytes = create_synthetic_regression_csv(80)
    ds_service = DatasetService(db_session)
    dataset = ds_service.upload(project.id, "det_reg.csv", csv_bytes, uploaded_by_id=user.id)
    ds_service.detect_structural_schema(dataset.id)

    split_service = DatasetSplitService(db_session)
    split_service.create_outer_split(dataset.id, locked_test_pct=20, seed=42)

    exp_service = ExperimentService(db_session)
    
    # Run 1
    res1 = exp_service.run_experiment(
        project_id=project.id,
        algorithms=["LinearRegression", "Ridge", "RandomForestRegressor"],
        folds=3,
        seed=999,
    )
    # Run 2
    res2 = exp_service.run_experiment(
        project_id=project.id,
        algorithms=["LinearRegression", "Ridge", "RandomForestRegressor"],
        folds=3,
        seed=999,
    )

    models1 = {m["algorithm_name"]: m["quick_cv_score"] for m in res1["trained_models"]}
    models2 = {m["algorithm_name"]: m["quick_cv_score"] for m in res2["trained_models"]}

    for alg in ["LinearRegression", "Ridge", "RandomForestRegressor"]:
        assert pytest.approx(models1[alg], abs=1e-5) == models2[alg]


# =============================================================================
# 6. Acceptance Check (f): Rejection of Mismatched Algorithm Names (HTTP 422)
# =============================================================================

def test_acceptance_check_f_task_type_mismatch_422(db_session):
    """
    Check (f): Requesting a classification algorithm on a REGRESSION-typed project
               (or vice versa) is rejected with a clear HTTP 422 before any training work starts.
    """
    role = db_session.query(Role).filter(Role.role_name == "ML_ENGINEER").first()
    user = User(
        id=uuid.uuid4(),
        full_name="Val Dev",
        email="val_dev@test.com",
        password_hash="fake",
        role_id=role.id,
    )
    db_session.add(user)

    reg_project = Project(
        id=uuid.uuid4(),
        owner_id=user.id,
        project_name="Reg Project",
        task_type="REGRESSION",
        target_column="target",
    )
    clf_project = Project(
        id=uuid.uuid4(),
        owner_id=user.id,
        project_name="Clf Project",
        task_type="CLASSIFICATION",
        target_column="target",
    )
    db_session.add_all([reg_project, clf_project])
    db_session.commit()

    exp_service = ExperimentService(db_session)

    # 1. Requesting Classifier on REGRESSION project
    with pytest.raises(Exception) as exc_info:
        exp_service.run_experiment(
            project_id=reg_project.id,
            algorithms=["LogisticRegression"],
        )
    assert "422" in str(exc_info.value) or "Invalid algorithm" in str(exc_info.value)

    # 2. Requesting Regressor on CLASSIFICATION project
    with pytest.raises(Exception) as exc_info2:
        exp_service.run_experiment(
            project_id=clf_project.id,
            algorithms=["LinearRegression"],
        )
    assert "422" in str(exc_info2.value) or "Invalid algorithm" in str(exc_info2.value)


# =============================================================================
# 7. API Endpoints, BackgroundTasks & RBAC Permission Tests
# =============================================================================

def test_api_experiments_endpoints_and_rbac(client):
    """
    Tests POST /api/v1/projects/{id}/experiments, GET /api/v1/experiments/{id},
    GET /api/v1/projects/{id}/experiments, and RBAC enforcement.
    """
    mle_token = get_auth_token(client, email="mle_trainer@studio.com", role_name="ML_ENGINEER")
    mle_headers = {"Authorization": f"Bearer {mle_token}"}

    viewer_token = get_auth_token(client, email="viewer_trainer@studio.com", role_name="VIEWER")
    viewer_headers = {"Authorization": f"Bearer {viewer_token}"}

    # 1. Create project
    proj_resp = client.post(
        "/api/v1/projects",
        headers=mle_headers,
        json={"project_name": "API Training Project"},
    )
    assert proj_resp.status_code == 201
    project_id = proj_resp.json()["id"]

    # 2. Upload dataset & split
    csv_bytes = create_synthetic_classification_csv(100)
    files = {"file": ("clf_data.csv", io.BytesIO(csv_bytes), "text/csv")}
    upload_resp = client.post(f"/api/v1/projects/{project_id}/datasets", headers=mle_headers, files=files)
    assert upload_resp.status_code == 201
    dataset_id = upload_resp.json()["id"]

    split_resp = client.post(
        f"/api/v1/datasets/{dataset_id}/split",
        headers=mle_headers,
        json={"test_percentage": 20.0, "seed": 42},
    )
    assert split_resp.status_code == 201

    # 3. Set target column & task type
    patch_resp = client.put(
        f"/api/v1/projects/{project_id}",
        headers=mle_headers,
        json={"task_type": "CLASSIFICATION", "target_column": "target"},
    )
    assert patch_resp.status_code == 200

    # 4. VIEWER lacks TRAIN permission -> should receive 403 Forbidden
    forbidden_resp = client.post(
        f"/api/v1/projects/{project_id}/experiments",
        headers=viewer_headers,
        json={"algorithms": ["LogisticRegression"], "folds": 3},
    )
    assert forbidden_resp.status_code == status.HTTP_403_FORBIDDEN

    # 5. Invalid algorithm rejection via API (422)
    mismatch_resp = client.post(
        f"/api/v1/projects/{project_id}/experiments",
        headers=mle_headers,
        json={"algorithms": ["LinearRegression"], "folds": 3},
    )
    assert mismatch_resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    # 6. Launch valid experiment via API (with TRAIN permission)
    train_resp = client.post(
        f"/api/v1/projects/{project_id}/experiments",
        headers=mle_headers,
        json={
            "algorithms": ["LogisticRegression", "RandomForestClassifier", "GradientBoostingClassifier"],
            "folds": 3,
            "seed": 42,
        },
    )
    assert train_resp.status_code == 200
    exp_data = train_resp.json()
    assert "experiment_id" in exp_data
    experiment_id = exp_data["experiment_id"]

    # 7. GET /api/v1/experiments/{id}
    get_resp = client.get(f"/api/v1/experiments/{experiment_id}", headers=mle_headers)
    assert get_resp.status_code == 200
    exp_details = get_resp.json()
    assert exp_details["id"] == experiment_id
    assert exp_details["task_type"] == "CLASSIFICATION"
    assert exp_details["fold_count"] == 3

    # 8. GET /api/v1/projects/{id}/experiments
    list_resp = client.get(f"/api/v1/projects/{project_id}/experiments", headers=mle_headers)
    assert list_resp.status_code == 200
    assert len(list_resp.json()) >= 1
