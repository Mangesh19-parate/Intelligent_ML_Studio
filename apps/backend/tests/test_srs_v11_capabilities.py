"""
Comprehensive Test Suite for SRS v11 Granular Taxonomy and New Capabilities.
Covers:
1. Mixed-Variable Handling (COERCE_NUMERIC, COERCE_CATEGORICAL, SPLIT) - deterministic
2. Date/Time Features & Temporal Leakage Guard (test_temporal_reference_fit_scope)
3. Active Outlier Remediation (IQR capping) - fold-scoped
4. Feature Construction & Construction Ledger - deterministic + Development-only correlation
5. Feature Extraction PCA (test_extraction_fit_scope) - fold-scoped
"""

import pytest
import numpy as np
import pandas as pd
from sklearn.exceptions import NotFittedError

from app.services.transformers import (
    MixedVariableResolver,
    DateTimeFeatureExtractor,
    TemporalReferenceTransformer,
    OutlierCapper,
    FoldScopedFeatureExtractor,
)
from app.services.feature_construction_service import (
    FeatureConstructor,
    FeatureConstructionService,
)


# ==============================================================================
# 1. MIXED-VARIABLE RESOLUTION (SRS v11 §2)
# ==============================================================================

def test_mixed_variable_resolution_deterministic():
    """
    SRS v11 §2: Verifies deterministic resolution of MIXED-dtype columns without cross-row leakage.
    """
    raw_mixed = pd.Series(["10.5", "20", "invalid_str", "30.2", "N/A", "40"])

    # 1. COERCE_NUMERIC: parse what parses, unparseable -> NaN
    res_num = MixedVariableResolver(strategy="COERCE_NUMERIC").transform(raw_mixed)
    assert np.isnan(res_num[2, 0])
    assert np.isnan(res_num[4, 0])
    assert res_num[0, 0] == 10.5
    assert res_num[5, 0] == 40.0

    # 2. COERCE_CATEGORICAL: stringify everything
    res_cat = MixedVariableResolver(strategy="COERCE_CATEGORICAL").transform(raw_mixed)
    assert res_cat[0, 0] == "10.5"
    assert res_cat[2, 0] == "invalid_str"

    # 3. SPLIT: produces 2 columns (numeric value + boolean was_non_numeric flag)
    resolver_split = MixedVariableResolver(strategy="SPLIT")
    res_split = resolver_split.transform(raw_mixed)
    assert res_split.shape == (6, 2)
    # Row 2 was "invalid_str" -> numeric NaN, was_non_numeric = 1.0
    assert np.isnan(res_split[2, 0])
    assert res_split[2, 1] == 1.0
    # Row 0 was "10.5" -> numeric 10.5, was_non_numeric = 0.0
    assert res_split[0, 0] == 10.5
    assert res_split[0, 1] == 0.0

    names = resolver_split.get_feature_names_out(["val"])
    assert list(names) == ["val_num", "val_was_non_numeric"]


# ==============================================================================
# 2. DATE/TIME FEATURE HANDLING & TEMPORAL LEAKAGE GUARD (SRS v11 §3)
# ==============================================================================

def test_datetime_feature_extractor_deterministic():
    """
    SRS v11 §3: Verifies deterministic calendar components and cyclical sin/cos encodings.
    """
    dates = pd.Series(["2024-01-15", "2024-06-20", "2024-12-31"])
    extractor = DateTimeFeatureExtractor(include_calendar=True, include_cyclical=True)
    res = extractor.transform(dates)

    # 6 calendar components + 4 cyclical components = 10 columns
    assert res.shape == (3, 10)
    # January: month=1, sin(2*pi*1/12) > 0
    assert res[0, 1] == 1.0
    assert np.isclose(res[0, 6], np.sin(2 * np.pi * 1.0 / 12.0))


def test_temporal_reference_fit_scope():
    """
    SRS v11 §3 INVARIANT TEST: Temporal Leakage Guard.
    Confirms any dataset-derived reference date is a LEARNED statistic that MUST be fit
    strictly inside training folds and is UNFIT prior to calling fit().
    """
    transformer = TemporalReferenceTransformer(reference_strategy="dataset_min")
    
    # 1. Assert transformer is completely unfit prior to fit()
    assert not hasattr(transformer, "reference_date_")
    with pytest.raises(NotFittedError):
        transformer.transform(pd.Series(["2024-05-01"]))

    # 2. Fit on training fold partition
    train_dates = pd.Series(["2023-01-01", "2023-06-01", "2023-12-01"])
    transformer.fit(train_dates)

    # 3. Assert reference date was learned strictly from training data
    assert hasattr(transformer, "reference_date_")
    assert transformer.reference_date_ == pd.Timestamp("2023-01-01")

    # 4. Transform computes elapsed days since learned reference
    test_dates = pd.Series(["2023-01-11"])
    elapsed = transformer.transform(test_dates)
    assert np.isclose(elapsed[0, 0], 10.0)


# ==============================================================================
# 3. ACTIVE OUTLIER REMEDIATION (SRS v11 §4)
# ==============================================================================

def test_active_outlier_remediation_fold_scoped():
    """
    SRS v11 §4 INVARIANT TEST: Confirms Active Outlier Remediation computes IQR thresholds
    strictly during fit() and is UNFIT prior to fit().
    """
    capper = OutlierCapper(strategy="iqr", iqr_multiplier=1.5)

    # 1. Assert unfit state
    assert not hasattr(capper, "lower_bounds_")
    assert not hasattr(capper, "upper_bounds_")
    with pytest.raises(NotFittedError):
        capper.transform(np.array([[10.0], [20.0]]))

    # 2. Fit on training fold with outliers
    X_train = np.array([[10.0], [12.0], [11.0], [13.0], [10.5], [100.0], [-50.0]])
    capper.fit(X_train)

    assert hasattr(capper, "lower_bounds_")
    assert hasattr(capper, "upper_bounds_")
    assert capper.upper_bounds_[0] < 50.0  # Successfully learned upper IQR boundary

    # 3. Transform clips test values against learned thresholds
    X_test = np.array([[1000.0], [-1000.0], [11.5]])
    clipped = capper.transform(X_test)
    assert clipped[0, 0] == capper.upper_bounds_[0]
    assert clipped[1, 0] == capper.lower_bounds_[0]
    assert clipped[2, 0] == 11.5


# ==============================================================================
# 4. FEATURE CONSTRUCTION & CONSTRUCTION LEDGER (SRS v11 §5)
# ==============================================================================

def test_feature_construction_arithmetic():
    """
    SRS v11 §5: Verifies deterministic feature construction for interactions, ratios, and polynomials.
    """
    df = pd.DataFrame({
        "revenue": [100.0, 200.0, 300.0],
        "users": [10.0, 0.0, 50.0],
        "cost": [50.0, 80.0, 120.0],
    })

    # 1. Interaction: A * B
    s_inter, f_inter = FeatureConstructor.construct_interaction(df, "revenue", "cost")
    assert f_inter == "revenue * cost"
    assert s_inter.iloc[0] == 5000.0

    # 2. Ratio with divide-by-zero protection: A / B -> NaN when B == 0
    s_ratio, f_ratio = FeatureConstructor.construct_ratio(df, "revenue", "users")
    assert s_ratio.iloc[0] == 10.0
    assert np.isnan(s_ratio.iloc[1])  # users == 0.0 guarded to NaN
    assert s_ratio.iloc[2] == 6.0

    # 3. Polynomial: A^2
    s_poly, f_poly = FeatureConstructor.construct_polynomial(df, "revenue", degree=2)
    assert f_poly == "revenue^2"
    assert s_poly.iloc[0] == 10000.0


# ==============================================================================
# 5. FEATURE EXTRACTION - DIMENSIONALITY REDUCTION (SRS v11 §6)
# ==============================================================================

def test_extraction_fit_scope():
    """
    SRS v11 §6 INVARIANT TEST: Confirms PCA Feature Extraction is UNFIT before fit(),
    learns SVD covariance components strictly within the training fold, and exposes explained variance evidence.
    """
    extractor = FoldScopedFeatureExtractor(n_components=2, random_state=42)

    # 1. Assert unfit state
    assert not hasattr(extractor, "pca_")
    assert not hasattr(extractor, "explained_variance_ratio_")
    with pytest.raises(NotFittedError):
        extractor.transform(np.random.randn(10, 5))

    # 2. Fit on training fold (5 features -> 2 components)
    rng = np.random.RandomState(42)
    X_train = rng.randn(50, 5)
    extractor.fit(X_train)

    # 3. Assert learned parameters & explained variance evidence
    assert hasattr(extractor, "pca_")
    assert hasattr(extractor, "explained_variance_ratio_")
    assert len(extractor.explained_variance_ratio_) == 2
    assert 0.0 < extractor.cumulative_variance_ <= 1.0

    # 4. Transform projects into 2 components
    X_test = rng.randn(10, 5)
    transformed = extractor.transform(X_test)
    assert transformed.shape == (10, 2)
    names = extractor.get_feature_names_out()
    assert list(names) == ["pca_component_1", "pca_component_2"]
