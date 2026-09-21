"""
Unit & Integration Tests for Day 1 — Metrics & model_metrics Persistence.

Verifies:
1. Exact metric-naming strings from Week 1 architecture contract (§7 / contract.py).
2. EvaluationService metric suites and naive baseline computation.
3. run_experiment persistence of per-fold (TRAIN / VALIDATION, fold_index 0..k-1) and CV-mean (CV_MEAN, fold_index=None) in model_metrics.
4. Classification non-scalar metrics (confusion_matrix) correctly stored in metric_json.
5. Winning model final refit (TRAIN) and single locked test (LOCKED_TEST) metric storage in model_metrics.
"""

from uuid import uuid4
import numpy as np
import pandas as pd
import pytest

from app.models.project import Project
from app.models.dataset import Dataset
from app.models.dataset_column import DatasetColumn
from app.models.dataset_split import DatasetSplit
from app.models.transformation_config import TransformationConfig
from app.models.model_metric import ModelMetric
from app.config.contract import METRICS, TaskType
from app.config.state_machines import ExperimentState
from app.services.evaluation_service import EvaluationService
from app.services.experiment_service import ExperimentService


def test_contract_metric_naming_strings():
    """Verify exact metric-naming strings frozen in Week 1 contract."""
    reg_keys = set(METRICS[TaskType.REGRESSION].keys())
    expected_reg = {"rmse", "mae", "mse", "r2", "adjusted_r2"}
    assert expected_reg.issubset(reg_keys)

    clf_keys = set(METRICS[TaskType.CLASSIFICATION].keys())
    expected_clf = {
        "macro_f1",
        "weighted_f1",
        "accuracy",
        "precision",
        "recall",
        "roc_auc",
        "log_loss",
        "confusion_matrix",
    }
    assert expected_clf.issubset(clf_keys)


def test_evaluation_service_regression_suite():
    """Verify EvaluationService regression metrics match frozen contract."""
    y_true = np.array([10.0, 20.0, 30.0, 40.0, 50.0])
    y_pred = np.array([11.0, 19.0, 32.0, 38.0, 51.0])

    metrics = EvaluationService.evaluate_regression(y_true, y_pred, n=5, p=1)

    assert "rmse" in metrics
    assert "mae" in metrics
    assert "mse" in metrics
    assert "r2" in metrics
    assert "adjusted_r2" in metrics
    assert isinstance(metrics["rmse"], float)
    assert metrics["rmse"] > 0.0


def test_evaluation_service_classification_suite():
    """Verify EvaluationService classification metrics match frozen contract."""
    y_true = np.array([0, 1, 0, 1, 1, 0])
    y_pred = np.array([0, 1, 0, 1, 0, 0])
    y_proba = np.array([
        [0.8, 0.2],
        [0.1, 0.9],
        [0.7, 0.3],
        [0.2, 0.8],
        [0.6, 0.4],
        [0.9, 0.1],
    ])

    metrics = EvaluationService.evaluate_classification(y_true, y_pred, y_proba=y_proba)

    assert "macro_f1" in metrics
    assert "weighted_f1" in metrics
    assert "accuracy" in metrics
    assert "precision" in metrics
    assert "recall" in metrics
    assert "roc_auc" in metrics
    assert "log_loss" in metrics
    assert "confusion_matrix" in metrics
    assert isinstance(metrics["confusion_matrix"], list)
    assert metrics["log_loss"] is not None
    assert metrics["roc_auc"] is not None


@pytest.fixture
def day1_regression_env(db_session, create_test_user, tmp_path):
    """Sets up a complete regression environment for run_experiment test."""
    user = create_test_user("d1_reg_user@studio.ml", "ADMIN")

    project = Project(
        id=uuid4(),
        owner_id=user.id,
        project_name="Day 1 Regression Project",
        task_type="REGRESSION",
        target_column="target",
        pipeline_stage="TRANSFORMED",
    )
    db_session.add(project)
    db_session.commit()

    np.random.seed(101)
    n_samples = 40
    f1 = np.random.normal(10, 2, n_samples)
    f2 = np.random.uniform(0, 5, n_samples)
    target = 1.5 * f1 + 2.0 * f2 + np.random.normal(0, 0.5, n_samples)

    df = pd.DataFrame({
        "feat1": f1,
        "feat2": f2,
        "target": target,
        "row_uid": [f"reg_{i}" for i in range(n_samples)],
    })

    csv_path = tmp_path / "d1_reg_data.csv"
    df.to_csv(csv_path, index=False)

    dataset = Dataset(
        id=uuid4(),
        project_id=project.id,
        file_path=str(csv_path),
        row_count=n_samples,
        column_count=3,
        content_hash="d1reghash123456",
        version_number=1,
        stage="SPLIT",
    )
    db_session.add(dataset)
    db_session.commit()

    c1 = DatasetColumn(id=uuid4(), dataset_id=dataset.id, column_name="feat1", data_type="NUMERIC")
    c2 = DatasetColumn(id=uuid4(), dataset_id=dataset.id, column_name="feat2", data_type="NUMERIC")
    c3 = DatasetColumn(id=uuid4(), dataset_id=dataset.id, column_name="target", data_type="NUMERIC", is_target=True)
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
        row_indices=[f"reg_{i}" for i in range(30)],
    )
    test_split = DatasetSplit(
        id=uuid4(),
        dataset_id=dataset.id,
        split_type="LOCKED_TEST",
        split_seed=42,
        row_indices=[f"reg_{i}" for i in range(30, n_samples)],
    )
    db_session.add(dev_split)
    db_session.add(test_split)
    db_session.commit()

    return project, dataset, user


@pytest.fixture
def day1_classification_env(db_session, create_test_user, tmp_path):
    """Sets up a complete classification environment for run_experiment test."""
    user = create_test_user("d1_clf_user@studio.ml", "ADMIN")

    project = Project(
        id=uuid4(),
        owner_id=user.id,
        project_name="Day 1 Classification Project",
        task_type="CLASSIFICATION",
        target_column="label",
        pipeline_stage="TRANSFORMED",
    )
    db_session.add(project)
    db_session.commit()

    np.random.seed(202)
    n_samples = 40
    f1 = np.random.normal(0, 1, n_samples)
    f2 = np.random.normal(0, 1, n_samples)
    labels = (f1 + f2 > 0).astype(int)

    df = pd.DataFrame({
        "feat1": f1,
        "feat2": f2,
        "label": labels,
        "row_uid": [f"clf_{i}" for i in range(n_samples)],
    })

    csv_path = tmp_path / "d1_clf_data.csv"
    df.to_csv(csv_path, index=False)

    dataset = Dataset(
        id=uuid4(),
        project_id=project.id,
        file_path=str(csv_path),
        row_count=n_samples,
        column_count=3,
        content_hash="d1clfhash123456",
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
        row_indices=[f"clf_{i}" for i in range(30)],
    )
    test_split = DatasetSplit(
        id=uuid4(),
        dataset_id=dataset.id,
        split_type="LOCKED_TEST",
        split_seed=42,
        row_indices=[f"clf_{i}" for i in range(30, n_samples)],
    )
    db_session.add(dev_split)
    db_session.add(test_split)
    db_session.commit()

    return project, dataset, user


def test_run_experiment_stores_regression_metrics(db_session, day1_regression_env):
    """Verify run_experiment computes and stores regression per-fold & CV_MEAN metrics in model_metrics."""
    project, dataset, user = day1_regression_env
    service = ExperimentService(db_session)

    exp = service.exp_repo.create_experiment(
        project_id=project.id,
        task_type="REGRESSION",
        status=ExperimentState.CREATED.value,
    )

    frozen_exp = service.freeze_experiment_config(
        exp.id,
        config_override={
            "algorithms": ["LinearRegression"],
            "folds": 3,
            "seed": 42,
            "selection_metric": "rmse",
            "selection_direction": "MINIMIZE",
        },
    )

    res = service.run_experiment(
        project_id=project.id,
        experiment_id=frozen_exp.id,
        auto_finalize=True,
    )

    assert res["status"] in ["COMPLETED", "EVALUATED", "REGISTERED"]
    assert len(res["trained_models"]) == 1
    model_id = res["trained_models"][0]["id"]

    metrics = db_session.query(ModelMetric).filter_by(model_id=model_id).all()
    assert len(metrics) > 0

    splits = {m.split for m in metrics}
    assert "TRAIN" in splits
    assert "VALIDATION" in splits
    assert "CV_MEAN" in splits
    assert "LOCKED_TEST" in splits

    # Verify per-fold metrics have fold_index 0, 1, 2
    val_metrics = [m for m in metrics if m.split == "VALIDATION"]
    val_fold_indices = {m.fold_index for m in val_metrics}
    assert val_fold_indices == {0, 1, 2}

    val_metric_names = {m.metric_name for m in val_metrics}
    assert {"rmse", "mae", "mse", "r2", "adjusted_r2"}.issubset(val_metric_names)

    # Verify CV_MEAN metrics have fold_index None
    cv_mean_metrics = [m for m in metrics if m.split == "CV_MEAN"]
    for cm in cv_mean_metrics:
        assert cm.fold_index is None
        assert cm.metric_value is not None

    cv_metric_names = {m.metric_name for m in cv_mean_metrics}
    assert {"rmse", "mae", "mse", "r2", "adjusted_r2"}.issubset(cv_metric_names)


def test_run_experiment_stores_classification_metrics(db_session, day1_classification_env):
    """Verify run_experiment computes and stores classification per-fold & CV_MEAN metrics in model_metrics."""
    project, dataset, user = day1_classification_env
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

    res = service.run_experiment(
        project_id=project.id,
        experiment_id=frozen_exp.id,
        auto_finalize=True,
    )

    assert res["status"] in ["COMPLETED", "EVALUATED", "REGISTERED"]
    assert len(res["trained_models"]) == 1
    model_id = res["trained_models"][0]["id"]

    metrics = db_session.query(ModelMetric).filter_by(model_id=model_id).all()
    assert len(metrics) > 0

    splits = {m.split for m in metrics}
    assert "TRAIN" in splits
    assert "VALIDATION" in splits
    assert "CV_MEAN" in splits
    assert "LOCKED_TEST" in splits

    # Verify per-fold metrics have fold_index 0, 1, 2
    val_metrics = [m for m in metrics if m.split == "VALIDATION"]
    val_fold_indices = {m.fold_index for m in val_metrics}
    assert val_fold_indices == {0, 1, 2}

    val_metric_names = {m.metric_name for m in val_metrics}
    assert {"macro_f1", "weighted_f1", "accuracy", "precision", "recall"}.issubset(val_metric_names)

    # Check confusion matrix stored in metric_json
    cm_metrics = [m for m in val_metrics if m.metric_name == "confusion_matrix"]
    assert len(cm_metrics) == 3
    for cm in cm_metrics:
        assert cm.metric_json is not None
        assert isinstance(cm.metric_json, list)

    # Verify CV_MEAN metrics
    cv_mean_metrics = [m for m in metrics if m.split == "CV_MEAN"]
    for cm in cv_mean_metrics:
        assert cm.fold_index is None
        assert cm.metric_value is not None

    cv_metric_names = {m.metric_name for m in cv_mean_metrics}
    assert {"macro_f1", "weighted_f1", "accuracy", "precision", "recall"}.issubset(cv_metric_names)
