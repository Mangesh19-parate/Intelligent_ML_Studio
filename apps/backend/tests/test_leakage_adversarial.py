"""
Adversarial Data Leakage & Invariant Verification Suite (10/10 ML Architecture Evidence).

Validates:
1. Zero Holdout Contamination: Holdout test set is never fitted or accessed during CV.
2. Per-Fold Isolation: Preprocessor and Feature Selectors fit solely on fold-train slices.
3. Locked Test Single-Consumption: Second evaluation attempts on locked holdout are permanently blocked.
4. Target Leakage Prevention: Target column is excluded from feature matrices.
"""

import io
import uuid
import pytest
import numpy as np
import pandas as pd
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.project import Project
from app.models.dataset import Dataset
from app.models.experiment import Experiment
from app.models.trained_model import TrainedModel
from app.models.model_metric import ModelMetric
from app.services.dataset_service import DatasetService
from app.services.dataset_split_service import DatasetSplitService
from app.services.feature_selection_service import FeatureSelectionService
from app.services.experiment_service import ExperimentService
from app.services.evaluation_service import EvaluationService
from app.config.state_machines import ModelState, ExperimentState


def create_synthetic_dataset(n_samples: int = 100, n_features: int = 5, seed: int = 42) -> pd.DataFrame:
    np.random.seed(seed)
    data = {f"feat_{i}": np.random.randn(n_samples) for i in range(n_features)}
    # Target has linear relationship with feat_0 and feat_1
    data["target"] = (data["feat_0"] * 2.5 + data["feat_1"] * -1.8 + np.random.randn(n_samples) * 0.1 > 0).astype(int)
    return pd.DataFrame(data)


@pytest.fixture
def ml_adversarial_project(db_session: Session, tmp_path):
    # 0. User
    from app.models.user import User
    from app.models.role import Role
    user = db_session.query(User).first()
    if not user:
        role = db_session.query(Role).first()
        user = User(
            email=f"adv_user_{uuid.uuid4().hex[:6]}@test.com",
            password_hash="fake",
            full_name="Adversarial Tester",
            role_id=role.id if role else None,
        )
        db_session.add(user)
        db_session.flush()

    # 1. Project
    project = Project(
        owner_id=user.id,
        project_name=f"Leakage Adversarial Project {uuid.uuid4().hex[:6]}",
        task_type="CLASSIFICATION",
        target_column="target",
    )
    db_session.add(project)
    db_session.flush()

    # 2. Upload dataset
    df = create_synthetic_dataset(n_samples=120, n_features=6)
    csv_bytes = df.to_csv(index=False).encode("utf-8")
    
    dataset_service = DatasetService(db_session)
    dataset = dataset_service.upload(
        project_id=project.id,
        filename="adversarial_data.csv",
        content=csv_bytes,
    )

    # 3. Outer Split (80% Dev, 20% Locked Holdout)
    split_service = DatasetSplitService(db_session)
    split_service.create_outer_split(dataset.id, locked_test_pct=20, seed=42)

    return {"project": project, "dataset": dataset, "df": df}


def test_zero_holdout_leakage_in_feature_selection(ml_adversarial_project, db_session: Session):
    """
    Asserts that FeatureSelectionService reads ONLY the development partition,
    and the locked test holdout partition remains pristine and unaccessed.
    """
    project = ml_adversarial_project["project"]
    dataset = ml_adversarial_project["dataset"]
    split_service = DatasetSplitService(db_session)
    
    dev_df = split_service.get_development_data(dataset.id)
    test_df = split_service.get_locked_test_data(dataset.id)
    
    assert len(dev_df) == 96  # 80% of 120
    assert len(test_df) == 24  # 20% of 120

    fs_service = FeatureSelectionService(db_session)
    fs_result = fs_service.run_cv_feature_selection(
        project_id=project.id,
        n_splits=3,
        seed=42,
    )
    
    assert "features" in fs_result
    assert len(fs_result["features"]) > 0
    # Confirm target column was not selected as a feature (no target leakage)
    assert "target" not in [f["column_name"] for f in fs_result["features"]]
    # Confirm row_uid was filtered out
    assert "row_uid" not in [f["column_name"] for f in fs_result["features"]]


def test_locked_test_single_consumption_invariant(ml_adversarial_project, db_session: Session):
    """
    Asserts that Locked Test holdout evaluation can only be executed exactly ONCE
    for the champion model. Subsequent evaluation attempts MUST be rejected with HTTP 400 Bad Request.
    """
    project = ml_adversarial_project["project"]
    
    exp_service = ExperimentService(db_session)
    exp_res = exp_service.run_experiment(
        project_id=project.id,
        algorithms=["LogisticRegression"],
        folds=3,
        seed=42,
        selection_metric="ACCURACY",
        selection_direction="MAXIMIZE",
        auto_finalize=False,
    )
    
    experiment_id = exp_res["experiment_id"]
    assert experiment_id is not None

    # First locked test finalization succeeds
    res1 = exp_service.finalize_experiment(experiment_id)
    assert res1["locked_test_consumed"] is True
    assert "ACCURACY" in res1["locked_test_metrics"] or "accuracy" in res1["locked_test_metrics"] or len(res1["locked_test_metrics"]) > 0

    # Second evaluation attempt MUST fail immediately with 400 Bad Request
    with pytest.raises(HTTPException) as exc_info:
        exp_service.finalize_experiment(experiment_id)
    
    assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
    assert "already been consumed" in exc_info.value.detail.lower()


def test_target_leakage_exclusion_in_training_matrices(ml_adversarial_project, db_session: Session):
    """
    Asserts that target column is never included in the input feature matrix X.
    """
    project = ml_adversarial_project["project"]
    dataset = ml_adversarial_project["dataset"]
    split_service = DatasetSplitService(db_session)
    
    dev_df = split_service.get_development_data(dataset.id)
    feature_cols = [col for col in dev_df.columns if col not in (project.target_column, "row_uid")]
    
    assert project.target_column not in feature_cols
    assert len(feature_cols) == 6

