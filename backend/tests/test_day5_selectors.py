"""
Day 5 — Comprehensive Unit & Integration Tests:
Evidence-Strength Bands (STRONG/MODERATE/LIMITED/INSUFFICIENT_EVIDENCE),
Forced 1-of-4-applied abort test confirming no subset returned,
and feature_selection_fold_results + feature_selection_snapshots persistence (SRS §2.7, §2.17).
"""

import io
import uuid
from unittest.mock import patch
import numpy as np
import pandas as pd
import pytest

from app.config.contract import EvidenceStrength, FeatureSelectionMethod, TechniqueStatus
from app.models.dataset import Dataset
from app.models.dataset_split import DatasetSplit
from app.models.experiment import Experiment
from app.models.feature_selection_fold_result import FeatureSelectionFoldResult
from app.models.feature_selection_snapshot import FeatureSelectionSnapshot
from app.models.project import Project
from app.models.user import User
from app.models.role import Role
from app.services.dataset_service import DatasetService
from app.services.dataset_split_service import DatasetSplitService
from app.services.feature_selection_service import FeatureSelectionService
from app.services.selectors import (
    compute_evidence_strength,
    apply_top_k_percent_selection,
    CORRELATION_SELECTOR,
    LASSO_SELECTOR,
    RANDOM_FOREST_IMPORTANCE_SELECTOR,
    PERMUTATION_IMPORTANCE_SELECTOR,
)


# =============================================================================
# 1. Evidence Strength Classification Tests (§2.7, §8)
# =============================================================================

def test_evidence_strength_bands():
    """
    SRS §2.7:
    - 4 applied -> STRONG
    - 3 applied -> MODERATE
    - 2 applied -> LIMITED (meets min_applied_methods=2)
    - 1 applied -> INSUFFICIENT_EVIDENCE (aborts selection)
    - 0 applied -> INSUFFICIENT_EVIDENCE
    """
    assert compute_evidence_strength(4, total_count=4, min_required=2) == EvidenceStrength.STRONG
    assert compute_evidence_strength(3, total_count=4, min_required=2) == EvidenceStrength.MODERATE
    assert compute_evidence_strength(2, total_count=4, min_required=2) == EvidenceStrength.LIMITED
    assert compute_evidence_strength(1, total_count=4, min_required=2) == EvidenceStrength.INSUFFICIENT_EVIDENCE
    assert compute_evidence_strength(0, total_count=4, min_required=2) == EvidenceStrength.INSUFFICIENT_EVIDENCE


# =============================================================================
# 2. Forced 1-of-4-Applied Test (No Subset Returned)
# =============================================================================

def test_forced_one_of_four_applied_insufficient_evidence():
    """
    Forced 1-of-4-applied condition:
    When only 1 technique is APPLIED (and 3 are SKIPPED/FAILED),
    evidence strength MUST be INSUFFICIENT_EVIDENCE and NO feature subset is returned.
    """
    feature_names = ["feat_a", "feat_b", "feat_c", "feat_d"]
    scores = {"feat_a": 0.9, "feat_b": 0.7, "feat_c": 0.4, "feat_d": 0.1}

    # Pass applied_count = 1 (< min_applied_methods = 2)
    res = apply_top_k_percent_selection(
        feature_names=feature_names,
        scores=scores,
        alpha=0.5,
        k_min=2,
        k_max=10,
        applied_count=1,
        min_applied_methods=2,
        total_methods=4,
    )

    assert res["evidence_strength"] == EvidenceStrength.INSUFFICIENT_EVIDENCE.value
    # Crucial Invariant: Strictly empty list returned!
    assert res["selected_features"] == []
    assert res["k_selected"] == 0
    assert all(val is False for val in res["is_selected_map"].values())


# =============================================================================
# 3. Fold Results & Snapshot Persistence Integration Tests (SRS §2.7, §2.17)
# =============================================================================

def test_fold_results_and_snapshot_persistence_end_to_end(db_session):
    """
    Verifies that running CV feature selection:
    1. Persists records to feature_selection_fold_results with all technique scores and fold indices.
    2. Persists record to feature_selection_snapshots on experiment completion and links it to Experiment.
    """
    role = db_session.query(Role).filter(Role.role_name == "ML_ENGINEER").first()
    user = User(
        id=uuid.uuid4(),
        full_name="Fold Tester",
        email="fold_tester@test.com",
        password_hash="fake",
        role_id=role.id,
    )
    db_session.add(user)

    project = Project(
        id=uuid.uuid4(),
        owner_id=user.id,
        project_name="Fold & Snapshot Test",
        task_type="REGRESSION",
        target_column="target",
        pipeline_stage="TRANSFORMED",
    )
    db_session.add(project)
    db_session.commit()

    # Create synthetic dataset
    np.random.seed(42)
    n = 100
    df = pd.DataFrame({
        "feat_signal1": np.random.normal(0, 1, n),
        "feat_signal2": np.random.normal(0, 1, n),
        "feat_noise": np.random.normal(0, 1, n),
        "target": np.random.normal(0, 1, n),
    })
    buf = io.BytesIO()
    df.to_csv(buf, index=False)
    buf.seek(0)

    ds_service = DatasetService(db_session)
    dataset = ds_service.upload(project.id, "data.csv", buf.getvalue(), uploaded_by_id=user.id)
    ds_service.detect_structural_schema(dataset.id)

    split_service = DatasetSplitService(db_session)
    split_service.create_outer_split(dataset.id, locked_test_pct=20, seed=42)

    fs_service = FeatureSelectionService(db_session)
    result = fs_service.run_cv_feature_selection(
        project_id=project.id,
        n_splits=5,
        cv_strategy="KFOLD",
        seed=42,
        threshold=0.2,
    )

    assert result["status"] == "COMPLETED"
    exp_id = result["experiment_id"]

    # 1. Verify feature_selection_fold_results stored
    fold_results = (
        db_session.query(FeatureSelectionFoldResult)
        .filter(FeatureSelectionFoldResult.experiment_id == exp_id)
        .order_by(FeatureSelectionFoldResult.fold_index.asc())
        .all()
    )
    assert len(fold_results) == 5
    for idx, f_res in enumerate(fold_results):
        assert f_res.fold_index == idx
        assert isinstance(f_res.selected_features, list)
        assert len(f_res.selected_features) > 0
        assert "Correlation" in f_res.technique_scores
        assert "Lasso" in f_res.technique_scores
        assert "Random Forest" in f_res.technique_scores
        assert "Permutation" in f_res.technique_scores

    # 2. Verify feature_selection_snapshots stored
    exp = db_session.query(Experiment).filter(Experiment.id == exp_id).first()
    assert exp.feature_selection_snapshot_id is not None

    snapshot = (
        db_session.query(FeatureSelectionSnapshot)
        .filter(FeatureSelectionSnapshot.id == exp.feature_selection_snapshot_id)
        .first()
    )
    assert snapshot is not None
    assert snapshot.experiment_id == exp.id
    assert snapshot.final_selection_method == "rank_aggregation_ensemble"
    assert isinstance(snapshot.final_selected_features, list)
    assert len(snapshot.final_selected_features) > 0


def test_cv_feature_selection_forced_one_applied_fold_aborts_selection(db_session):
    """
    Simulates a CV run where 3 selectors fail in a fold, leaving only 1 applied selector.
    Verifies that the fold record has selected_features == [].
    """
    role = db_session.query(Role).filter(Role.role_name == "ML_ENGINEER").first()
    user = User(
        id=uuid.uuid4(),
        full_name="Aborted Fold Dev",
        email="abort_fold@test.com",
        password_hash="fake",
        role_id=role.id,
    )
    db_session.add(user)

    project = Project(
        id=uuid.uuid4(),
        owner_id=user.id,
        project_name="Abort Fold Test",
        task_type="REGRESSION",
        target_column="target",
        pipeline_stage="TRANSFORMED",
    )
    db_session.add(project)
    db_session.commit()

    np.random.seed(42)
    n = 60
    df = pd.DataFrame({
        "f1": np.random.normal(0, 1, n),
        "f2": np.random.normal(0, 1, n),
        "target": np.random.normal(0, 1, n),
    })
    buf = io.BytesIO()
    df.to_csv(buf, index=False)
    buf.seek(0)

    ds_service = DatasetService(db_session)
    dataset = ds_service.upload(project.id, "abort.csv", buf.getvalue(), uploaded_by_id=user.id)
    ds_service.detect_structural_schema(dataset.id)

    split_service = DatasetSplitService(db_session)
    split_service.create_outer_split(dataset.id, locked_test_pct=20, seed=42)

    fs_service = FeatureSelectionService(db_session)

    # Patch Lasso, RF, and Permutation to raise exceptions, leaving only Correlation APPLIED
    with patch.object(FeatureSelectionService, "compute_lasso_scores", side_effect=RuntimeError("Lasso solver error")), \
         patch.object(FeatureSelectionService, "compute_random_forest_scores", side_effect=RuntimeError("RF tree error")), \
         patch.object(FeatureSelectionService, "compute_permutation_scores", side_effect=RuntimeError("Permutation error")):
        
        result = fs_service.run_cv_feature_selection(
            project_id=project.id,
            n_splits=3,
            cv_strategy="KFOLD",
            seed=42,
        )

    assert result["status"] == "COMPLETED"
    exp_id = result["experiment_id"]

    # In every fold, only 1 selector (Correlation) succeeded -> fold_selected must be []
    folds = (
        db_session.query(FeatureSelectionFoldResult)
        .filter(FeatureSelectionFoldResult.experiment_id == exp_id)
        .all()
    )
    assert len(folds) == 3
    for fold in folds:
        assert fold.selected_features == [], "Fold with only 1 applied selector must abort with []"
        assert fold.technique_scores["Correlation"]["f1"]["status"] == "APPLIED"
        assert fold.technique_scores["Lasso"]["f1"]["status"] == "FAILED"
        assert fold.technique_scores["Random Forest"]["f1"]["status"] == "FAILED"
        assert fold.technique_scores["Permutation"]["f1"]["status"] == "FAILED"
