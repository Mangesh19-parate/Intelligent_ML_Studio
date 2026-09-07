"""
Day 1 — Comprehensive Unit & Integration Tests:
Correlation + Lasso Selectors and SRS v9 Rank Formula (§2.7).
"""

import numpy as np
import pandas as pd
import pytest

from app.config.contract import FeatureSelectionMethod, TechniqueStatus
from app.services.selectors import (
    calculate_srs_rank_scores,
    CORRELATION_SELECTOR,
    LASSO_SELECTOR,
    CorrelationSelector,
    LassoSelector,
    SelectorOutput,
)
from app.services.feature_selection_service import FeatureSelectionService


# =============================================================================
# 1. SRS v9 Mathematical Rank Engine Tests (§2.7)
# =============================================================================

def test_srs_rank_formula_p_equals_one_edge_case():
    """
    SRS §2.7: p = 1 -> rank score = 1.0 (avoids p - 1 = 0 division error).
    """
    raw_scores = np.array([12.34])
    ranks, norm_scores = calculate_srs_rank_scores(raw_scores)

    assert len(ranks) == 1
    assert len(norm_scores) == 1
    assert ranks[0] == 1.0
    assert norm_scores[0] == 1.0


def test_srs_rank_formula_empty_p_zero():
    """
    Empty input array returns empty ranks and normalized scores.
    """
    ranks, norm_scores = calculate_srs_rank_scores(np.array([]))
    assert len(ranks) == 0
    assert len(norm_scores) == 0


def test_srs_rank_formula_strict_descending_order():
    """
    Standard descending ranking:
    scores = [10.0, 8.0, 6.0, 4.0] (p = 4)
    ranks  = [1.0, 2.0, 3.0, 4.0]
    norm   = [1.0, 0.666667, 0.333333, 0.0]
    """
    scores = np.array([10.0, 8.0, 6.0, 4.0])
    ranks, norm_scores = calculate_srs_rank_scores(scores)

    np.testing.assert_array_almost_equal(ranks, [1.0, 2.0, 3.0, 4.0])
    np.testing.assert_array_almost_equal(norm_scores, [1.0, 2.0 / 3.0, 1.0 / 3.0, 0.0])


def test_srs_rank_formula_average_rank_ties():
    """
    SRS §2.7: Ties receive the average rank.
    scores = [10.0, 10.0, 5.0] (p = 3)
    ranks  = [1.5, 1.5, 3.0]
    norm   = 1 - (rank - 1)/(3 - 1)
             rank 1.5 -> 1 - 0.5/2 = 0.75
             rank 3.0 -> 1 - 2.0/2 = 0.0
    """
    scores = np.array([10.0, 10.0, 5.0])
    ranks, norm_scores = calculate_srs_rank_scores(scores)

    np.testing.assert_array_almost_equal(ranks, [1.5, 1.5, 3.0])
    np.testing.assert_array_almost_equal(norm_scores, [0.75, 0.75, 0.0])


def test_srs_rank_formula_all_tied_features():
    """
    All features tied:
    scores = [7.0, 7.0, 7.0, 7.0] (p = 4)
    ranks  = [2.5, 2.5, 2.5, 2.5]
    norm   = 1 - (2.5 - 1)/(4 - 1) = 1 - 1.5/3 = 0.5
    """
    scores = np.array([7.0, 7.0, 7.0, 7.0])
    ranks, norm_scores = calculate_srs_rank_scores(scores)

    np.testing.assert_array_almost_equal(ranks, [2.5, 2.5, 2.5, 2.5])
    np.testing.assert_array_almost_equal(norm_scores, [0.5, 0.5, 0.5, 0.5])


def test_srs_rank_formula_absolute_score_ranking():
    """
    Negative values are ranked by absolute magnitude (|score|).
    scores = [-10.0, 5.0, -1.0] -> abs = [10.0, 5.0, 1.0]
    ranks  = [1.0, 2.0, 3.0]
    norm   = [1.0, 0.5, 0.0]
    """
    scores = np.array([-10.0, 5.0, -1.0])
    ranks, norm_scores = calculate_srs_rank_scores(scores)

    np.testing.assert_array_almost_equal(ranks, [1.0, 2.0, 3.0])
    np.testing.assert_array_almost_equal(norm_scores, [1.0, 0.5, 0.0])


def test_srs_rank_formula_nan_and_inf_safety():
    """
    NaNs or Infs should be safely replaced with 0.0 and receive lowest ranks.
    """
    scores = np.array([10.0, np.nan, 5.0, np.inf])
    # inf becomes 0, nan becomes 0, so [10, 0, 5, 0] -> abs [10, 0, 5, 0]
    # ranks: 10->1, 5->2, 0 and 0 tied for 3 and 4 -> 3.5
    ranks, norm_scores = calculate_srs_rank_scores(scores)
    assert ranks[0] == 1.0
    assert ranks[2] == 2.0
    assert ranks[1] == 3.5
    assert ranks[3] == 3.5


# =============================================================================
# 2. CORRELATION_SELECTOR Tests
# =============================================================================

def test_correlation_selector_regression():
    """
    Tests correlation selector on continuous regression data.
    """
    np.random.seed(42)
    n = 150
    x1 = np.random.normal(0, 1, n)
    x2 = np.random.normal(0, 1, n)
    x3 = np.random.normal(0, 1, n)
    y = 5.0 * x1 + 2.5 * x2 + np.random.normal(0, 0.2, n)

    X = np.column_stack([x1, x2, x3])
    feature_names = ["feat_strong", "feat_weak", "feat_noise"]

    output = CORRELATION_SELECTOR.select(
        X=X,
        y=y,
        task_type="REGRESSION",
        feature_names=feature_names,
    )

    assert isinstance(output, SelectorOutput)
    assert output.status == TechniqueStatus.APPLIED
    assert output.method_name == FeatureSelectionMethod.CORRELATION.value
    assert output.raw_scores[0] > output.raw_scores[1] > output.raw_scores[2]
    assert output.ranks[0] == 1.0
    assert output.rank_scores[0] == 1.0
    assert output.rank_scores[2] == 0.0

    feat_map = output.to_feature_map()
    assert feat_map["feat_strong"]["status"] == "APPLIED"
    assert feat_map["feat_strong"]["rank"] == 1.0
    assert feat_map["feat_strong"]["rank_score"] == 1.0


def test_correlation_selector_binary_classification():
    """
    Tests correlation selector on binary classification data.
    """
    np.random.seed(42)
    n = 100
    x_signal = np.random.normal(0, 1, n)
    x_noise = np.random.normal(0, 1, n)
    y = (x_signal > 0).astype(int)

    X = np.column_stack([x_signal, x_noise])
    output = CORRELATION_SELECTOR.select(
        X=X,
        y=y,
        task_type="CLASSIFICATION",
        feature_names=["signal", "noise"],
    )

    assert output.status == TechniqueStatus.APPLIED
    assert output.raw_scores[0] > output.raw_scores[1]
    assert output.ranks[0] == 1.0
    assert output.ranks[1] == 2.0


def test_correlation_selector_multiclass_classification():
    """
    Tests correlation selector on multiclass string categories.
    """
    np.random.seed(42)
    n = 120
    x1 = np.random.normal(0, 1, n)
    x2 = np.random.normal(0, 1, n)
    x3 = np.random.normal(0, 1, n)
    
    # Target classes correlated with x1
    labels = []
    for val in x1:
        if val < -0.5:
            labels.append("class_A")
        elif val < 0.5:
            labels.append("class_B")
        else:
            labels.append("class_C")
    
    y = np.array(labels)
    X = np.column_stack([x1, x2, x3])
    feature_names = ["signal", "noise1", "noise2"]

    output = CORRELATION_SELECTOR.select(
        X=X,
        y=y,
        task_type="CLASSIFICATION",
        feature_names=feature_names,
    )

    assert output.status == TechniqueStatus.APPLIED
    assert output.raw_scores[0] > output.raw_scores[1]
    assert output.ranks[0] == 1.0


def test_correlation_selector_zero_variance_column():
    """
    Zero-variance (constant) columns must receive 0.0 correlation and lowest rank.
    """
    np.random.seed(42)
    n = 50
    x_active = np.random.normal(0, 1, n)
    x_const = np.full(n, 42.0)  # constant zero variance
    y = 2.0 * x_active + np.random.normal(0, 0.1, n)

    X = np.column_stack([x_active, x_const])
    output = CORRELATION_SELECTOR.select(
        X=X,
        y=y,
        task_type="REGRESSION",
        feature_names=["active", "const"],
    )

    assert output.status == TechniqueStatus.APPLIED
    assert output.raw_scores[1] == 0.0
    assert output.ranks[0] == 1.0
    assert output.ranks[1] == 2.0


def test_correlation_selector_single_feature_p1():
    """
    p = 1 single feature input test.
    """
    np.random.seed(42)
    n = 40
    X = np.random.normal(0, 1, (n, 1))
    y = X[:, 0] * 3.0 + np.random.normal(0, 0.1, n)

    output = CORRELATION_SELECTOR.select(
        X=X,
        y=y,
        task_type="REGRESSION",
        feature_names=["only_feature"],
    )

    assert output.status == TechniqueStatus.APPLIED
    assert len(output.ranks) == 1
    assert output.ranks[0] == 1.0
    assert output.rank_scores[0] == 1.0


# =============================================================================
# 3. LASSO_SELECTOR Tests
# =============================================================================

def test_lasso_selector_regression():
    """
    Tests Lasso selector on regression task.
    """
    np.random.seed(42)
    n = 100
    x1 = np.random.normal(0, 1, n)
    x2 = np.random.normal(0, 1, n)
    x3 = np.random.normal(0, 1, n)
    y = 10.0 * x1 + 2.0 * x2 + np.random.normal(0, 0.1, n)

    X = np.column_stack([x1, x2, x3])
    output = LASSO_SELECTOR.select(
        X=X,
        y=y,
        task_type="REGRESSION",
        feature_names=["feat1", "feat2", "noise"],
        seed=42,
    )

    assert output.status == TechniqueStatus.APPLIED
    assert output.method_name == FeatureSelectionMethod.LASSO.value
    assert output.raw_scores[0] > output.raw_scores[1]
    assert output.ranks[0] == 1.0
    assert output.rank_scores[0] == 1.0


def test_lasso_selector_classification():
    """
    Tests Lasso selector (L1 Logistic Regression) on classification.
    """
    np.random.seed(42)
    n = 100
    x1 = np.random.normal(0, 1, n)
    x2 = np.random.normal(0, 1, n)
    y = (x1 * 3.0 + np.random.normal(0, 0.2, n) > 0).astype(int)

    X = np.column_stack([x1, x2])
    output = LASSO_SELECTOR.select(
        X=X,
        y=y,
        task_type="CLASSIFICATION",
        feature_names=["sig", "noise"],
        seed=42,
    )

    assert output.status == TechniqueStatus.APPLIED
    assert output.raw_scores[0] > output.raw_scores[1]
    assert output.ranks[0] == 1.0
    assert output.ranks[1] == 2.0


def test_lasso_selector_multiclass():
    """
    Tests Lasso selector with multiclass target averaging coefficients across classes.
    """
    np.random.seed(42)
    n = 90
    x1 = np.random.normal(0, 1, n)
    x2 = np.random.normal(0, 1, n)
    x3 = np.random.normal(0, 1, n)
    y = np.random.choice(["catA", "catB", "catC"], size=n)

    X = np.column_stack([x1, x2, x3])
    output = LASSO_SELECTOR.select(
        X=X,
        y=y,
        task_type="CLASSIFICATION",
        feature_names=["f1", "f2", "f3"],
        seed=42,
    )

    assert output.status == TechniqueStatus.APPLIED
    assert len(output.raw_scores) == 3
    assert len(output.ranks) == 3


def test_lasso_selector_single_feature_p1():
    """
    Lasso selector with p=1 single feature.
    """
    np.random.seed(42)
    n = 50
    X = np.random.normal(0, 1, (n, 1))
    y = X[:, 0] * 2.0 + np.random.normal(0, 0.1, n)

    output = LASSO_SELECTOR.select(
        X=X,
        y=y,
        task_type="REGRESSION",
        feature_names=["sole_feature"],
    )

    assert output.status == TechniqueStatus.APPLIED
    assert output.ranks[0] == 1.0
    assert output.rank_scores[0] == 1.0


def test_lasso_selector_reproducibility():
    """
    Seed guarantees deterministic reproducibility.
    """
    np.random.seed(42)
    n, p = 80, 5
    X = np.random.normal(0, 1, (n, p))
    y = np.random.choice([0, 1], size=n)

    out1 = LASSO_SELECTOR.select(X, y, "CLASSIFICATION", seed=123)
    out2 = LASSO_SELECTOR.select(X, y, "CLASSIFICATION", seed=123)

    np.testing.assert_array_equal(out1.raw_scores, out2.raw_scores)
    np.testing.assert_array_equal(out1.ranks, out2.ranks)
    np.testing.assert_array_equal(out1.rank_scores, out2.rank_scores)


def test_selector_pandas_dataframe_input():
    """
    Verifies DataFrame inputs work directly with column names preserved.
    """
    df = pd.DataFrame({
        "col_a": [1.0, 2.0, 3.0, 4.0, 5.0],
        "col_b": [5.0, 4.0, 3.0, 2.0, 1.0],
        "col_c": [0.0, 0.0, 0.0, 0.0, 0.0],
    })
    y = pd.Series([10.0, 20.0, 30.0, 40.0, 50.0])

    out = CORRELATION_SELECTOR.select(df, y, task_type="REGRESSION")
    assert out.feature_names == ["col_a", "col_b", "col_c"]
    assert out.to_feature_map()["col_a"]["rank"] == 1.5  # col_a (+1.0) and col_b (-1.0) tied at abs correlation 1.0
    assert out.to_feature_map()["col_b"]["rank"] == 1.5
    assert out.to_feature_map()["col_c"]["rank"] == 3.0
