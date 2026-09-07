"""
Unit Tests for Day 4 Pipeline Construction & Per-Fold Independent Refitting (SRS v9 §2 / Day 4).

Verifies:
1. Full Pipeline assembly: ('transformer', ColumnTransformer), ('selector', FeatureSelector), ('estimator', BaseEstimator).
2. Independent transformer refitting per fold (learned scaler means/variances/imputations match training slices only).
3. Independent selector refitting per fold.
4. End-to-end execution of run_experiment_fold_pipelines for both Regression and Classification.
5. Zero test leakage across fold transformations.
"""

from uuid import uuid4
import numpy as np
import pandas as pd
import pytest
from sklearn.dummy import DummyRegressor, DummyClassifier
from sklearn.linear_model import LinearRegression, LogisticRegression
from sklearn.pipeline import Pipeline

from app.models.project import Project
from app.models.dataset import Dataset
from app.models.dataset_column import DatasetColumn
from app.models.dataset_split import DatasetSplit
from app.models.transformation_config import TransformationConfig
from app.models.experiment import Experiment
from app.config.state_machines import ExperimentState
from app.services.experiment_service import ExperimentService
from app.services.trainers import FeatureSelector


@pytest.fixture
def pipeline_regression_setup(db_session, create_test_user, tmp_path):
    """Sets up a project with transformation configs, columns, and outer split."""
    user = create_test_user("pipe_tester@studio.ml", "ADMIN")

    project = Project(
        id=uuid4(),
        owner_id=user.id,
        project_name="Pipeline Construction Reg Project",
        task_type="REGRESSION",
        target_column="target_val",
        pipeline_stage="TRANSFORMED",
    )
    db_session.add(project)
    db_session.commit()

    # Create dataset with distinct values per row so fold statistics differ
    np.random.seed(42)
    n_samples = 100
    feat_a = np.linspace(10.0, 500.0, n_samples) + np.random.randn(n_samples) * 5.0
    feat_b = np.random.uniform(1.0, 10.0, n_samples)
    target = 3.0 * feat_a + 2.0 * feat_b + np.random.randn(n_samples)

    df = pd.DataFrame({
        "feat_a": feat_a,
        "feat_b": feat_b,
        "target_val": target,
        "row_uid": [f"pipe_reg_{i}" for i in range(n_samples)],
    })

    csv_path = tmp_path / "pipe_reg_data.csv"
    df.to_csv(csv_path, index=False)

    dataset = Dataset(
        id=uuid4(),
        project_id=project.id,
        file_path=str(csv_path),
        version_number=1,
        row_count=n_samples,
        column_count=3,
        stage="SPLIT",
    )
    db_session.add(dataset)
    db_session.commit()

    # Add DatasetColumn records so build_pipeline detects column metadata
    col_a = DatasetColumn(id=uuid4(), dataset_id=dataset.id, column_name="feat_a", data_type="NUMERIC")
    col_b = DatasetColumn(id=uuid4(), dataset_id=dataset.id, column_name="feat_b", data_type="NUMERIC")
    col_t = DatasetColumn(id=uuid4(), dataset_id=dataset.id, column_name="target_val", data_type="NUMERIC")
    db_session.add(col_a)
    db_session.add(col_b)
    db_session.add(col_t)

    dev_uids = [f"pipe_reg_{i}" for i in range(80)]
    test_uids = [f"pipe_reg_{i}" for i in range(80, 100)]

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

    # Add Standard Scaler to feat_a, MinMax to feat_b
    tc_a = TransformationConfig(
        id=uuid4(),
        project_id=project.id,
        column_name="feat_a",
        missing_value_strategy="MEAN",
        scaling_strategy="STANDARD",
        encoding_strategy=None,
        outlier_strategy="NONE",
        is_active=True,
    )
    tc_b = TransformationConfig(
        id=uuid4(),
        project_id=project.id,
        column_name="feat_b",
        missing_value_strategy="MEDIAN",
        scaling_strategy="MINMAX",
        encoding_strategy=None,
        outlier_strategy="NONE",
        is_active=True,
    )
    db_session.add(tc_a)
    db_session.add(tc_b)
    db_session.commit()

    return {
        "project": project,
        "dataset": dataset,
        "df": df,
    }


@pytest.fixture
def pipeline_classification_setup(db_session, create_test_user, tmp_path):
    """Sets up a classification project with preprocessing."""
    user = create_test_user("pipe_tester_clf@studio.ml", "ADMIN")

    project = Project(
        id=uuid4(),
        owner_id=user.id,
        project_name="Pipeline Construction Clf Project",
        task_type="CLASSIFICATION",
        target_column="label",
        pipeline_stage="TRANSFORMED",
    )
    db_session.add(project)
    db_session.commit()

    np.random.seed(99)
    n_samples = 100
    x1 = np.random.randn(n_samples) * 10
    x2 = np.random.randn(n_samples) * 5
    label = np.array([0] * 50 + [1] * 50)
    np.random.shuffle(label)

    df = pd.DataFrame({
        "x1": x1,
        "x2": x2,
        "label": label,
        "row_uid": [f"pipe_clf_{i}" for i in range(n_samples)],
    })

    csv_path = tmp_path / "pipe_clf_data.csv"
    df.to_csv(csv_path, index=False)

    dataset = Dataset(
        id=uuid4(),
        project_id=project.id,
        file_path=str(csv_path),
        version_number=1,
        row_count=n_samples,
        column_count=3,
        stage="SPLIT",
    )
    db_session.add(dataset)
    db_session.commit()

    # Add DatasetColumn records
    col_x1 = DatasetColumn(id=uuid4(), dataset_id=dataset.id, column_name="x1", data_type="NUMERIC")
    col_x2 = DatasetColumn(id=uuid4(), dataset_id=dataset.id, column_name="x2", data_type="NUMERIC")
    col_l = DatasetColumn(id=uuid4(), dataset_id=dataset.id, column_name="label", data_type="CATEGORICAL")
    db_session.add(col_x1)
    db_session.add(col_x2)
    db_session.add(col_l)

    dev_uids = [f"pipe_clf_{i}" for i in range(80)]
    test_uids = [f"pipe_clf_{i}" for i in range(80, 100)]

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

    tc = TransformationConfig(
        id=uuid4(),
        project_id=project.id,
        column_name="x1",
        missing_value_strategy="MEAN",
        scaling_strategy="ROBUST",
        encoding_strategy=None,
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


def test_build_fold_pipeline_structure(db_session, pipeline_regression_setup):
    """
    Test that build_fold_pipeline correctly constructs a Pipeline with:
    1. 'transformer'
    2. 'selector'
    3. 'estimator'
    """
    project = pipeline_regression_setup["project"]
    service = ExperimentService(db_session)

    pipeline = service.build_fold_pipeline(
        project_id=project.id,
        task_type="REGRESSION",
        selected_features=["feat_a"],
    )

    assert isinstance(pipeline, Pipeline)
    step_names = [name for name, _ in pipeline.steps]
    assert step_names == ["transformer", "selector", "estimator"]
    assert isinstance(pipeline.named_steps["selector"], FeatureSelector)
    assert pipeline.named_steps["selector"].selected_features == ["feat_a"]
    assert isinstance(pipeline.named_steps["estimator"], LinearRegression)


def test_transformer_refit_independently_per_fold(db_session, pipeline_regression_setup):
    """
    CRITICAL INVARIANT TEST:
    Verify that the ColumnTransformer is fit INDEPENDENTLY per fold.
    Learned parameters (e.g. StandardScaler mean_ on feat_a) must strictly equal
    the mean of that specific fold's training slice, and differ across folds.
    """
    project = pipeline_regression_setup["project"]
    service = ExperimentService(db_session)

    exp = service.exp_repo.create_experiment(
        project_id=project.id,
        task_type="REGRESSION",
        status=ExperimentState.CREATED.value,
    )
    service.freeze_experiment_config(exp.id, config_override={"folds": 4, "seed": 42})

    results = service.run_experiment_fold_pipelines(exp.id)
    fold_results = results["fold_results"]
    assert len(fold_results) == 4

    ctx = service.prepare_experiment_cv_context(exp.id)
    X_df = ctx["X_df"]

    learned_means = []
    for f in fold_results:
        f_idx = f["fold_index"]
        pipe = f["pipeline"]
        train_idx = ctx["fold_splits"][f_idx]["train_indices"]

        # Expected mean of feat_a on this fold's training slice
        expected_mean = float(np.mean(X_df["feat_a"].iloc[train_idx]))

        # Extract fitted StandardScaler from pipeline
        col_trans = pipe.named_steps["transformer"]
        scaler = col_trans.named_transformers_["trans_feat_a"].named_steps["scaler"]
        actual_mean = float(scaler.mean_[0])

        assert np.isclose(actual_mean, expected_mean, atol=1e-5), (
            f"Fold {f_idx} learned scaler mean {actual_mean} does not match fold train mean {expected_mean}"
        )
        learned_means.append(actual_mean)

    # Verify that means across different folds are distinct
    assert len(set(round(m, 3) for m in learned_means)) == 4, (
        "Learned transformer parameters did not vary across folds — check per-fold isolation"
    )


def test_selector_refit_independently_per_fold(db_session, pipeline_regression_setup):
    """
    Test that FeatureSelector fits properly within the pipeline on each fold.
    """
    project = pipeline_regression_setup["project"]
    service = ExperimentService(db_session)

    exp = service.exp_repo.create_experiment(
        project_id=project.id,
        task_type="REGRESSION",
        status=ExperimentState.CREATED.value,
    )
    service.freeze_experiment_config(exp.id, config_override={"folds": 3, "seed": 42})

    results = service.run_experiment_fold_pipelines(exp.id)
    for f in results["fold_results"]:
        pipe = f["pipeline"]
        selector = pipe.named_steps["selector"]
        assert hasattr(selector, "n_features_in_")
        assert selector.n_features_in_ > 0
        assert selector.selected_indices_ is not None


def test_run_experiment_fold_pipelines_classification(db_session, pipeline_classification_setup):
    """
    Test run_experiment_fold_pipelines on classification project with StratifiedKFold.
    """
    project = pipeline_classification_setup["project"]
    service = ExperimentService(db_session)

    exp = service.exp_repo.create_experiment(
        project_id=project.id,
        task_type="CLASSIFICATION",
        status=ExperimentState.CREATED.value,
    )
    service.freeze_experiment_config(exp.id, config_override={"folds": 4, "seed": 100})

    results = service.run_experiment_fold_pipelines(exp.id)
    assert results["task_type"] == "CLASSIFICATION"
    assert results["cv_strategy"] == "STRATIFIED_KFOLD"
    assert len(results["fold_results"]) == 4

    for f in results["fold_results"]:
        assert isinstance(f["pipeline"].named_steps["estimator"], LogisticRegression)
        assert len(f["y_val_pred"]) == f["val_size"]


def test_custom_placeholder_estimator_in_fold_pipeline(db_session, pipeline_regression_setup):
    """
    Test providing a custom placeholder estimator (e.g. DummyRegressor) to run_experiment_fold_pipelines.
    """
    project = pipeline_regression_setup["project"]
    service = ExperimentService(db_session)

    exp = service.exp_repo.create_experiment(
        project_id=project.id,
        task_type="REGRESSION",
        status=ExperimentState.CREATED.value,
    )
    service.freeze_experiment_config(exp.id, config_override={"folds": 3, "seed": 42})

    dummy = DummyRegressor(strategy="mean")
    results = service.run_experiment_fold_pipelines(exp.id, estimator=dummy)

    for f in results["fold_results"]:
        assert isinstance(f["pipeline"].named_steps["estimator"], DummyRegressor)
        assert len(f["y_val_pred"]) == f["val_size"]
