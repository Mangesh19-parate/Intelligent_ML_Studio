"""
Unit Tests for run_experiment Foundational Skeleton (SRS v9 §2 / Day 3).

Verifies:
1. Loading and honoring frozen experiment_config.
2. Loading Development data strictly by row_uid (Zero Test Leakage Invariant).
3. Deterministic CV split construction (KFold for Regression, StratifiedKFold for Classification).
4. Strict Zero Leakage validation across CV folds (train_indices ∩ val_indices == ∅).
5. Reproducibility across multiple invocations with same cv_seed.
6. Proper exception handling for edge cases (insufficient rows, missing target column).
"""

import io
from uuid import uuid4
import numpy as np
import pandas as pd
import pytest
from fastapi import HTTPException, status

from app.models.project import Project
from app.models.dataset import Dataset
from app.models.dataset_column import DatasetColumn
from app.models.dataset_split import DatasetSplit
from app.models.transformation_config import TransformationConfig
from app.models.experiment import Experiment
from app.config.state_machines import ExperimentState
from app.services.experiment_service import ExperimentService
from app.services.dataset_split_service import DatasetSplitService


@pytest.fixture
def regression_cv_setup(db_session, create_test_user, tmp_path):
    """Sets up a complete regression dataset, outer split, and experiment for CV testing."""
    user = create_test_user("cv_tester_reg@studio.ml", "ADMIN")

    project = Project(
        id=uuid4(),
        owner_id=user.id,
        project_name="Housing CV Regression",
        task_type="REGRESSION",
        target_column="price",
        pipeline_stage="TRANSFORMED",
    )
    db_session.add(project)
    db_session.commit()

    # Generate synthetic regression dataset
    np.random.seed(42)
    n_samples = 100
    sqft = np.random.uniform(500, 3000, n_samples)
    beds = np.random.randint(1, 5, n_samples).astype(float)
    price = 200.0 * sqft + 5000.0 * beds + np.random.randn(n_samples) * 1000.0

    df = pd.DataFrame({
        "sqft": sqft,
        "beds": beds,
        "price": price,
    })
    # Deterministic row_uids
    df["row_uid"] = [f"row_reg_{i}" for i in range(n_samples)]

    csv_file = tmp_path / "housing_cv.csv"
    df.to_csv(csv_file, index=False)

    dataset = Dataset(
        id=uuid4(),
        project_id=project.id,
        file_path=str(csv_file),
        version_number=1,
        row_count=n_samples,
        column_count=3,
        stage="SPLIT",
    )
    db_session.add(dataset)
    db_session.commit()

    # 80 Dev, 20 Locked Test
    dev_uids = [f"row_reg_{i}" for i in range(80)]
    test_uids = [f"row_reg_{i}" for i in range(80, 100)]

    dev_split = DatasetSplit(
        id=uuid4(),
        dataset_id=dataset.id,
        split_type="DEVELOPMENT",
        split_seed=42,
        row_indices=dev_uids,
    )
    test_split = DatasetSplit(
        id=uuid4(),
        dataset_id=dataset.id,
        split_type="LOCKED_TEST",
        split_seed=42,
        row_indices=test_uids,
    )
    db_session.add(dev_split)
    db_session.add(test_split)

    # Transformation config
    for col in ["sqft", "beds"]:
        tc = TransformationConfig(
            id=uuid4(),
            project_id=project.id,
            column_name=col,
            missing_value_strategy="MEAN",
            scaling_strategy="STANDARD",
            encoding_strategy=None,
            outlier_strategy="NONE",
            is_active=True,
        )
        db_session.add(tc)
    db_session.commit()

    return {
        "user": user,
        "project": project,
        "dataset": dataset,
        "dev_split": dev_split,
        "test_split": test_split,
        "df": df,
    }


@pytest.fixture
def classification_cv_setup(db_session, create_test_user, tmp_path):
    """Sets up a complete classification dataset, outer split, and experiment for Stratified CV testing."""
    user = create_test_user("cv_tester_clf@studio.ml", "ADMIN")

    project = Project(
        id=uuid4(),
        owner_id=user.id,
        project_name="Churn CV Classification",
        task_type="CLASSIFICATION",
        target_column="churn",
        pipeline_stage="TRANSFORMED",
    )
    db_session.add(project)
    db_session.commit()

    # Generate synthetic binary classification dataset
    np.random.seed(123)
    n_samples = 120
    age = np.random.uniform(18, 70, n_samples)
    balance = np.random.uniform(0, 50000, n_samples)
    # Balanced classes (60 zeros, 60 ones)
    churn = np.array([0] * 60 + [1] * 60)
    np.random.shuffle(churn)

    df = pd.DataFrame({
        "age": age,
        "balance": balance,
        "churn": churn,
    })
    df["row_uid"] = [f"row_clf_{i}" for i in range(n_samples)]

    csv_file = tmp_path / "churn_cv.csv"
    df.to_csv(csv_file, index=False)

    dataset = Dataset(
        id=uuid4(),
        project_id=project.id,
        file_path=str(csv_file),
        version_number=1,
        row_count=n_samples,
        column_count=3,
        stage="SPLIT",
    )
    db_session.add(dataset)
    db_session.commit()

    dev_uids = [f"row_clf_{i}" for i in range(96)]
    test_uids = [f"row_clf_{i}" for i in range(96, 120)]

    dev_split = DatasetSplit(
        id=uuid4(),
        dataset_id=dataset.id,
        split_type="DEVELOPMENT",
        split_seed=42,
        row_indices=dev_uids,
    )
    test_split = DatasetSplit(
        id=uuid4(),
        dataset_id=dataset.id,
        split_type="LOCKED_TEST",
        split_seed=42,
        row_indices=test_uids,
    )
    db_session.add(dev_split)
    db_session.add(test_split)

    for col in ["age", "balance"]:
        tc = TransformationConfig(
            id=uuid4(),
            project_id=project.id,
            column_name=col,
            missing_value_strategy="MEAN",
            scaling_strategy="ROBUST",
            encoding_strategy=None,
            outlier_strategy="NONE",
            is_active=True,
        )
        db_session.add(tc)
    db_session.commit()

    return {
        "user": user,
        "project": project,
        "dataset": dataset,
        "dev_split": dev_split,
        "test_split": test_split,
        "df": df,
    }


def test_prepare_cv_context_loads_frozen_config(db_session, regression_cv_setup):
    """
    Test that prepare_experiment_cv_context loads all parameters directly
    from the frozen experiment_config.
    """
    project = regression_cv_setup["project"]
    service = ExperimentService(db_session)

    exp = service.exp_repo.create_experiment(
        project_id=project.id,
        task_type="REGRESSION",
        status=ExperimentState.CREATED.value,
    )

    # Freeze config
    service.freeze_experiment_config(
        exp.id,
        config_override={
            "algorithms": ["LinearRegression", "Ridge"],
            "folds": 4,
            "seed": 777,
            "selection_metric": "rmse",
            "selection_direction": "MINIMIZE",
        },
    )

    ctx = service.prepare_experiment_cv_context(exp.id)

    assert ctx["experiment_config"] is not None
    assert ctx["experiment_config"]["task_type"] == "REGRESSION"
    assert ctx["experiment_config"]["target"] == "price"
    assert ctx["fold_count"] == 4
    assert ctx["cv_seed"] == 777
    assert ctx["cv_strategy"] == "KFOLD"
    assert ctx["candidate_cols"] == ["sqft", "beds"]


def test_dev_data_loaded_strictly_by_row_uid_zero_locked_test_leakage(db_session, regression_cv_setup):
    """
    Test that dev_df contains exactly the row_uids assigned to the Development partition,
    and has 0% overlap with the Locked Test partition.
    """
    project = regression_cv_setup["project"]
    test_split = regression_cv_setup["test_split"]
    service = ExperimentService(db_session)

    exp = service.exp_repo.create_experiment(
        project_id=project.id,
        task_type="REGRESSION",
        status=ExperimentState.CREATED.value,
    )
    service.freeze_experiment_config(exp.id, config_override={"folds": 5, "seed": 42})

    ctx = service.prepare_experiment_cv_context(exp.id)
    dev_df = ctx["dev_df"]

    assert len(dev_df) == 80
    dev_uids = set(dev_df["row_uid"])
    test_uids = set(test_split.row_indices)

    # Invariant: Strict zero overlap between dev data and locked test partition
    assert len(dev_uids.intersection(test_uids)) == 0


def test_regression_cv_splits_kfold_and_zero_leakage(db_session, regression_cv_setup):
    """
    Test that KFold inner CV splits partition Development data with exact fold counts
    and strict zero leakage across fold slices.
    """
    project = regression_cv_setup["project"]
    service = ExperimentService(db_session)

    exp = service.exp_repo.create_experiment(
        project_id=project.id,
        task_type="REGRESSION",
        status=ExperimentState.CREATED.value,
    )
    service.freeze_experiment_config(exp.id, config_override={"folds": 5, "seed": 42})

    ctx = service.prepare_experiment_cv_context(exp.id)
    fold_splits = ctx["fold_splits"]

    assert len(fold_splits) == 5

    total_dev_rows = len(ctx["dev_df"])
    for fold in fold_splits:
        train_idx = fold["train_indices"]
        val_idx = fold["val_indices"]

        # 1. Total samples equal dev dataset size
        assert len(train_idx) + len(val_idx) == total_dev_rows
        # 2. Strict Zero Leakage: No shared row indices between train and val
        assert len(set(train_idx).intersection(set(val_idx))) == 0
        # 3. Row UIDs correspond correctly
        assert len(set(fold["train_row_uids"]).intersection(set(fold["val_row_uids"]))) == 0


def test_classification_cv_splits_stratified_kfold(db_session, classification_cv_setup):
    """
    Test StratifiedKFold for Classification tasks, ensuring class distributions
    are preserved across train and validation folds.
    """
    project = classification_cv_setup["project"]
    service = ExperimentService(db_session)

    exp = service.exp_repo.create_experiment(
        project_id=project.id,
        task_type="CLASSIFICATION",
        status=ExperimentState.CREATED.value,
    )
    service.freeze_experiment_config(
        exp.id,
        config_override={
            "algorithms": ["LogisticRegression", "RandomForestClassifier"],
            "folds": 4,
            "seed": 99,
        },
    )

    ctx = service.prepare_experiment_cv_context(exp.id)
    assert ctx["cv_strategy"] == "STRATIFIED_KFOLD"
    assert len(ctx["fold_splits"]) == 4

    y_raw = ctx["y_raw"]
    for fold in ctx["fold_splits"]:
        train_y = y_raw.iloc[fold["train_indices"]]
        val_y = y_raw.iloc[fold["val_indices"]]

        # Verify class proportions are roughly equal in train and val folds
        train_pos_rate = np.mean(train_y == 1)
        val_pos_rate = np.mean(val_y == 1)
        assert abs(train_pos_rate - val_pos_rate) < 0.15

        # Zero leakage check
        assert len(set(fold["train_indices"]).intersection(set(fold["val_indices"]))) == 0


def test_cv_splits_deterministic_reproducibility(db_session, regression_cv_setup):
    """
    Test that calling prepare_experiment_cv_context multiple times with the same seed
    yields 100% identical fold index partitions.
    """
    project = regression_cv_setup["project"]
    service = ExperimentService(db_session)

    exp1 = service.exp_repo.create_experiment(
        project_id=project.id,
        task_type="REGRESSION",
        status=ExperimentState.CREATED.value,
    )
    service.freeze_experiment_config(exp1.id, config_override={"folds": 5, "seed": 54321})

    exp2 = service.exp_repo.create_experiment(
        project_id=project.id,
        task_type="REGRESSION",
        status=ExperimentState.CREATED.value,
    )
    service.freeze_experiment_config(exp2.id, config_override={"folds": 5, "seed": 54321})

    ctx1 = service.prepare_experiment_cv_context(exp1.id)
    ctx2 = service.prepare_experiment_cv_context(exp2.id)

    for f1, f2 in zip(ctx1["fold_splits"], ctx2["fold_splits"]):
        assert np.array_equal(f1["train_indices"], f2["train_indices"])
        assert np.array_equal(f1["val_indices"], f2["val_indices"])
        assert f1["train_row_uids"] == f2["train_row_uids"]
        assert f1["val_row_uids"] == f2["val_row_uids"]


def test_insufficient_samples_raises_400(db_session, regression_cv_setup):
    """
    Test that requesting more folds than available samples raises HTTP 400.
    """
    project = regression_cv_setup["project"]
    service = ExperimentService(db_session)

    exp = service.exp_repo.create_experiment(
        project_id=project.id,
        task_type="REGRESSION",
        status=ExperimentState.CREATED.value,
    )
    # Set folds = 100 while dev set has 80 samples
    exp.experiment_config = {
        "task_type": "REGRESSION",
        "target": "price",
        "cv": {"folds": 100, "seed": 42},
    }
    db_session.add(exp)
    db_session.commit()

    with pytest.raises(HTTPException) as exc_info:
        service.prepare_experiment_cv_context(exp.id)
    assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
    assert "Insufficient samples" in exc_info.value.detail


def test_missing_target_column_raises_400(db_session, regression_cv_setup):
    """
    Test that a configured target column missing from the Development data raises HTTP 400.
    """
    project = regression_cv_setup["project"]
    service = ExperimentService(db_session)

    exp = service.exp_repo.create_experiment(
        project_id=project.id,
        task_type="REGRESSION",
        status=ExperimentState.CREATED.value,
    )
    exp.experiment_config = {
        "task_type": "REGRESSION",
        "target": "non_existent_target_col",
        "cv": {"folds": 5, "seed": 42},
    }
    db_session.add(exp)
    db_session.commit()

    with pytest.raises(HTTPException) as exc_info:
        service.prepare_experiment_cv_context(exp.id)
    assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
    assert "non_existent_target_col" in exc_info.value.detail
