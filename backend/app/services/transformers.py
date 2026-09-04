import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.utils.validation import check_is_fitted

class OutlierCapper(BaseEstimator, TransformerMixin):
    """
    Leakage-safe outlier handler that computes capping thresholds during `fit()`
    and applies clipping during `transform()`.
    
    Supported strategies:
    - 'none': Passthrough
    - 'zscore': Capping at mean +/- (z_threshold * std)
    - 'iqr': Capping at Q1 - 1.5*IQR and Q3 + 1.5*IQR
    - 'percentile': Capping at 1st and 99th percentiles
    - 'winsorize': Capping at 5th and 95th percentiles
    
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
        if self.strategy == "none" or not self.strategy:
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
            # Ignore NaNs during threshold calculation
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
            elif self.strategy == "iqr":
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
