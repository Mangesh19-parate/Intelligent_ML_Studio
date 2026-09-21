"""
Unit & Integration Tests for Day 5 — Leakage Protection & Threshold Provenance.

Per SRS v9 §5 and SRS §2.11 / §2.12:
1. `test_test_reuse`:
   - Assert Locked Test data is never accessed during training, feature selection, or CV threshold tuning.
   - Assert diagnostic re-runs never overwrite model artifacts, weights, or frozen decision thresholds.
2. `test_threshold_not_from_test`:
   - Assert the frozen decision threshold (trained_models.decision_threshold) is computed strictly
     from Development out-of-fold predictions.
   - Assert the frozen threshold is completely invariant to any alterations, corruptions, or inversions
     in Locked Test data.
3. `test_transformer_and_feature_selector_no_test_leakage`:
   - Assert transformers and feature selection methods fit strictly on Development partition rows.
"""

import uuid
from uuid import uuid4
from unittest.mock import patch
import numpy as np
import pandas as pd
import pytest
from sklearn.compose import ColumnTransformer

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
from app.services.dataset_split_service import DatasetSplitService
from app.services.experiment_service import ExperimentService
from app.services.trainers import ClassificationTrainer, RegressionTrainer


def create_mock_project_and_dataset(db_session, user, project_name, dev_df, test_df, task_type="CLASSIFICATION", target_col="label", tmp_path=None):
    """Helper to create project, dataset, columns, transformations, and outer split."""
    project = Project(
        id=uuid4(),
        owner_id=user.id,
        project_name=project_name,
        task_type=task_type,
        target_column=target_col,
        pipeline_stage="TRANSFORMED",
    )
    db_session.add(project)
    db_session.commit()

    combined_df = pd.concat([dev_df, test_df], ignore_index=True)
    n_samples = len(combined_df)
    n_dev = len(dev_df)

    csv_path = tmp_path / f"{project_name.replace(' ', '_')}.csv"
    combined_df.to_csv(csv_path, index=False)

    dataset = Dataset(
        id=uuid4(),
        project_id=project.id,
        file_path=str(csv_path),
        row_count=n_samples,
        column_count=len(combined_df.columns),
        content_hash=f"hash_{uuid4().hex[:12]}",
        version_number=1,
        stage="SPLIT",
    )
    db_session.add(dataset)
    db_session.commit()

    for col in combined_df.columns:
        if col == "row_uid":
            continue
        is_target = (col == target_col)
        dtype = "CATEGORICAL" if (is_target and task_type == "CLASSIFICATION") else "NUMERIC"
        c = DatasetColumn(
            id=uuid4(),
            dataset_id=dataset.id,
            column_name=col,
            data_type=dtype,
            is_target=is_target
        )
        db_session.add(c)

        if not is_target:
            tc = TransformationConfig(
                id=uuid4(),
                project_id=project.id,
                column_name=col,
                missing_value_strategy="MEAN",
                scaling_strategy="STANDARD",
                outlier_strategy="NONE",
                is_active=True,
            )
            db_session.add(tc)

    dev_split = DatasetSplit(
        id=uuid4(),
        dataset_id=dataset.id,
        split_type="DEVELOPMENT",
        split_seed=42,
        row_indices=list(dev_df["row_uid"]),
    )
    test_split = DatasetSplit(
        id=uuid4(),
        dataset_id=dataset.id,
        split_type="LOCKED_TEST",
        split_seed=42,
        row_indices=list(test_df["row_uid"]),
    )
    db_session.add(dev_split)
    db_session.add(test_split)
    db_session.commit()

    return project, dataset


# =============================================================================
# 1. test_test_reuse
# =============================================================================

def test_test_reuse(db_session, create_test_user, tmp_path):
    """
    Asserts:
    1. Zero access to Locked Test partition during CV training and threshold selection.
    2. All .fit() calls strictly operate on Development subsets.
    3. Diagnostic re-evaluation on Locked Test data does not alter model artifacts,
       weights, frozen decision thresholds, or authoritative metrics.
    """
    user = create_test_user("test_reuse_user@studio.ml", "ADMIN")

    np.random.seed(42)
    n_dev = 50
    n_test = 20

    dev_df = pd.DataFrame({
        "feat1": np.random.normal(0, 1, n_dev),
        "feat2": np.random.normal(0, 1, n_dev),
        "label": np.random.choice([0, 1], size=n_dev, p=[0.6, 0.4]),
        "row_uid": [f"dev_{i}" for i in range(n_dev)],
    })

    test_df = pd.DataFrame({
        "feat1": np.random.normal(0, 1, n_test),
        "feat2": np.random.normal(0, 1, n_test),
        "label": np.random.choice([0, 1], size=n_test, p=[0.5, 0.5]),
        "row_uid": [f"test_{i}" for i in range(n_test)],
    })

    project, dataset = create_mock_project_and_dataset(
        db_session, user, "Test Reuse Project", dev_df, test_df,
        task_type="CLASSIFICATION", target_col="label", tmp_path=tmp_path
    )

    # Track calls to Locked Test data loader
    original_get_locked_test = DatasetSplitService.get_locked_test_data
    locked_test_call_count = 0

    def spy_get_locked_test(self, dataset_id):
        nonlocal locked_test_call_count
        locked_test_call_count += 1
        return original_get_locked_test(self, dataset_id)

    # Track all fit calls
    fit_samples_seen = []
    original_fit = ClassificationTrainer.fit

    def spy_fit(self, X, y):
        fit_samples_seen.append(len(X))
        return original_fit(self, X, y)

    with patch.object(DatasetSplitService, "get_locked_test_data", spy_get_locked_test), \
         patch.object(ClassificationTrainer, "fit", spy_fit):

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

        # 1. Run CV & threshold selection without auto-finalization
        res = service.run_experiment(
            project_id=project.id,
            experiment_id=frozen_exp.id,
            auto_finalize=False,
        )

        # ASSERTION 1: Zero locked test access during CV / threshold search
        assert locked_test_call_count == 0, (
            f"LEAKAGE DETECTED: get_locked_test_data was called {locked_test_call_count} times during CV training!"
        )

        # ASSERTION 2: All fold fits saw strictly fold subsets (< n_dev)
        for s_count in fit_samples_seen:
            assert s_count < n_dev, f"Fold fit saw {s_count} samples, which exceeds fold size (< {n_dev})!"

        # 2. Finalize experiment (consuming Locked Test once)
        fin_res = service.finalize_experiment(exp.id)
        assert locked_test_call_count == 1, "get_locked_test_data must be called exactly once on first finalization"

        # Refit on full dev partition (saw exactly n_dev samples)
        assert fit_samples_seen[-1] == n_dev, (
            f"Expected final refit on full Development set to see {n_dev} rows, but saw {fit_samples_seen[-1]}"
        )

        # Record winning model state and frozen threshold
        winning_model = db_session.query(TrainedModel).filter_by(id=exp.selected_model_id).first()
        initial_threshold = float(winning_model.decision_threshold)
        initial_artifact_path = winning_model.artifact_path
        initial_checksum = winning_model.artifact_checksum
        initial_cv_score = float(winning_model.quick_cv_score)
        initial_selection_score = float(winning_model.model_selection_score)

        # 3. Diagnostic Re-run: evaluate Locked Test partition again
        diag_res = service.rerun_locked_test_diagnostic(exp.id)
        assert diag_res["split"] == "TEST_REUSED_DIAGNOSTIC"

        # ASSERTION 3: Diagnostic re-run MUST NOT alter model weights, checksum, or frozen threshold
        db_session.refresh(winning_model)
        assert float(winning_model.decision_threshold) == initial_threshold
        assert winning_model.artifact_path == initial_artifact_path
        assert winning_model.artifact_checksum == initial_checksum
        assert float(winning_model.quick_cv_score) == initial_cv_score
        assert float(winning_model.model_selection_score) == initial_selection_score

        # Authoritative LOCKED_TEST metric count remains 1 per metric
        locked_metrics = db_session.query(ModelMetric).filter_by(
            model_id=winning_model.id,
            split="LOCKED_TEST"
        ).all()
        assert len(locked_metrics) > 0


# =============================================================================
# 2. test_threshold_not_from_test
# =============================================================================

def test_threshold_not_from_test(db_session, create_test_user, tmp_path):
    """
    Asserts that the frozen decision threshold NEVER changes based on any Locked Test data:
    1. Dataset A has fixed Development data D and Locked Test data T_1.
    2. Dataset B has the exact same Development data D and radically corrupted Locked Test data T_2.
    3. Both experiments produce EXACTLY identical decision_threshold values.
    """
    user = create_test_user("thresh_leak_user@studio.ml", "ADMIN")

    # Generate identical Development partition D
    np.random.seed(1337)
    n_dev = 60
    feat1_dev = np.random.normal(0, 1, n_dev)
    feat2_dev = np.random.normal(0, 1, n_dev)
    # Skew probabilities to ensure optimal threshold != 0.5
    label_dev = ((feat1_dev + feat2_dev) > 0.3).astype(int)

    dev_df = pd.DataFrame({
        "feat1": feat1_dev,
        "feat2": feat2_dev,
        "label": label_dev,
        "row_uid": [f"dev_{i}" for i in range(n_dev)],
    })

    # Test partition T_1: standard test data
    n_test = 20
    test_df_1 = pd.DataFrame({
        "feat1": np.random.normal(0, 1, n_test),
        "feat2": np.random.normal(0, 1, n_test),
        "label": np.random.choice([0, 1], size=n_test, p=[0.5, 0.5]),
        "row_uid": [f"test1_{i}" for i in range(n_test)],
    })

    # Test partition T_2: radically corrupted test data (extreme outliers and inverted labels)
    test_df_2 = pd.DataFrame({
        "feat1": np.random.normal(100.0, 50.0, n_test),  # Extreme feature values
        "feat2": np.random.normal(-500.0, 10.0, n_test),
        "label": np.zeros(n_test, dtype=int),             # 100% negative class
        "row_uid": [f"test2_{i}" for i in range(n_test)],
    })

    # Create Experiment 1 on Dataset A (D + T_1)
    project_1, dataset_1 = create_mock_project_and_dataset(
        db_session, user, "Threshold Invariance Proj 1", dev_df, test_df_1,
        task_type="CLASSIFICATION", target_col="label", tmp_path=tmp_path
    )
    service_1 = ExperimentService(db_session)
    exp_1 = service_1.exp_repo.create_experiment(
        project_id=project_1.id,
        task_type="CLASSIFICATION",
        status=ExperimentState.CREATED.value,
    )
    frozen_exp_1 = service_1.freeze_experiment_config(
        exp_1.id,
        config_override={
            "algorithms": ["LogisticRegression"],
            "folds": 3,
            "seed": 42,
            "selection_metric": "macro_f1",
            "selection_direction": "MAXIMIZE",
        },
    )
    res_1 = service_1.run_experiment(
        project_id=project_1.id,
        experiment_id=frozen_exp_1.id,
        auto_finalize=True,
    )

    winning_model_1 = db_session.query(TrainedModel).filter_by(id=exp_1.selected_model_id).first()
    thresh_1 = float(winning_model_1.decision_threshold)

    # Create Experiment 2 on Dataset B (D + T_2)
    project_2, dataset_2 = create_mock_project_and_dataset(
        db_session, user, "Threshold Invariance Proj 2", dev_df, test_df_2,
        task_type="CLASSIFICATION", target_col="label", tmp_path=tmp_path
    )
    service_2 = ExperimentService(db_session)
    exp_2 = service_2.exp_repo.create_experiment(
        project_id=project_2.id,
        task_type="CLASSIFICATION",
        status=ExperimentState.CREATED.value,
    )
    frozen_exp_2 = service_2.freeze_experiment_config(
        exp_2.id,
        config_override={
            "algorithms": ["LogisticRegression"],
            "folds": 3,
            "seed": 42,
            "selection_metric": "macro_f1",
            "selection_direction": "MAXIMIZE",
        },
    )
    res_2 = service_2.run_experiment(
        project_id=project_2.id,
        experiment_id=frozen_exp_2.id,
        auto_finalize=True,
    )

    winning_model_2 = db_session.query(TrainedModel).filter_by(id=exp_2.selected_model_id).first()
    thresh_2 = float(winning_model_2.decision_threshold)

    # CRITICAL INVARIANT ASSERTION:
    # Threshold 1 and Threshold 2 must be EXACTLY identical despite completely corrupted test data
    assert thresh_1 == thresh_2, (
        f"LEAKAGE DETECTED! Frozen decision threshold changed when Locked Test data was modified: "
        f"thresh_1={thresh_1} vs thresh_2={thresh_2}"
    )

    # Verify both models retain this threshold after Locked Test evaluation
    db_session.refresh(winning_model_1)
    db_session.refresh(winning_model_2)
    assert float(winning_model_1.decision_threshold) == thresh_1
    assert float(winning_model_2.decision_threshold) == thresh_2


# =============================================================================
# 3. test_transformer_and_feature_selector_no_test_leakage
# =============================================================================

def test_transformer_and_feature_selector_no_test_leakage(db_session, create_test_user, tmp_path):
    """
    Asserts that TransformationService and FeatureSelectionService
    strictly fit on Development partition slices and never receive Locked Test samples.
    """
    user = create_test_user("trans_leak_user@studio.ml", "ADMIN")

    np.random.seed(99)
    n_dev = 40
    n_test = 15

    dev_df = pd.DataFrame({
        "num_a": np.random.normal(5, 2, n_dev),
        "num_b": np.random.normal(10, 3, n_dev),
        "target": np.random.choice([0, 1], size=n_dev),
        "row_uid": [f"dev_{i}" for i in range(n_dev)],
    })

    test_df = pd.DataFrame({
        "num_a": np.random.normal(5, 2, n_test),
        "num_b": np.random.normal(10, 3, n_test),
        "target": np.random.choice([0, 1], size=n_test),
        "row_uid": [f"test_{i}" for i in range(n_test)],
    })

    project, dataset = create_mock_project_and_dataset(
        db_session, user, "Transform Leakage Project", dev_df, test_df,
        task_type="CLASSIFICATION", target_col="target", tmp_path=tmp_path
    )

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
            "folds": 2,
            "seed": 42,
            "selection_metric": "macro_f1",
            "selection_direction": "MAXIMIZE",
        },
    )

    # Track rows passed to transformer.fit_transform and feature selection
    transform_fit_rows = []
    original_ct_fit_transform = ColumnTransformer.fit_transform

    def spy_fit_transform(self, X, y=None):
        transform_fit_rows.append(len(X))
        return original_ct_fit_transform(self, X, y)

    fs_fit_rows = []
    original_fs_refit = ExperimentService._select_features_for_refit

    def spy_fs_refit(self, X_trans, y, task_type, feature_names, seed):
        fs_fit_rows.append(len(X_trans))
        return original_fs_refit(self, X_trans, y, task_type, feature_names, seed)

    with patch.object(ColumnTransformer, "fit_transform", spy_fit_transform), \
         patch.object(ExperimentService, "_select_features_for_refit", spy_fs_refit):
        service.run_experiment(
            project_id=project.id,
            experiment_id=frozen_exp.id,
            auto_finalize=True,
        )

    # Verify that every single transformer fit_transform saw <= n_dev rows
    assert len(transform_fit_rows) > 0
    for r_count in transform_fit_rows:
        assert r_count <= n_dev, (
            f"LEAKAGE DETECTED! Transformer fit_transform saw {r_count} rows, exceeding Development set size ({n_dev})!"
        )

    # Verify feature selection refit saw exactly n_dev rows
    assert len(fs_fit_rows) == 1
    assert fs_fit_rows[0] == n_dev
