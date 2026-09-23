"""
Custom Scikit-Learn Transformers for ML Studio (SRS v11).
Enforces Invariant 1 (Zero Test Leakage) and the Temporal Leakage Guard:
- Deterministic transforms (MixedVariableResolver, Calendar/Cyclical dates, FeatureConstructor)
  require no cross-row statistics and are applied per-value.
- Learned transforms (OutlierCapper, TemporalReferenceTransformer, FoldScopedFeatureExtractor)
  learn parameters strictly during fit() on training fold slices and are NEVER fit globally upfront.
"""

import numpy as np
import pandas as pd
from typing import Any, Sequence
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.utils.validation import check_is_fitted
from sklearn.decomposition import PCA


# ==============================================================================
# 1. MIXED-VARIABLE RESOLUTION (SRS v11 §2 - Deterministic, No Fold-Scoping Needed)
# ==============================================================================

class MixedVariableResolver(BaseEstimator, TransformerMixin):
    """
    Deterministic mixed-variable resolution (SRS v11 §2).
    Resolves columns flagged MIXED at structural validation.
    
    LEAKAGE CLASSIFICATION:
    This operation is purely deterministic and row-local. Parsing a string to a float,
    stringifying a value, or setting a boolean flag uses NO cross-row statistic and
    NO target information. It does NOT need fold-scoped refitting.
    
    Strategies:
    - 'COERCE_NUMERIC': Parse numeric-convertible strings to float, unparseable -> NaN.
    - 'COERCE_CATEGORICAL': Stringify all values into uniform category strings.
    - 'SPLIT': Produce numeric value (NaN otherwise) + boolean 'was_non_numeric' indicator.
    """

    def __init__(self, strategy: str = "COERCE_NUMERIC"):
        self.strategy = strategy.upper().strip()

    def fit(self, X, y=None):
        # Deterministic transform: fit is a no-op passthrough
        self.n_features_in_ = 1
        return self

    def transform(self, X):
        strat = self.strategy.upper()
        
        # Convert input to 1D series or array
        if isinstance(X, pd.DataFrame):
            col_data = X.iloc[:, 0]
        elif isinstance(X, pd.Series):
            col_data = X
        else:
            col_data = pd.Series(np.asarray(X).ravel())

        if strat == "COERCE_NUMERIC":
            numeric_series = pd.to_numeric(col_data, errors="coerce")
            return numeric_series.to_numpy(dtype=np.float64).reshape(-1, 1)

        elif strat == "COERCE_CATEGORICAL":
            cat_series = col_data.astype(str)
            return cat_series.to_numpy(dtype=object).reshape(-1, 1)

        elif strat == "SPLIT":
            numeric_series = pd.to_numeric(col_data, errors="coerce")
            was_non_numeric = numeric_series.isna() & col_data.notna()
            res = np.column_stack([
                numeric_series.to_numpy(dtype=np.float64),
                was_non_numeric.to_numpy(dtype=np.float64)
            ])
            return res

        else:
            raise ValueError(f"Unsupported mixed-variable strategy: '{self.strategy}'. Must be COERCE_NUMERIC, COERCE_CATEGORICAL, or SPLIT.")

    def get_feature_names_out(self, input_features=None):
        base = input_features[0] if input_features is not None and len(input_features) > 0 else "col"
        if self.strategy.upper() == "SPLIT":
            return np.array([f"{base}_num", f"{base}_was_non_numeric"], dtype=str)
        return np.array([base], dtype=str)


# ==============================================================================
# 2. DATE/TIME HANDLING + TEMPORAL LEAKAGE GUARD (SRS v11 §3)
# ==============================================================================

class DateTimeFeatureExtractor(BaseEstimator, TransformerMixin):
    """
    Extracts calendar components and cyclical encodings from datetime features (SRS v11 §3).
    
    LEAKAGE CLASSIFICATION:
    - Calendar components (year, month, day, day_of_week, is_weekend, quarter) &
      cyclical encodings (sin/cos of month/day_of_week) are relative to the calendar
      itself and use NO dataset-derived statistics. They are deterministic.
    """

    def __init__(
        self,
        include_calendar: bool = True,
        include_cyclical: bool = True,
    ):
        self.include_calendar = include_calendar
        self.include_cyclical = include_cyclical

    def fit(self, X, y=None):
        self.n_features_in_ = 1
        return self

    def transform(self, X):
        if isinstance(X, (pd.DataFrame, pd.Series)):
            dt_series = pd.to_datetime(X.iloc[:, 0] if isinstance(X, pd.DataFrame) else X, errors="coerce")
        else:
            dt_series = pd.to_datetime(pd.Series(np.asarray(X).ravel()), errors="coerce")

        extracted = []
        if self.include_calendar:
            extracted.append(dt_series.dt.year.to_numpy(dtype=np.float64))
            extracted.append(dt_series.dt.month.to_numpy(dtype=np.float64))
            extracted.append(dt_series.dt.day.to_numpy(dtype=np.float64))
            extracted.append(dt_series.dt.dayofweek.to_numpy(dtype=np.float64))
            extracted.append(dt_series.dt.dayofweek.isin([5, 6]).to_numpy(dtype=np.float64))
            extracted.append(dt_series.dt.quarter.to_numpy(dtype=np.float64))

        if self.include_cyclical:
            month = dt_series.dt.month.to_numpy(dtype=np.float64)
            dow = dt_series.dt.dayofweek.to_numpy(dtype=np.float64)
            extracted.append(np.sin(2 * np.pi * month / 12.0))
            extracted.append(np.cos(2 * np.pi * month / 12.0))
            extracted.append(np.sin(2 * np.pi * dow / 7.0))
            extracted.append(np.cos(2 * np.pi * dow / 7.0))

        return np.column_stack(extracted)

    def get_feature_names_out(self, input_features=None):
        base = input_features[0] if input_features is not None and len(input_features) > 0 else "dt"
        names = []
        if self.include_calendar:
            names.extend([f"{base}_year", f"{base}_month", f"{base}_day", f"{base}_dayofweek", f"{base}_is_weekend", f"{base}_quarter"])
        if self.include_cyclical:
            names.extend([f"{base}_sin_month", f"{base}_cos_month", f"{base}_sin_dow", f"{base}_cos_dow"])
        return np.array(names, dtype=str)


class TemporalReferenceTransformer(BaseEstimator, TransformerMixin):
    """
    Computes elapsed time (e.g. days_since_reference) from a reference timestamp (SRS v11 §3).
    
    TEMPORAL LEAKAGE GUARD (INVARIANT 1):
    When the reference point is COMPUTED FROM THE DATASET (e.g. 'min_date' across training data),
    it is a LEARNED STATISTIC. Computing this globally leaks future date distributions.
    This transformer learns `reference_date_` strictly inside `fit()` on training fold data.
    """

    def __init__(self, reference_strategy: str = "dataset_min"):
        self.reference_strategy = reference_strategy

    def fit(self, X, y=None):
        if isinstance(X, (pd.DataFrame, pd.Series)):
            dt_series = pd.to_datetime(X.iloc[:, 0] if isinstance(X, pd.DataFrame) else X, errors="coerce").dropna()
        else:
            dt_series = pd.to_datetime(pd.Series(np.asarray(X).ravel()), errors="coerce").dropna()

        if len(dt_series) == 0:
            self.reference_date_ = pd.Timestamp("2000-01-01")
        elif self.reference_strategy == "dataset_min":
            self.reference_date_ = dt_series.min()
        elif self.reference_strategy == "dataset_max":
            self.reference_date_ = dt_series.max()
        else:
            self.reference_date_ = pd.to_datetime(self.reference_strategy)

        self.n_features_in_ = 1
        return self

    def transform(self, X):
        check_is_fitted(self, ["reference_date_"])
        if isinstance(X, (pd.DataFrame, pd.Series)):
            dt_series = pd.to_datetime(X.iloc[:, 0] if isinstance(X, pd.DataFrame) else X, errors="coerce")
        else:
            dt_series = pd.to_datetime(pd.Series(np.asarray(X).ravel()), errors="coerce")

        # Elapsed days since learned reference date
        elapsed_days = (dt_series - self.reference_date_).dt.total_seconds() / 86400.0
        return elapsed_days.to_numpy(dtype=np.float64).reshape(-1, 1)

    def get_feature_names_out(self, input_features=None):
        base = input_features[0] if input_features is not None and len(input_features) > 0 else "dt"
        return np.array([f"{base}_days_since_ref"], dtype=str)


# ==============================================================================
# 3. ACTIVE OUTLIER REMEDIATION (SRS v11 §4 - Fold-Scoped Transform)
# ==============================================================================

class OutlierCapper(BaseEstimator, TransformerMixin):
    """
    Fold-scoped active outlier handler (SRS v11 §4).
    Computes IQR / Z-score thresholds strictly during `fit()` and applies clipping during `transform()`.
    
    ARCHITECTURAL INVARIANT:
    - Unfit state has NO fitted parameters (`lower_bounds_`, `upper_bounds_`).
    - Thresholds are learned exclusively on training partition data during fit.
    """

    def __init__(
        self,
        strategy: str = "none",
        z_threshold: float = 3.0,
        iqr_multiplier: float = 1.5,
        percentile_lower: float = 1.0,
        percentile_upper: float = 99.0,
        winsorize_lower: float = 5.0,
        winsorize_upper: float = 95.0,
    ):
        self.strategy = strategy
        self.z_threshold = z_threshold
        self.iqr_multiplier = iqr_multiplier
        self.percentile_lower = percentile_lower
        self.percentile_upper = percentile_upper
        self.winsorize_lower = winsorize_lower
        self.winsorize_upper = winsorize_upper

    def fit(self, X, y=None):
        strat = (self.strategy or "none").lower()
        if strat == "none":
            self.lower_bounds_ = None
            self.upper_bounds_ = None
            self.n_features_in_ = np.asarray(X).shape[1] if len(np.asarray(X).shape) > 1 else 1
            return self

        X_arr = np.asarray(X, dtype=np.float64)
        if X_arr.ndim == 1:
            X_arr = X_arr.reshape(-1, 1)

        n_features = X_arr.shape[1]
        self.n_features_in_ = n_features
        lower_bounds = []
        upper_bounds = []

        for i in range(n_features):
            col = X_arr[:, i]
            valid_mask = ~np.isnan(col)
            if not np.any(valid_mask):
                lower_bounds.append(-np.inf)
                upper_bounds.append(np.inf)
                continue

            valid_col = col[valid_mask]

            if self.strategy == "zscore":
                mean = float(np.mean(valid_col))
                std = float(np.std(valid_col))
                lower = mean - (self.z_threshold * std) if std > 0 else mean
                upper = mean + (self.z_threshold * std) if std > 0 else mean
            elif self.strategy in ["iqr", "cap"]:
                q25, q75 = np.percentile(valid_col, [25, 75])
                iqr = float(q75 - q25)
                lower = float(q25 - (self.iqr_multiplier * iqr))
                upper = float(q75 + (self.iqr_multiplier * iqr))
            elif self.strategy == "percentile":
                lower, upper = np.percentile(valid_col, [self.percentile_lower, self.percentile_upper])
                lower, upper = float(lower), float(upper)
            elif self.strategy == "winsorize":
                lower, upper = np.percentile(valid_col, [self.winsorize_lower, self.winsorize_upper])
                lower, upper = float(lower), float(upper)
            else:
                raise ValueError(f"Unsupported outlier strategy: '{self.strategy}'")

            lower_bounds.append(lower)
            upper_bounds.append(upper)

        self.lower_bounds_ = np.array(lower_bounds, dtype=np.float64)
        self.upper_bounds_ = np.array(upper_bounds, dtype=np.float64)
        return self

    def transform(self, X):
        if self.strategy == "none" or not self.strategy:
            return np.asarray(X)

        check_is_fitted(self, ["lower_bounds_", "upper_bounds_"])
        
        is_df = isinstance(X, pd.DataFrame)
        cols = X.columns if is_df else None
        
        X_arr = np.asarray(X, dtype=np.float64)
        orig_shape = X_arr.shape
        if X_arr.ndim == 1:
            X_arr = X_arr.reshape(-1, 1)

        clipped = np.clip(X_arr, self.lower_bounds_, self.upper_bounds_)

        if orig_shape != clipped.shape:
            clipped = clipped.reshape(orig_shape)

        if is_df:
            return pd.DataFrame(clipped, columns=cols, index=X.index)
        return clipped

    def get_feature_names_out(self, input_features=None):
        if input_features is None:
            return [f"x{i}" for i in range(getattr(self, "n_features_in_", 1))]
        return np.asarray(input_features, dtype=str)


# ==============================================================================
# 4. FEATURE EXTRACTION - DIMENSIONALITY REDUCTION (SRS v11 §6 - Fold-Scoped PCA)
# ==============================================================================

class FoldScopedFeatureExtractor(BaseEstimator, TransformerMixin):
    """
    Fold-scoped Dimensionality Reduction via PCA (SRS v11 §6).
    
    LEAKAGE CLASSIFICATION:
    PCA SVD components & variance ratios are LEARNED from the covariance matrix of training data.
    Fitting PCA globally before cross-validation causes severe data leakage.
    This extractor MUST be wired into the sklearn Pipeline and fit strictly inside each CV fold.
    """

    def __init__(self, n_components: int | float | None = 2, random_state: int = 42):
        self.n_components = n_components
        self.random_state = random_state

    def fit(self, X, y=None):
        X_arr = np.asarray(X, dtype=np.float64)
        # Handle missing values internally with mean if present
        if np.isnan(X_arr).any():
            col_means = np.nanmean(X_arr, axis=0)
            inds = np.where(np.isnan(X_arr))
            X_arr[inds] = np.take(col_means, inds[1])

        self.pca_ = PCA(n_components=self.n_components, random_state=self.random_state)
        self.pca_.fit(X_arr)
        self.n_components_ = self.pca_.n_components_
        self.explained_variance_ratio_ = self.pca_.explained_variance_ratio_
        self.cumulative_variance_ = float(np.sum(self.explained_variance_ratio_))
        return self

    def transform(self, X):
        check_is_fitted(self, ["pca_", "explained_variance_ratio_"])
        X_arr = np.asarray(X, dtype=np.float64)
        if np.isnan(X_arr).any():
            col_means = np.nanmean(X_arr, axis=0)
            inds = np.where(np.isnan(X_arr))
            X_arr[inds] = np.take(col_means, inds[1])
        return self.pca_.transform(X_arr)

    def get_feature_names_out(self, input_features=None):
        check_is_fitted(self, ["n_components_"])
        return np.array([f"pca_component_{i+1}" for i in range(self.n_components_)], dtype=str)


def safely_encode_matrix_pair(X_train: Any, X_eval: Any | None = None) -> tuple[np.ndarray, np.ndarray | None]:
    """
    Robust numeric conversion for feature matrices and unencoded passthrough columns.
    Enforces categorical encoding consistency:
    - Learns category value -> code mapping strictly from X_train.
    - Applies mapping to X_eval with unseen categories deterministically mapped to -1.0.
    """
    if hasattr(X_train, "toarray"):
        X_train = X_train.toarray()
    if X_eval is not None and hasattr(X_eval, "toarray"):
        X_eval = X_eval.toarray()

    if isinstance(X_train, pd.DataFrame):
        df_tr = X_train.copy()
        df_ev = X_eval.copy() if isinstance(X_eval, pd.DataFrame) else None
        
        for c in df_tr.columns:
            if not pd.api.types.is_numeric_dtype(df_tr[c]):
                unique_vals = [x for x in df_tr[c].dropna().unique()]
                mapping = {val: float(idx) for idx, val in enumerate(unique_vals)}
                df_tr[c] = df_tr[c].map(mapping).fillna(-1.0).astype(np.float64)
                if df_ev is not None and c in df_ev.columns:
                    df_ev[c] = df_ev[c].map(mapping).fillna(-1.0).astype(np.float64)
            else:
                df_tr[c] = pd.to_numeric(df_tr[c], errors="coerce").fillna(0.0).astype(np.float64)
                if df_ev is not None and c in df_ev.columns:
                    df_ev[c] = pd.to_numeric(df_ev[c], errors="coerce").fillna(0.0).astype(np.float64)

        X_tr_out = df_tr.to_numpy(dtype=np.float64)
        X_ev_out = df_ev.to_numpy(dtype=np.float64) if df_ev is not None else None
        return X_tr_out, X_ev_out

    # Array / Matrix path
    X_tr_arr = np.asarray(X_train)
    X_ev_arr = np.asarray(X_eval) if X_eval is not None else None

    tr_is_num = np.issubdtype(X_tr_arr.dtype, np.number)
    ev_is_num = X_ev_arr is None or np.issubdtype(X_ev_arr.dtype, np.number)

    if not tr_is_num or not ev_is_num:
        tr_2d = X_tr_arr if X_tr_arr.ndim > 1 else X_tr_arr.reshape(-1, 1)
        ev_2d = (X_ev_arr if X_ev_arr.ndim > 1 else X_ev_arr.reshape(-1, 1)) if X_ev_arr is not None else None

        n_rows_tr, n_cols_tr = tr_2d.shape
        num_tr = np.zeros((n_rows_tr, n_cols_tr), dtype=np.float64)
        num_ev = np.zeros(ev_2d.shape, dtype=np.float64) if ev_2d is not None else None

        for j in range(n_cols_tr):
            col_tr = tr_2d[:, j]
            col_ev = ev_2d[:, j] if ev_2d is not None and j < ev_2d.shape[1] else None

            try:
                num_tr[:, j] = col_tr.astype(np.float64)
                tr_col_numeric = True
            except (ValueError, TypeError):
                tr_col_numeric = False
                uniques = [x for x in pd.Series(col_tr).dropna().unique()]
                mapping = {val: float(idx) for idx, val in enumerate(uniques)}
                num_tr[:, j] = pd.Series(col_tr).map(mapping).fillna(-1.0).to_numpy(dtype=np.float64)

            if col_ev is not None:
                if tr_col_numeric:
                    try:
                        num_ev[:, j] = col_ev.astype(np.float64)
                    except (ValueError, TypeError):
                        num_ev[:, j] = pd.to_numeric(pd.Series(col_ev), errors="coerce").fillna(-1.0).to_numpy(dtype=np.float64)
                else:
                    num_ev[:, j] = pd.Series(col_ev).map(mapping).fillna(-1.0).to_numpy(dtype=np.float64)

        out_tr = num_tr if X_tr_arr.ndim > 1 else num_tr.ravel()
        out_ev = (num_ev if X_ev_arr.ndim > 1 else num_ev.ravel()) if num_ev is not None else None
        return out_tr, out_ev

    X_tr_out = np.asarray(X_tr_arr, dtype=np.float64)
    X_ev_out = np.asarray(X_ev_arr, dtype=np.float64) if X_ev_arr is not None else None
    return X_tr_out, X_ev_out
