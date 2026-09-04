from abc import ABC, abstractmethod
from typing import Any
import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer
from sklearn.linear_model import LinearRegression, Ridge, LogisticRegression
from sklearn.ensemble import RandomForestRegressor, RandomForestClassifier, GradientBoostingClassifier

class FeatureSelector(BaseEstimator, TransformerMixin):
    """
    Unfit / fit FeatureSelector transformer step that subsets columns based on selected feature names or indices.
    
    ARCHITECTURAL INVARIANT:
    - Unfit state holds no learned partitions or data distributions.
    - Operates seamlessly on pandas DataFrames and 2D NumPy arrays.
    """
    def __init__(self, selected_features: list[str] | list[int] | None = None):
        self.selected_features = selected_features
        self.selected_indices_ = None
        self.feature_names_in_ = None

    def fit(self, X, y=None):
        if isinstance(X, pd.DataFrame):
            self.feature_names_in_ = list(X.columns)
            if self.selected_features is not None:
                self.selected_indices_ = [
                    i for i, col in enumerate(X.columns) if col in self.selected_features
                ]
            else:
                self.selected_indices_ = list(range(X.shape[1]))
        else:
            n_cols = np.asarray(X).shape[1] if len(np.asarray(X).shape) > 1 else 1
            if self.selected_features is not None and len(self.selected_features) > 0 and isinstance(self.selected_features[0], int):
                self.selected_indices_ = self.selected_features
            else:
                self.selected_indices_ = list(range(n_cols))
        return self

    def transform(self, X):
        if isinstance(X, pd.DataFrame):
            if self.selected_features is not None:
                valid_cols = [c for c in self.selected_features if c in X.columns]
                return X[valid_cols] if valid_cols else X
            return X
        X_arr = np.asarray(X)
        if hasattr(self, "selected_indices_") and self.selected_indices_ is not None and len(self.selected_indices_) > 0:
            return X_arr[:, self.selected_indices_]
        return X_arr

    def get_feature_names_out(self, input_features=None):
        if self.selected_features is not None:
            return np.asarray(self.selected_features, dtype=str)
        if input_features is not None:
            return np.asarray(input_features, dtype=str)
        return np.array([])


class BaseModelTrainer(ABC):
    """
    Abstract Base Class for Model Trainers (SRS §2.8).
    
    ARCHITECTURAL INVARIANTS:
    1. Template Pipeline: `get_pipeline()` constructs and returns ONE fresh, UNFIT scikit-learn Pipeline
       combining Day 4's transformer step, Day 5's selector step, and the estimator.
    2. Never Return Pre-Fit Object: Pipeline instances are fresh per call.
    3. Scikit-learn Defaults: No hidden hyperparameter tuning today.
    """
    def __init__(
        self,
        algorithm_name: str,
        hyperparameters: dict[str, Any] | None = None,
        random_state: int | None = None,
    ):
        self.algorithm_name = algorithm_name
        self.hyperparameters = hyperparameters or {}
        self.random_state = random_state
        self.estimator = self._build_estimator()

    @abstractmethod
    def _build_estimator(self) -> Any:
        """Instantiates the scikit-learn estimator with defaults or configured hyperparameters."""
        pass

    @abstractmethod
    def get_pipeline(
        self,
        transformer: TransformerMixin | None = None,
        selector: TransformerMixin | None = None,
    ) -> Pipeline:
        """Returns a fresh, unfit scikit-learn Pipeline combining transformer, selector, and estimator."""
        pass

    def fit(self, X: Any, y: Any) -> "BaseModelTrainer":
        """Fits the underlying estimator."""
        self.estimator.fit(X, y)
        return self

    def predict(self, X: Any) -> np.ndarray:
        """Predicts using the fitted estimator."""
        return self.estimator.predict(X)

    def predict_proba(self, X: Any) -> np.ndarray | None:
        """Predicts class probabilities if supported by the estimator."""
        if hasattr(self.estimator, "predict_proba"):
            try:
                return self.estimator.predict_proba(X)
            except Exception:
                return None
        return None

    def get_estimator(self) -> Any:
        """Returns the underlying estimator instance."""
        return self.estimator



class RegressionTrainer(BaseModelTrainer):
    """
    Regression Model Trainer (SRS §2.8).
    
    Supported Algorithm Set (fixed 3 for Day 6):
    - LinearRegression (base/default)
    - Ridge
    - RandomForestRegressor
    """
    SUPPORTED_ALGORITHMS = {
        "LinearRegression": LinearRegression,
        "Linear Regression": LinearRegression,
        "Ridge": Ridge,
        "Ridge Regression": Ridge,
        "RandomForestRegressor": RandomForestRegressor,
        "Random Forest": RandomForestRegressor,
        "Random Forest Regressor": RandomForestRegressor,
    }

    CANONICAL_NAMES = {
        "LinearRegression": "LinearRegression",
        "Linear Regression": "LinearRegression",
        "Ridge": "Ridge",
        "Ridge Regression": "Ridge",
        "RandomForestRegressor": "RandomForestRegressor",
        "Random Forest": "RandomForestRegressor",
        "Random Forest Regressor": "RandomForestRegressor",
    }

    def _build_estimator(self) -> Any:
        name = self.algorithm_name
        if name not in self.SUPPORTED_ALGORITHMS:
            raise ValueError(
                f"Unsupported regression algorithm: '{name}'. "
                f"Valid algorithms: LinearRegression, Ridge, RandomForestRegressor"
            )

        cls = self.SUPPORTED_ALGORITHMS[name]
        params = dict(self.hyperparameters)

        if name in ["Ridge", "Ridge Regression"]:
            if "random_state" not in params and self.random_state is not None:
                params["random_state"] = self.random_state
        elif name in ["RandomForestRegressor", "Random Forest", "Random Forest Regressor"]:
            if "random_state" not in params and self.random_state is not None:
                params["random_state"] = self.random_state
            if "n_estimators" not in params:
                params["n_estimators"] = 100

        return cls(**params)

    def get_pipeline(
        self,
        transformer: TransformerMixin | None = None,
        selector: TransformerMixin | None = None,
    ) -> Pipeline:
        t_step = transformer if transformer is not None else ColumnTransformer(transformers=[], remainder="passthrough")
        s_step = selector if selector is not None else FeatureSelector()
        est = self._build_estimator()
        return Pipeline([
            ("transformer", t_step),
            ("selector", s_step),
            ("estimator", est),
        ])


class ClassificationTrainer(BaseModelTrainer):
    """
    Classification Model Trainer (SRS §2.8).
    
    Supported Algorithm Set (fixed 3 for Day 6):
    - LogisticRegression (base/default)
    - RandomForestClassifier
    - GradientBoostingClassifier
    """
    SUPPORTED_ALGORITHMS = {
        "LogisticRegression": LogisticRegression,
        "Logistic Regression": LogisticRegression,
        "RandomForestClassifier": RandomForestClassifier,
        "Random Forest": RandomForestClassifier,
        "Random Forest Classifier": RandomForestClassifier,
        "GradientBoostingClassifier": GradientBoostingClassifier,
        "Gradient Boosting": GradientBoostingClassifier,
        "Gradient Boosting Classifier": GradientBoostingClassifier,
    }

    CANONICAL_NAMES = {
        "LogisticRegression": "LogisticRegression",
        "Logistic Regression": "LogisticRegression",
        "RandomForestClassifier": "RandomForestClassifier",
        "Random Forest": "RandomForestClassifier",
        "Random Forest Classifier": "RandomForestClassifier",
        "GradientBoostingClassifier": "GradientBoostingClassifier",
        "Gradient Boosting": "GradientBoostingClassifier",
        "Gradient Boosting Classifier": "GradientBoostingClassifier",
    }

    def _build_estimator(self) -> Any:
        name = self.algorithm_name
        if name not in self.SUPPORTED_ALGORITHMS:
            raise ValueError(
                f"Unsupported classification algorithm: '{name}'. "
                f"Valid algorithms: LogisticRegression, RandomForestClassifier, GradientBoostingClassifier"
            )

        cls = self.SUPPORTED_ALGORITHMS[name]
        params = dict(self.hyperparameters)

        if name in ["LogisticRegression", "Logistic Regression"]:
            if "max_iter" not in params:
                params["max_iter"] = 1000
            if "random_state" not in params and self.random_state is not None:
                params["random_state"] = self.random_state
        elif name in ["RandomForestClassifier", "Random Forest", "Random Forest Classifier"]:
            if "random_state" not in params and self.random_state is not None:
                params["random_state"] = self.random_state
            if "n_estimators" not in params:
                params["n_estimators"] = 100
        elif name in ["GradientBoostingClassifier", "Gradient Boosting", "Gradient Boosting Classifier"]:
            if "random_state" not in params and self.random_state is not None:
                params["random_state"] = self.random_state
            if "n_estimators" not in params:
                params["n_estimators"] = 100

        return cls(**params)

    def get_pipeline(
        self,
        transformer: TransformerMixin | None = None,
        selector: TransformerMixin | None = None,
    ) -> Pipeline:
        t_step = transformer if transformer is not None else ColumnTransformer(transformers=[], remainder="passthrough")
        s_step = selector if selector is not None else FeatureSelector()
        est = self._build_estimator()
        return Pipeline([
            ("transformer", t_step),
            ("selector", s_step),
            ("estimator", est),
        ])
