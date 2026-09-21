"""
Day 3 — Comprehensive Unit & Integration Tests:
EnsembleScore Aggregation and TOP_K_PERCENT Selection Rule with k_min/k_max Clamps (SRS §2.7, §8).
"""

import numpy as np
import pytest

from app.config.contract import FEATURE_SELECTION_DEFAULTS
from app.services.selectors import (
    aggregate_ensemble_scores,
    resolve_top_k,
    apply_top_k_percent_selection,
    calculate_srs_rank_scores,
)
from app.services.feature_selection_service import FeatureSelectionService


# =============================================================================
# 1. EnsembleScore Aggregation Tests (SRS §2.7)
# =============================================================================

def test_ensemble_score_aggregation_all_applied():
    """
    SRS §2.7:
    EnsembleScore_j = (1 / T_applied) * sum_{T in Applied} r_{j,T}
    When all 4 techniques are applied (T_applied = 4):
    r_1 = [1.0, 0.67, 0.33, 0.0]
    r_2 = [1.0, 0.33, 0.67, 0.0]
    r_3 = [0.67, 1.0, 0.33, 0.0]
    r_4 = [1.0, 1.0, 0.0, 0.0]
    Ensemble:
    feat0: (1.0 + 1.0 + 0.67 + 1.0)/4 = 0.9175
    feat1: (0.67 + 0.33 + 1.0 + 1.0)/4 = 0.75
    feat2: (0.33 + 0.67 + 0.33 + 0.0)/4 = 0.3325
    feat3: (0.0 + 0.0 + 0.0 + 0.0)/4 = 0.0
    """
    p = 4
    r1 = np.array([1.0, 0.67, 0.33, 0.0])
    r2 = np.array([1.0, 0.33, 0.67, 0.0])
    r3 = np.array([0.67, 1.0, 0.33, 0.0])
    r4 = np.array([1.0, 1.0, 0.0, 0.0])

    applied_scores = [r1, r2, r3, r4]
    ens = aggregate_ensemble_scores(applied_scores, p)

    expected = np.array([0.9175, 0.75, 0.3325, 0.0])
    np.testing.assert_array_almost_equal(ens, expected)


def test_ensemble_score_aggregation_non_dilution_on_skipped_failed():
    """
    SRS §2.7:
    Techniques with SKIPPED or FAILED status must NOT dilute T_applied.
    Only applied rank scores are passed into aggregate_ensemble_scores (T_applied = 2).
    """
    p = 3
    r_corr = np.array([1.0, 0.5, 0.0])
    r_rf = np.array([0.8, 0.6, 0.2])

    applied_scores = [r_corr, r_rf]
    ens = aggregate_ensemble_scores(applied_scores, p)

    expected = np.array([0.9, 0.55, 0.1])
    np.testing.assert_array_almost_equal(ens, expected)


def test_ensemble_score_aggregation_zero_applied():
    """
    If all techniques are skipped/failed (T_applied = 0), return zeros without division error.
    """
    p = 5
    ens = aggregate_ensemble_scores([], p)
    assert len(ens) == 5
    assert np.all(ens == 0.0)


def test_ensemble_score_aggregation_empty_p_zero():
    """
    p = 0 returns an empty array.
    """
    ens = aggregate_ensemble_scores([], 0)
    assert len(ens) == 0


# =============================================================================
# 2. TOP_K_PERCENT Clamping Formula Tests (SRS §2.7, §8)
# =============================================================================

def test_resolve_top_k_lower_clamp_boundary():
    """
    Lower clamp boundary test (k_min = 5):
    - p = 20, alpha = 0.10 -> raw k = 20 * 0.10 = 2 (< 5). Clamped up to 5.
    - p = 30, alpha = 0.05 -> raw k = 30 * 0.05 = 1.5 -> 2 (< 5). Clamped up to 5.
    - p = 12, alpha = 0.15 -> raw k = 1.8 -> 2 (< 5). Clamped up to 5.
    """
    assert resolve_top_k(p=20, alpha=0.10, k_min=5, k_max=50) == 5
    assert resolve_top_k(p=30, alpha=0.05, k_min=5, k_max=50) == 5
    assert resolve_top_k(p=12, alpha=0.15, k_min=5, k_max=50) == 5


def test_resolve_top_k_lower_clamp_small_p_bound():
    """
    When total features p is smaller than k_min, cannot select more than p features.
    - p = 3, alpha = 0.25, k_min = 5 -> raw k = 1 -> clamped to min(5, 3) = 3.
    - p = 4, alpha = 0.10, k_min = 5 -> clamped to min(5, 4) = 4.
    """
    assert resolve_top_k(p=3, alpha=0.25, k_min=5, k_max=50) == 3
    assert resolve_top_k(p=4, alpha=0.10, k_min=5, k_max=50) == 4


def test_resolve_top_k_upper_clamp_boundary():
    """
    Upper clamp boundary test (k_max = 50):
    - p = 300, alpha = 0.25 -> raw k = 300 * 0.25 = 75 (> 50). Clamped down to 50.
    - p = 1000, alpha = 0.10 -> raw k = 1000 * 0.10 = 100 (> 50). Clamped down to 50.
    - p = 80, alpha = 0.80 -> raw k = 80 * 0.80 = 64 (> 50). Clamped down to 50.
    """
    assert resolve_top_k(p=300, alpha=0.25, k_min=5, k_max=50) == 50
    assert resolve_top_k(p=1000, alpha=0.10, k_min=5, k_max=50) == 50
    assert resolve_top_k(p=80, alpha=0.80, k_min=5, k_max=50) == 50


def test_resolve_top_k_in_range():
    """
    In-range tests where k_min <= raw_k <= k_max:
    - p = 40, alpha = 0.25 -> raw k = 10. (5 <= 10 <= 50) -> returns 10.
    - p = 100, alpha = 0.30 -> raw k = 30. (5 <= 30 <= 50) -> returns 30.
    - p = 60, alpha = 0.25 -> raw k = 15. (5 <= 15 <= 50) -> returns 15.
    """
    assert resolve_top_k(p=40, alpha=0.25, k_min=5, k_max=50) == 10
    assert resolve_top_k(p=100, alpha=0.30, k_min=5, k_max=50) == 30
    assert resolve_top_k(p=60, alpha=0.25, k_min=5, k_max=50) == 15


def test_resolve_top_k_edge_cases():
    """
    Edge cases: p = 1 and p = 0.
    """
    assert resolve_top_k(p=1, alpha=0.25, k_min=5, k_max=50) == 1
    assert resolve_top_k(p=0, alpha=0.25, k_min=5, k_max=50) == 0


def test_resolve_top_k_default_contract_values():
    """
    Verifies default values from FEATURE_SELECTION_DEFAULTS in contract.py.
    """
    alpha = FEATURE_SELECTION_DEFAULTS["alpha"]
    k_min = FEATURE_SELECTION_DEFAULTS["k_min"]
    k_max = FEATURE_SELECTION_DEFAULTS["k_max"]

    assert alpha == 0.25
    assert k_min == 5
    assert k_max == 50

    # Test with contract defaults
    assert resolve_top_k(p=20, alpha=alpha, k_min=k_min, k_max=k_max) == 5   # clamped lower
    assert resolve_top_k(p=40, alpha=alpha, k_min=k_min, k_max=k_max) == 10  # in-range
    assert resolve_top_k(p=300, alpha=alpha, k_min=k_min, k_max=k_max) == 50 # clamped upper


# =============================================================================
# 3. apply_top_k_percent_selection Integration Tests
# =============================================================================

def test_apply_top_k_percent_selection_lower_clamp():
    """
    p = 20 features, alpha = 0.10 (raw k = 2).
    Clamped to k = 5. Top 5 features must be selected.
    """
    feature_names = [f"f_{i:02d}" for i in range(20)]
    # Descending scores
    scores = {f"f_{i:02d}": 1.0 - (i / 20.0) for i in range(20)}

    res = apply_top_k_percent_selection(
        feature_names=feature_names,
        scores=scores,
        alpha=0.10,
        k_min=5,
        k_max=50,
    )

    assert res["k_selected"] == 5
    assert res["k_raw"] == 2
    assert len(res["selected_features"]) == 5
    assert res["selected_features"] == ["f_00", "f_01", "f_02", "f_03", "f_04"]

    # Verify is_selected_map
    for i in range(5):
        assert res["is_selected_map"][f"f_{i:02d}"] is True
    for i in range(5, 20):
        assert res["is_selected_map"][f"f_{i:02d}"] is False


def test_apply_top_k_percent_selection_upper_clamp():
    """
    p = 300 features, alpha = 0.25 (raw k = 75).
    Clamped to k = 50. Exactly top 50 features selected.
    """
    feature_names = [f"col_{i}" for i in range(300)]
    scores = {f"col_{i}": float(300 - i) for i in range(300)}

    res = apply_top_k_percent_selection(
        feature_names=feature_names,
        scores=scores,
        alpha=0.25,
        k_min=5,
        k_max=50,
    )

    assert res["k_selected"] == 50
    assert res["k_raw"] == 75
    assert len(res["selected_features"]) == 50
    assert res["selected_features"] == [f"col_{i}" for i in range(50)]
    assert res["is_selected_map"]["col_0"] is True
    assert res["is_selected_map"]["col_49"] is True
    assert res["is_selected_map"]["col_50"] is False


def test_apply_top_k_percent_selection_stable_ties():
    """
    When features have tied scores, stable sort maintains deterministic order.
    """
    feature_names = ["alpha_feat", "beta_feat", "gamma_feat", "delta_feat"]
    scores = {
        "alpha_feat": 0.8,
        "beta_feat": 0.8,
        "gamma_feat": 0.2,
        "delta_feat": 0.1,
    }

    res = apply_top_k_percent_selection(
        feature_names=feature_names,
        scores=scores,
        alpha=0.5,
        k_min=2,
        k_max=10,
    )

    assert res["k_selected"] == 2
    # Tied 0.8 scores preserved in input order
    assert res["selected_features"] == ["alpha_feat", "beta_feat"]
    assert res["is_selected_map"]["alpha_feat"] is True
    assert res["is_selected_map"]["beta_feat"] is True
    assert res["is_selected_map"]["gamma_feat"] is False


def test_apply_top_k_percent_selection_empty():
    """
    Empty feature list returns cleanly.
    """
    res = apply_top_k_percent_selection([], {})
    assert res["k_selected"] == 0
    assert res["selected_features"] == []
    assert res["is_selected_map"] == {}
