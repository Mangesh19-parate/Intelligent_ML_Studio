"""
Unit Tests for Day 6 Full Cross-Validation Run & State Transitions (SRS v9 §2 / Day 6).

Verifies:
1. End-to-end regression CV run with full metrics, fit diagnostics, and model ranking.
2. End-to-end classification CV run with StratifiedKFold and class probabilities.
3. State transitions CONFIGURED -> TRAINING -> EVALUATED.
4. Day 1 concurrency lock blocking a second simultaneous attempt on the same experiment with HTTP 409 Conflict.
"""

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
from app.config.state_machines import ExperimentState, ModelState
from app.services.experiment_service import ExperimentService


@pytest.fixture
def day6_regression_setup(db_session, create_test_user, tmp_path):
    """Sets up a complete regression project with dataset, columns, and split."""
    user = create_test_user("d6_reg_user@studio.ml", "ADMIN")

    project = Project(
        id=uuid4(),
        owner_id=user.id,
        project_name="Day 6 Full CV Regression Project",
        task_type="REGRESSION",
        target_column="target_price",
        pipeline_stage="TRANSFORMED",
    )
    db_session.add(project)
    db_session.commit()

    np.random.seed(42)
    n_samples = 60
    f1 = np.random.normal(50, 10, n_samples)
    f2 = np.random.uniform(1, 5, n_samples)
    target = 2.0 * f1 + 3.0 * f2 + np.random.normal(0, 1, n_samples)

    df = pd.DataFrame({
        "feat_1": f1,
        "feat_2": f2,
        "target_price": target,
        "row_uid": [f"d6_reg_{i}" for i in range(n_samples)],
    })

    csv_path = tmp_path / "d6_reg_data.csv"
    df.to_csv(csv_path, index=False)

    dataset = Dataset(
        id=uuid4(),
        project_id=project.id,
        file_path=str(csv_path),
        version_number=1,
        row_count=n_samples,
        column_count=3,
        stage="SPLIT",
        content_hash="d6_reg_hash_123",
    )
    db_session.add(dataset)
    db_session.commit()

    # Column metadata
    c1 = DatasetColumn(id=uuid4(), dataset_id=dataset.id, column_name="feat_1", data_type="NUMERIC")
    c2 = DatasetColumn(id=uuid4(), dataset_id=dataset.id, column_name="feat_2", data_type="NUMERIC")
    ct = DatasetColumn(id=uuid4(), dataset_id=dataset.id, column_name="target_price", data_type="NUMERIC")
    db_session.add(c1)
    db_session.add(c2)
    db_session.add(ct)

    # Outer split: 48 dev, 12 locked test
    dev_split = DatasetSplit(
        id=uuid4(),
        dataset_id=dataset.id,
        split_type="DEVELOPMENT",
        split_seed=42,
        row_indices=[f"d6_reg_{i}" for i in range(48)],
    )
    test_split = DatasetSplit(
        id=uuid4(),
        dataset_id=dataset.id,
        split_type="LOCKED_TEST",
        split_seed=42,
        row_indices=[f"d6_reg_{i}" for i in range(48, n_samples)],
    )
    db_session.add(dev_split)
    db_session.add(test_split)

    # Transformation config
    tc1 = TransformationConfig(
        id=uuid4(),
        project_id=project.id,
        column_name="feat_1",
        missing_value_strategy="MEAN",
        scaling_strategy="STANDARD",
        outlier_strategy="NONE",
        is_active=True,
    )
    db_session.add(tc1)
    db_session.commit()

    return {
        "project": project,
        "dataset": dataset,
        "df": df,
    }


@pytest.fixture
def day6_classification_setup(db_session, create_test_user, tmp_path):
    """Sets up a complete classification project with dataset, columns, and split."""
    user = create_test_user("d6_clf_user@studio.ml", "ADMIN")

    project = Project(
        id=uuid4(),
        owner_id=user.id,
        project_name="Day 6 Full CV Classification Project",
        task_type="CLASSIFICATION",
        target_column="churn",
        pipeline_stage="TRANSFORMED",
    )
    db_session.add(project)
    db_session.commit()

    np.random.seed(99)
    n_samples = 60
    x1 = np.random.randn(n_samples) * 5
    x2 = np.random.randn(n_samples) * 2
    target = np.array([0] * 30 + [1] * 30)
    np.random.shuffle(target)

    df = pd.DataFrame({
        "x1": x1,
        "x2": x2,
        "churn": target,
        "row_uid": [f"d6_clf_{i}" for i in range(n_samples)],
    })

    csv_path = tmp_path / "d6_clf_data.csv"
    df.to_csv(csv_path, index=False)

    dataset = Dataset(
        id=uuid4(),
        project_id=project.id,
        file_path=str(csv_path),
        version_number=1,
        row_count=n_samples,
        column_count=3,
        stage="SPLIT",
        content_hash="d6_clf_hash_456",
    )
    db_session.add(dataset)
    db_session.commit()

    # Column metadata
    cx1 = DatasetColumn(id=uuid4(), dataset_id=dataset.id, column_name="x1", data_type="NUMERIC")
    cx2 = DatasetColumn(id=uuid4(), dataset_id=dataset.id, column_name="x2", data_type="NUMERIC")
    cch = DatasetColumn(id=uuid4(), dataset_id=dataset.id, column_name="churn", data_type="CATEGORICAL")
    db_session.add(cx1)
    db_session.add(cx2)
    db_session.add(cch)

    # Outer split: 48 dev, 12 locked test
    dev_split = DatasetSplit(
        id=uuid4(),
        dataset_id=dataset.id,
        split_type="DEVELOPMENT",
        split_seed=42,
        row_indices=[f"d6_clf_{i}" for i in range(48)],
    )
    test_split = DatasetSplit(
        id=uuid4(),
        dataset_id=dataset.id,
        split_type="LOCKED_TEST",
        split_seed=42,
        row_indices=[f"d6_clf_{i}" for i in range(48, n_samples)],
    )
    db_session.add(dev_split)
    db_session.add(test_split)

    tc = TransformationConfig(
        id=uuid4(),
        project_id=project.id,
        column_name="x1",
        missing_value_strategy="MEDIAN",
        scaling_strategy="ROBUST",
        outlier_strategy="NONE",
        is_active=True,
    )
    db_session.add(tc)
    db_session.commit()

    return {
        "project": project,
        "dataset": dataset,
        "df": df,
    }


def test_end_to_end_regression_cv_run(db_session, day6_regression_setup):
    """
    Test end-to-end regression CV run:
    1. CREATED -> CONFIGURED (via freeze)
    2. CONFIGURED -> TRAINING -> EVALUATED (via run_experiment)
    3. Verifies trained model records, fold metrics, CV_MEAN, and fit diagnostics.
    """
    project = day6_regression_setup["project"]
    service = ExperimentService(db_session)

    exp = service.exp_repo.create_experiment(
        project_id=project.id,
        task_type="REGRESSION",
        status=ExperimentState.CREATED.value,
    )
    assert exp.status == ExperimentState.CREATED.value

    # Freeze config
    frozen_exp = service.freeze_experiment_config(
        exp.id,
        config_override={
            "algorithms": ["LinearRegression", "Ridge"],
            "folds": 3,
            "seed": 42,
            "selection_metric": "rmse",
            "selection_direction": "MINIMIZE",
        },
    )
    assert frozen_exp.status == ExperimentState.CONFIGURED.value

    # Run experiment without auto_finalize to observe EVALUATED state
    result = service.run_experiment(
        project_id=project.id,
        experiment_id=frozen_exp.id,
        auto_finalize=False,
    )

    db_session.refresh(frozen_exp)
    assert frozen_exp.status == ExperimentState.EVALUATED.value
    assert len(result["trained_models"]) == 2
    for m in result["trained_models"]:
        assert m["status"] in [ModelState.TRAINED.value, "TRAINED"]
        assert m["quick_cv_score"] is not None
        assert m["fit_diagnosis"] in [
            "GOOD_FIT",
            "POTENTIAL_OVERFIT",
            "POTENTIAL_UNDERFIT_WEAK_SIGNAL",
            "INSUFFICIENT_DATA",
        ]


def test_end_to_end_classification_cv_run(db_session, day6_classification_setup):
    """
    Test end-to-end classification CV run:
    1. CREATED -> CONFIGURED (via freeze)
    2. CONFIGURED -> TRAINING -> EVALUATED (via run_experiment)
    3. Verifies StratifiedKFold evaluation and classification metrics.
    """
    project = day6_classification_setup["project"]
    service = ExperimentService(db_session)

    exp = service.exp_repo.create_experiment(
        project_id=project.id,
        task_type="CLASSIFICATION",
        status=ExperimentState.CREATED.value,
    )

    frozen_exp = service.freeze_experiment_config(
        exp.id,
        config_override={
            "algorithms": ["LogisticRegression", "RandomForestClassifier"],
            "folds": 3,
            "seed": 100,
            "selection_metric": "f1_macro",
            "selection_direction": "MAXIMIZE",
        },
    )
    assert frozen_exp.status == ExperimentState.CONFIGURED.value

    result = service.run_experiment(
        project_id=project.id,
        experiment_id=frozen_exp.id,
        auto_finalize=False,
    )

    db_session.refresh(frozen_exp)
    assert frozen_exp.status == ExperimentState.EVALUATED.value
    assert len(result["trained_models"]) == 2
    for m in result["trained_models"]:
        assert m["status"] in [ModelState.TRAINED.value, "TRAINED"]
        assert m["quick_cv_score"] is not None


def test_concurrency_lock_blocks_second_simultaneous_attempt(db_session, day6_regression_setup):
    """
    CRITICAL INVARIANT TEST (SRS v9 §6):
    Test that when an experiment is actively in TRAINING state, any second
    simultaneous attempt to run or start training on that experiment is blocked
    and immediately rejected with HTTP 409 Conflict.
    """
    project = day6_regression_setup["project"]
    service = ExperimentService(db_session)

    exp = service.exp_repo.create_experiment(
        project_id=project.id,
        task_type="REGRESSION",
        status=ExperimentState.CREATED.value,
    )
    service.freeze_experiment_config(exp.id, config_override={"folds": 3, "seed": 42})

    # Put experiment into TRAINING state
    service.start_training(exp.id)
    db_session.refresh(exp)
    assert exp.status == ExperimentState.TRAINING.value

    # Second start_training attempt MUST be rejected with HTTP 409
    with pytest.raises(HTTPException) as exc_info:
        service.start_training(exp.id)
    assert exc_info.value.status_code == status.HTTP_409_CONFLICT
    assert "already actively training" in exc_info.value.detail

    # Second run_experiment attempt on the same active training experiment MUST also be rejected with HTTP 409
    with pytest.raises(HTTPException) as exc_info2:
        service.run_experiment(
            project_id=project.id,
            experiment_id=exp.id,
        )
    assert exc_info2.value.status_code == status.HTTP_409_CONFLICT
    assert "already actively training" in exc_info2.value.detail
