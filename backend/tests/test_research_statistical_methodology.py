"""
Tests for Research Track Statistical Methodology & Validation Isolation.
Verifies:
1. Permutation importance evaluation strictly on validation fold slice.
2. Kuncheva Stability Index calculation and chance correction.
3. Pairwise Jaccard Index calculation across folds.
4. Nogueira stability index calculation.
"""

import numpy as np
import pytest
from app.services.selectors import PermutationImportanceSelector
from research.stability import (
    compute_kuncheva_index,
    compute_pairwise_jaccard,
    compute_nogueira_stability,
    StabilityScorer,
)


def test_permutation_importance_validation_fold_isolation():
    """
    Verifies that permutation importance can evaluate on an independent validation fold
    rather than being restricted to the training fold.
    """
    np.random.seed(42)
    # 50 training samples, 20 validation samples, 5 features
    X_train = np.random.randn(50, 5)
    # Target depends strongly on feature 0 and feature 1 only
    y_train = 3.0 * X_train[:, 0] - 2.0 * X_train[:, 1] + np.random.randn(50) * 0.1

    X_val = np.random.randn(20, 5)
    y_val = 3.0 * X_val[:, 0] - 2.0 * X_val[:, 1] + np.random.randn(20) * 0.1

    selector = PermutationImportanceSelector()
    scores = selector.compute_raw_scores(
        X=X_train,
        y=y_train,
        task_type="REGRESSION",
        seed=42,
        X_val=X_val,
        y_val=y_val,
    )

    assert len(scores) == 5
    # Features 0 and 1 should have much higher permutation importance on validation set than noise features
    assert scores[0] > scores[2]
    assert scores[1] > scores[3]
    assert scores[0] > scores[4]


def test_pairwise_jaccard_calculation():
    """Verifies pairwise Jaccard calculation for identical, disjoint, and overlapping sets."""
    # Identical subsets -> Jaccard = 1.0
    subsets_identical = [["f1", "f2"], ["f1", "f2"], ["f1", "f2"]]
    assert compute_pairwise_jaccard(subsets_identical) == 1.0

    # Disjoint subsets -> Jaccard = 0.0
    subsets_disjoint = [["f1"], ["f2"]]
    assert compute_pairwise_jaccard(subsets_disjoint) == 0.0

    # 50% overlap: |{f1, f2} ∩ {f2, f3}| / |{f1, f2, f3}| = 1/3
    subsets_overlap = [["f1", "f2"], ["f2", "f3"]]
    assert pytest.approx(compute_pairwise_jaccard(subsets_overlap), 0.001) == 1.0 / 3.0


def test_kuncheva_index_calculation():
    """Verifies Kuncheva index chance-corrected stability calculation."""
    # Identical subsets of size 2 from 10 features -> Kuncheva = 1.0
    subsets_identical = [["f1", "f2"], ["f1", "f2"]]
    assert compute_kuncheva_index(subsets_identical, total_features=10) == 1.0

    # Disjoint subsets of size 2 from 10 features:
    # r = 0, k1 = 2, k2 = 2, p = 10 -> num = 0 - 4 = -4, denom = 20 - 4 = 16 -> K = -4/16 = -0.25
    subsets_disjoint = [["f1", "f2"], ["f3", "f4"]]
    assert pytest.approx(compute_kuncheva_index(subsets_disjoint, total_features=10), 0.001) == -0.25


def test_nogueira_stability_calculation():
    """Verifies Nogueira stability from binary indicator matrix."""
    # Perfect stability (all 3 runs select same 2 features out of 4)
    mat_perfect = np.array([
        [1, 1, 0, 0],
        [1, 1, 0, 0],
        [1, 1, 0, 0],
    ])
    assert compute_nogueira_stability(mat_perfect) == 1.0

    # Random / varying selection
    mat_varying = np.array([
        [1, 0, 1, 0],
        [0, 1, 1, 0],
        [1, 1, 0, 0],
    ])
    stab = compute_nogueira_stability(mat_varying)
    assert -1.0 <= stab <= 1.0
