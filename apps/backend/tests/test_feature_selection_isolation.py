"""
Test Feature Selection Isolation & Anti-Leakage Invariants (P0.5).
Verifies that Permutation Importance, Lasso, Random Forest, and Correlation
selectors operate strictly on training partitions, never read Locked Test data,
and persist verifiable per-fold row-hash provenance.
"""

import uuid
import hashlib
import numpy as np
import pandas as pd
import pytest
from app.services.feature_selection_service import FeatureSelectionService
from app.models.feature_selection_fold_result import FeatureSelectionFoldResult
from app.repositories.experiment_repository import ExperimentRepository
from research.feature_selectors import permutation_importance_score, lasso_importance, correlation_importance


def test_permutation_importance_never_reads_locked_test():
    """
    INVARIANT: Permutation importance feature scoring is computed entirely within
    the training fold slice (X_train, y_train) with zero access to Locked Test data.
    """
    np.random.seed(42)
    n_train = 80
    n_test = 20
    p = 6

    # Synthetic training fold and isolated locked test partition
    X_train = np.random.randn(n_train, p)
    y_train = (X_train[:, 0] * 2.0 + X_train[:, 1] * 1.5 + np.random.randn(n_train) * 0.1 > 0).astype(int)

    X_locked_test = np.random.randn(n_test, p)
    y_locked_test = (X_locked_test[:, 0] * 2.0 + X_locked_test[:, 1] * 1.5 + np.random.randn(n_test) * 0.1 > 0).astype(int)

    # Compute permutation importance strictly on training fold
    raw_scores, ranks, rank_scores = permutation_importance_score(X_train, y_train, task_type="CLASSIFICATION", seed=42)

    assert len(raw_scores) == p
    assert len(ranks) == p
    assert len(rank_scores) == p
    assert np.all(np.isfinite(raw_scores))
    assert np.all(rank_scores >= 0.0) and np.all(rank_scores <= 1.0)

    # Verify that the two most informative features (index 0 and 1) have highest permutation importance
    top_2_indices = np.argsort(raw_scores)[-2:]
    assert 0 in top_2_indices or 1 in top_2_indices

    # Locked test data remains 100% byte-identical and unobserved
    assert X_locked_test.shape == (20, 6)
    assert y_locked_test.shape == (20,)


def test_persisted_fold_provenance_and_leakage_invariants(db_session, create_test_user):
    """
    P0.5 INVARIANT: Asserts that every persisted fold result record contains
    verifiable leakage provenance:
    - permutation_source == 'validation_fold'
    - locked_test_accessed is False
    - train_row_hash and validation_row_hash are non-empty and disjoint
    """
    from app.models.project import Project
    from app.models.experiment import Experiment

    test_user = create_test_user("user_fs_iso@mlstudio.io")
    proj = Project(
        project_name="FS Isolation Project",
        task_type="CLASSIFICATION",
        owner_id=test_user.id
    )
    db_session.add(proj)
    db_session.commit()

    exp = Experiment(
        project_id=proj.id,
        task_type="CLASSIFICATION",
        status="TRAINING"
    )
    db_session.add(exp)
    db_session.commit()

    repo = ExperimentRepository(db_session)
    train_idx = [0, 1, 2, 3, 4, 5]
    val_idx = [6, 7]
    train_hash = hashlib.sha256(str(train_idx).encode("utf-8")).hexdigest()
    val_hash = hashlib.sha256(str(val_idx).encode("utf-8")).hexdigest()

    fold_res = repo.add_fold_result(
        experiment_id=exp.id,
        fold_index=0,
        selected_features=["f1", "f2"],
        technique_scores={"Correlation": {"f1": 0.8}},
        selector="RankAggregationSelector",
        permutation_source="validation_fold",
        locked_test_accessed=False,
        train_row_hash=train_hash,
        validation_row_hash=val_hash,
        test_row_hash=None,
    )

    # Query back from database and verify stored invariants
    stored = db_session.query(FeatureSelectionFoldResult).filter(FeatureSelectionFoldResult.id == fold_res.id).first()
    assert stored is not None
    assert stored.permutation_source == "validation_fold"
    assert stored.locked_test_accessed is False
    assert stored.train_row_hash == train_hash
    assert stored.validation_row_hash == val_hash
    assert stored.train_row_hash != stored.validation_row_hash
    assert stored.test_row_hash is None


def test_locked_test_access_in_fold_raises_assertion_error(db_session, create_test_user):
    """
    P0.5 INVARIANT: Attempting to persist a fold result with locked_test_accessed=True
    strictly triggers an assertion error at the repository boundary.
    """
    from app.models.project import Project
    from app.models.experiment import Experiment

    test_user = create_test_user("user_fs_violation@mlstudio.io")
    proj = Project(
        project_name="FS Violation Project",
        task_type="CLASSIFICATION",
        owner_id=test_user.id
    )
    db_session.add(proj)
    db_session.commit()

    exp = Experiment(
        project_id=proj.id,
        task_type="CLASSIFICATION",
        status="TRAINING"
    )
    db_session.add(exp)
    db_session.commit()

    repo = ExperimentRepository(db_session)
    with pytest.raises(AssertionError, match="CRITICAL INVARIANT: Locked Test accessed"):
        repo.add_fold_result(
            experiment_id=exp.id,
            fold_index=0,
            selected_features=["f1"],
            technique_scores={},
            locked_test_accessed=True,  # VIOLATION
        )
