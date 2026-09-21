"""
Day 2 — Comprehensive Unit & Integration Tests:
RANDOM_FOREST_IMPORTANCE_SELECTOR + PERMUTATION_IMPORTANCE_SELECTOR (SRS §2.7).
Tests APPLIED / SKIPPED / FAILED status tracking and forced FAILED cases.
"""

from unittest.mock import patch
import numpy as np
import pandas as pd
import pytest

from app.config.contract import FeatureSelectionMethod, TechniqueStatus
from app.services.selectors import (
    calculate_srs_rank_scores,
    CORRELATION_SELECTOR,
    LASSO_SELECTOR,
    RANDOM_FOREST_IMPORTANCE_SELECTOR,
    PERMUTATION_IMPORTANCE_SELECTOR,
    RandomForestImportanceSelector,
    PermutationImportanceSelector,
    SelectorOutput,
)
from app.services.feature_selection_service import FeatureSelectionService


# =============================================================================
# 1. Exact Naming Invariant Tests (Never bare 'RF selector')
# =============================================================================

def test_exact_selector_naming():
    """
    SRS & Architecture Invariant:
    Must use exact canonical names RANDOM_FOREST_IMPORTANCE_SELECTOR and
    PERMUTATION_IMPORTANCE_SELECTOR, never bare 'RF selector'.
    """
    assert isinstance(RANDOM_FOREST_IMPORTANCE_SELECTOR, RandomForestImportanceSelector)
    assert isinstance(PERMUTATION_IMPORTANCE_SELECTOR, PermutationImportanceSelector)
    assert RANDOM_FOREST_IMPORTANCE_SELECTOR.name == FeatureSelectionMethod.RANDOM_FOREST.value
    assert PERMUTATION_IMPORTANCE_SELECTOR.name == FeatureSelectionMethod.PERMUTATION.value


# =============================================================================
# 2. RANDOM_FOREST_IMPORTANCE_SELECTOR Tests
# =============================================================================

def test_random_forest_importance_selector_regression():
    """
    Tests Random Forest MDI importance on continuous regression dataset.
    """
    np.random.seed(42)
    n = 120
    x1 = np.random.normal(0, 1, n)
    x2 = np.random.normal(0, 1, n)
    x3 = np.random.normal(0, 1, n)
    y = 5.0 * x1 + 2.5 * x2 + np.random.normal(0, 0.2, n)

    X = np.column_stack([x1, x2, x3])
    feature_names = ["feat_primary", "feat_secondary", "feat_noise"]

    output = RANDOM_FOREST_IMPORTANCE_SELECTOR.select(
        X=X,
        y=y,
        task_type="REGRESSION",
        feature_names=feature_names,
        seed=42,
    )

    assert isinstance(output, SelectorOutput)
    assert output.status == TechniqueStatus.APPLIED
    assert output.status_reason is None
    assert output.method_name == FeatureSelectionMethod.RANDOM_FOREST.value
    assert len(output.raw_scores) == 3
    # Informative features ranked above noise
    assert output.raw_scores[0] > output.raw_scores[2]
    assert output.ranks[0] == 1.0
    assert output.rank_scores[0] == 1.0

    feat_map = output.to_feature_map()
    assert feat_map["feat_primary"]["status"] == "APPLIED"
    assert feat_map["feat_primary"]["rank"] == 1.0


def test_random_forest_importance_selector_classification():
    """
    Tests Random Forest MDI importance on binary classification dataset.
    """
    np.random.seed(42)
    n = 120
    x_signal = np.random.normal(0, 1, n)
    x_noise = np.random.normal(0, 1, n)
    y = (x_signal * 2.0 + np.random.normal(0, 0.3, n) > 0).astype(int)

    X = np.column_stack([x_signal, x_noise])
    output = RANDOM_FOREST_IMPORTANCE_SELECTOR.select(
        X=X,
        y=y,
        task_type="CLASSIFICATION",
        feature_names=["signal_feat", "noise_feat"],
        seed=42,
    )

    assert output.status == TechniqueStatus.APPLIED
    assert output.raw_scores[0] > output.raw_scores[1]
    assert output.ranks[0] == 1.0
    assert output.ranks[1] == 2.0
    assert output.rank_scores[0] == 1.0
    assert output.rank_scores[1] == 0.0


def test_random_forest_importance_selector_multiclass():
    """
    Tests Random Forest MDI importance on multiclass dataset.
    """
    np.random.seed(42)
    n = 100
    x1 = np.random.normal(0, 1, n)
    x2 = np.random.normal(0, 1, n)
    y = np.random.choice(["catA", "catB", "catC"], size=n)

    X = np.column_stack([x1, x2])
    output = RANDOM_FOREST_IMPORTANCE_SELECTOR.select(
        X=X,
        y=y,
        task_type="CLASSIFICATION",
        feature_names=["f1", "f2"],
        seed=42,
    )

    assert output.status == TechniqueStatus.APPLIED
    assert len(output.raw_scores) == 2
    assert len(output.ranks) == 2


def test_random_forest_importance_selector_single_feature_p1():
    """
    p = 1 single feature SRS §2.7 edge case.
    """
    np.random.seed(42)
    n = 50
    X = np.random.normal(0, 1, (n, 1))
    y = X[:, 0] * 3.0 + np.random.normal(0, 0.1, n)

    output = RANDOM_FOREST_IMPORTANCE_SELECTOR.select(
        X=X,
        y=y,
        task_type="REGRESSION",
        feature_names=["sole_feat"],
    )

    assert output.status == TechniqueStatus.APPLIED
    assert output.ranks[0] == 1.0
    assert output.rank_scores[0] == 1.0


def test_random_forest_importance_selector_skipped_cases():
    """
    Tests SKIPPED status when input data is empty or has fewer than 2 samples.
    """
    # Empty data (p = 0)
    out_empty = RANDOM_FOREST_IMPORTANCE_SELECTOR.select(
        X=np.empty((10, 0)),
        y=np.ones(10),
        task_type="REGRESSION",
    )
    assert out_empty.status == TechniqueStatus.SKIPPED
    assert "Empty" in (out_empty.status_reason or "")

    # Insufficient samples (n = 1)
    out_single_row = RANDOM_FOREST_IMPORTANCE_SELECTOR.select(
        X=np.array([[1.0, 2.0]]),
        y=np.array([42.0]),
        task_type="REGRESSION",
        feature_names=["col1", "col2"],
    )
    assert out_single_row.status == TechniqueStatus.SKIPPED
    assert "insufficient sample count" in (out_single_row.status_reason or "")
    feat_map = out_single_row.to_feature_map()
    assert feat_map["col1"]["status"] == "SKIPPED"
    assert feat_map["col1"]["raw_score"] is None


def test_random_forest_importance_selector_forced_failed_case():
    """
    Forced FAILED case: Simulates an unrecoverable exception during fitting.
    Verifies that status becomes FAILED and status_reason captures the exception.
    """
    n, p = 50, 3
    X = np.random.normal(0, 1, (n, p))
    y = np.random.normal(0, 1, n)

    # Force failure by patching compute_raw_scores to raise a simulated error
    with patch.object(
        RANDOM_FOREST_IMPORTANCE_SELECTOR,
        "compute_raw_scores",
        side_effect=RuntimeError("Forced Random Forest Convergence Failure for Testing"),
    ):
        output = RANDOM_FOREST_IMPORTANCE_SELECTOR.select(
            X=X,
            y=y,
            task_type="REGRESSION",
            feature_names=["f1", "f2", "f3"],
        )

    assert output.status == TechniqueStatus.FAILED
    assert "Forced Random Forest Convergence Failure for Testing" in output.status_reason
    assert np.all(output.raw_scores == 0.0)
    assert np.all(output.ranks == 0.0)

    feat_map = output.to_feature_map()
    assert feat_map["f1"]["status"] == "FAILED"
    assert feat_map["f1"]["status_reason"] == "Forced Random Forest Convergence Failure for Testing"
    assert feat_map["f1"]["raw_score"] is None


# =============================================================================
# 3. PERMUTATION_IMPORTANCE_SELECTOR Tests
# =============================================================================

def test_permutation_importance_selector_regression():
    """
    Tests Permutation Importance on continuous regression dataset.
    """
    np.random.seed(42)
    n = 120
    x1 = np.random.normal(0, 1, n)
    x2 = np.random.normal(0, 1, n)
    x3 = np.random.normal(0, 1, n)
    y = 4.0 * x1 + 2.0 * x2 + np.random.normal(0, 0.2, n)

    X = np.column_stack([x1, x2, x3])
    feature_names = ["feat1", "feat2", "noise"]

    output = PERMUTATION_IMPORTANCE_SELECTOR.select(
        X=X,
        y=y,
        task_type="REGRESSION",
        feature_names=feature_names,
        seed=42,
    )

    assert isinstance(output, SelectorOutput)
    assert output.status == TechniqueStatus.APPLIED
    assert output.method_name == FeatureSelectionMethod.PERMUTATION.value
    assert output.raw_scores[0] > output.raw_scores[2]
    assert output.ranks[0] == 1.0
    assert output.rank_scores[0] == 1.0


def test_permutation_importance_selector_classification():
    """
    Tests Permutation Importance on binary classification dataset.
    """
    np.random.seed(42)
    n = 120
    x1 = np.random.normal(0, 1, n)
    x2 = np.random.normal(0, 1, n)
    y = (x1 * 3.0 + np.random.normal(0, 0.3, n) > 0).astype(int)

    X = np.column_stack([x1, x2])
    output = PERMUTATION_IMPORTANCE_SELECTOR.select(
        X=X,
        y=y,
        task_type="CLASSIFICATION",
        feature_names=["informative", "noise"],
        seed=42,
    )

    assert output.status == TechniqueStatus.APPLIED
    assert output.raw_scores[0] > output.raw_scores[1]
    assert output.ranks[0] == 1.0
    assert output.ranks[1] == 2.0


def test_permutation_importance_selector_single_feature_p1():
    """
    p = 1 single feature SRS §2.7 edge case.
    """
    np.random.seed(42)
    n = 50
    X = np.random.normal(0, 1, (n, 1))
    y = X[:, 0] * 2.0 + np.random.normal(0, 0.1, n)

    output = PERMUTATION_IMPORTANCE_SELECTOR.select(
        X=X,
        y=y,
        task_type="REGRESSION",
        feature_names=["solo_feature"],
    )

    assert output.status == TechniqueStatus.APPLIED
    assert output.ranks[0] == 1.0
    assert output.rank_scores[0] == 1.0


def test_permutation_importance_selector_skipped_cases():
    """
    Tests SKIPPED status when input data is empty or has fewer than 2 samples.
    """
    # Empty data
    out_empty = PERMUTATION_IMPORTANCE_SELECTOR.select(
        X=np.empty((5, 0)),
        y=np.ones(5),
        task_type="REGRESSION",
    )
    assert out_empty.status == TechniqueStatus.SKIPPED
    assert "Empty" in (out_empty.status_reason or "")

    # Single sample
    out_single_row = PERMUTATION_IMPORTANCE_SELECTOR.select(
        X=np.array([[1.0, 2.0, 3.0]]),
        y=np.array([10.0]),
        task_type="REGRESSION",
        feature_names=["a", "b", "c"],
    )
    assert out_single_row.status == TechniqueStatus.SKIPPED
    assert "insufficient sample count" in (out_single_row.status_reason or "")


def test_permutation_importance_selector_forced_failed_case():
    """
    Forced FAILED case: Simulates an unrecoverable exception in permutation computation.
    Verifies that status becomes FAILED and status_reason captures the exception.
    """
    n, p = 50, 3
    X = np.random.normal(0, 1, (n, p))
    y = np.random.normal(0, 1, n)

    with patch.object(
        PERMUTATION_IMPORTANCE_SELECTOR,
        "compute_raw_scores",
        side_effect=ValueError("Forced Permutation Scoring Failure for Testing"),
    ):
        output = PERMUTATION_IMPORTANCE_SELECTOR.select(
            X=X,
            y=y,
            task_type="REGRESSION",
            feature_names=["f1", "f2", "f3"],
        )

    assert output.status == TechniqueStatus.FAILED
    assert "Forced Permutation Scoring Failure for Testing" in output.status_reason
    assert np.all(output.raw_scores == 0.0)

    feat_map = output.to_feature_map()
    assert feat_map["f1"]["status"] == "FAILED"
    assert feat_map["f1"]["status_reason"] == "Forced Permutation Scoring Failure for Testing"
    assert feat_map["f1"]["raw_score"] is None


# =============================================================================
# 4. Fold Aggregation Status Handling Integration Test (SRS §2.7)
# =============================================================================

def test_fold_aggregation_excludes_failed_and_skipped():
    """
    SRS §2.7:
    EnsembleScore_j = (1 / T_applied) * sum_{T in Applied} r_{j,T}
    When a technique is SKIPPED or FAILED, it must NOT dilute T_applied.
    """
    feature_names = ["feat1", "feat2", "feat3"]
    technique_results = {
        "Correlation": {
            "status": "APPLIED",
            "raw_scores": np.array([0.9, 0.5, 0.1]),
            "status_reason": None,
        },
        "Lasso": {
            "status": "SKIPPED",
            "raw_scores": None,
            "status_reason": "Skipped due to single sample",
        },
        "Random Forest": {
            "status": "FAILED",
            "raw_scores": None,
            "status_reason": "Tree build memory exception",
        },
        "Permutation": {
            "status": "APPLIED",
            "raw_scores": np.array([0.8, 0.4, 0.2]),
            "status_reason": None,
        },
    }

    payload, ensemble = FeatureSelectionService.aggregate_technique_scores_for_fold(
        feature_names, technique_results
    )

    # T_applied = 2 (Correlation + Permutation)
    # Correlation normalized scores: feat1=1.0, feat2=0.5, feat3=0.0
    # Permutation normalized scores: feat1=1.0, feat2=0.5, feat3=0.0
    # Ensemble: feat1=(1.0+1.0)/2 = 1.0, feat2=(0.5+0.5)/2 = 0.5, feat3=(0.0+0.0)/2 = 0.0
    assert ensemble["feat1"] == 1.0
    assert ensemble["feat2"] == 0.5
    assert ensemble["feat3"] == 0.0

    # Verify statuses in payload
    assert payload["Correlation"]["feat1"]["status"] == "APPLIED"
    assert payload["Lasso"]["feat1"]["status"] == "SKIPPED"
    assert payload["Lasso"]["feat1"]["status_reason"] == "Skipped due to single sample"
    assert payload["Random Forest"]["feat1"]["status"] == "FAILED"
    assert payload["Random Forest"]["feat1"]["status_reason"] == "Tree build memory exception"
    assert payload["Permutation"]["feat1"]["status"] == "APPLIED"
