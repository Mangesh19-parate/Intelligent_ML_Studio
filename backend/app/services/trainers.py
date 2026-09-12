from abc import ABC, abstractmethod
from typing import Any
import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin, clone
from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer
from sklearn.linear_model import LinearRegression, LogisticRegression
from sklearn.ensemble import (
    RandomForestRegressor,
    RandomForestClassifier,
    GradientBoostingRegressor,
    GradientBoostingClassifier,
)

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
            self.n_features_in_ = X.shape[1]
            if self.selected_features is not None:
                self.selected_indices_ = [
                    i for i, col in enumerate(X.columns) if col in self.selected_features
                ]
            else:
                self.selected_indices_ = list(range(X.shape[1]))
        else:
            n_cols = np.asarray(X).shape[1] if len(np.asarray(X).shape) > 1 else 1
            self.n_features_in_ = n_cols
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
    Abstract Base Class for Model Trainers (SRS v9 §2.8 & Architecture Contract §2).
    
    ARCHITECTURAL INVARIANTS:
    1. Template Pipeline: `get_pipeline()` constructs and returns ONE fresh, UNFIT scikit-learn Pipeline
       combining Day 4's transformer step, Day 5's selector step, and the estimator.
    2. Never Return Pre-Fit Object: Pipeline instances are fresh per call.
    3. Canonical Algorithm Names: Adheres strictly to canonical identifiers. Prohibits bare abbreviations like 'RF'.
    4. Scikit-learn Defaults: No hidden hyperparameter tuning.
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

    @property
    @abstractmethod
    def task_type(self) -> str:
        """Returns the task type: 'REGRESSION' or 'CLASSIFICATION'."""
        pass

    @property
    @abstractmethod
    def canonical_name(self) -> str:
        """Returns the resolved canonical algorithm identifier."""
        pass

    @abstractmethod
    def _build_estimator(self) -> Any:
        """Instantiates the scikit-learn estimator with defaults or configured hyperparameters."""
        pass

    def get_pipeline(
        self,
        transformer: TransformerMixin | None = None,
        selector: TransformerMixin | None = None,
    ) -> Pipeline:
        """Returns a fresh, unfit scikit-learn Pipeline combining transformer, selector, and estimator."""
        t_step = transformer if transformer is not None else ColumnTransformer(transformers=[], remainder="passthrough")
        s_step = selector if selector is not None else FeatureSelector()
        est = clone(self.estimator) if hasattr(self.estimator, "fit") else self._build_estimator()
        return Pipeline([
            ("transformer", t_step),
            ("selector", s_step),
            ("estimator", est),
        ])

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
    Regression Model Trainer (SRS v9 §2.8 & Architecture Contract §2).
    
    Canonical Algorithms:
    - LinearRegression (`linear_regression`): Ordinary Least Squares baseline
    - Ridge (`ridge_regression`): L2-regularized linear regression
    - RandomForestRegressor (`random_forest_regressor`): Ensemble bagging regressor
    - GradientBoostingRegressor (`gradient_boosting_regressor`): Stage-wise additive boosting regressor
    """
    CANONICAL_NAMES = {
        "linearregression": "LinearRegression",
        "linear regression": "LinearRegression",
        "linear_regression": "LinearRegression",
        "LinearRegression": "LinearRegression",
        "Linear Regression": "LinearRegression",
        "randomforestregressor": "RandomForestRegressor",
        "random forest regressor": "RandomForestRegressor",
        "random_forest_regressor": "RandomForestRegressor",
        "random forest": "RandomForestRegressor",
        "RandomForestRegressor": "RandomForestRegressor",
        "Random Forest Regressor": "RandomForestRegressor",
        "Random Forest": "RandomForestRegressor",
        "gradientboostingregressor": "GradientBoostingRegressor",
        "gradient boosting regressor": "GradientBoostingRegressor",
        "gradient_boosting_regressor": "GradientBoostingRegressor",
        "gradient boosting": "GradientBoostingRegressor",
        "GradientBoostingRegressor": "GradientBoostingRegressor",
        "Gradient Boosting Regressor": "GradientBoostingRegressor",
        "Gradient Boosting": "GradientBoostingRegressor",
    }

    SUPPORTED_ALGORITHMS = {
        "LinearRegression": LinearRegression,
        "RandomForestRegressor": RandomForestRegressor,
        "GradientBoostingRegressor": GradientBoostingRegressor,
    }

    @classmethod
    def is_supported(cls, name: str) -> bool:
        if not name or not isinstance(name, str):
            return False
        cleaned = name.strip().lower()
        if cleaned in ["rf", "rf_regressor", "rf_regression", "rf_classifier", "rf_classification"]:
            return False
        return cleaned in cls.CANONICAL_NAMES

    @classmethod
    def to_canonical_name(cls, name: str) -> str:
        if not name or not isinstance(name, str):
            raise ValueError("Algorithm name must be a non-empty string.")
        cleaned = name.strip().lower()
        if cleaned in ["rf", "rf_regressor", "rf_regression", "rf_classifier", "rf_classification"] or cleaned == "rf":
            raise ValueError(
                f"Unsupported algorithm '{name}'. Prohibited bare abbreviation: "
                f"use 'RandomForestRegressor' for regression or 'RandomForestClassifier' for classification."
            )
        if cleaned not in cls.CANONICAL_NAMES:
            valid_list = sorted(list(set(cls.SUPPORTED_ALGORITHMS.keys())))
            raise ValueError(
                f"Unsupported regression algorithm: '{name}'. "
                f"Valid canonical algorithms: {valid_list}"
            )
        return cls.CANONICAL_NAMES[cleaned]

    @classmethod
    def get_supported_algorithms(cls) -> list[str]:
        return sorted(list(cls.SUPPORTED_ALGORITHMS.keys()))

    @property
    def task_type(self) -> str:
        return "REGRESSION"

    @property
    def canonical_name(self) -> str:
        return self.to_canonical_name(self.algorithm_name)

    def _build_estimator(self) -> Any:
        canon_name = self.canonical_name
        cls = self.SUPPORTED_ALGORITHMS[canon_name]
        params = dict(self.hyperparameters)

        if canon_name == "RandomForestRegressor":
            if "random_state" not in params and self.random_state is not None:
                params["random_state"] = self.random_state
            if "n_estimators" not in params:
                params["n_estimators"] = 100
        elif canon_name == "GradientBoostingRegressor":
            if "random_state" not in params and self.random_state is not None:
                params["random_state"] = self.random_state
            if "n_estimators" not in params:
                params["n_estimators"] = 100

        return cls(**params)


class ClassificationTrainer(BaseModelTrainer):
    """
    Classification Model Trainer (SRS v9 §2.8 & Architecture Contract §2).
    
    Canonical Algorithms:
    - LogisticRegression (`logistic_regression`): Regularized linear classification baseline
    - RandomForestClassifier (`random_forest_classifier`): Ensemble bagging classifier
    - GradientBoostingClassifier (`gradient_boosting_classifier`): Stage-wise additive boosting classifier
    """
    CANONICAL_NAMES = {
        "logisticregression": "LogisticRegression",
        "logistic regression": "LogisticRegression",
        "logistic_regression": "LogisticRegression",
        "LogisticRegression": "LogisticRegression",
        "Logistic Regression": "LogisticRegression",
        "randomforestclassifier": "RandomForestClassifier",
        "random forest classifier": "RandomForestClassifier",
        "random_forest_classifier": "RandomForestClassifier",
        "random forest": "RandomForestClassifier",
        "RandomForestClassifier": "RandomForestClassifier",
        "Random Forest Classifier": "RandomForestClassifier",
        "Random Forest": "RandomForestClassifier",
        "gradientboostingclassifier": "GradientBoostingClassifier",
        "gradient boosting classifier": "GradientBoostingClassifier",
        "gradient_boosting_classifier": "GradientBoostingClassifier",
        "gradient boosting": "GradientBoostingClassifier",
        "GradientBoostingClassifier": "GradientBoostingClassifier",
        "Gradient Boosting Classifier": "GradientBoostingClassifier",
        "Gradient Boosting": "GradientBoostingClassifier",
    }

    SUPPORTED_ALGORITHMS = {
        "LogisticRegression": LogisticRegression,
        "RandomForestClassifier": RandomForestClassifier,
        "GradientBoostingClassifier": GradientBoostingClassifier,
    }

    @classmethod
    def is_supported(cls, name: str) -> bool:
        if not name or not isinstance(name, str):
            return False
        cleaned = name.strip().lower()
        if cleaned in ["rf", "rf_classifier", "rf_classification", "rf_regressor", "rf_regression"]:
            return False
        return cleaned in cls.CANONICAL_NAMES

    @classmethod
    def to_canonical_name(cls, name: str) -> str:
        if not name or not isinstance(name, str):
            raise ValueError("Algorithm name must be a non-empty string.")
        cleaned = name.strip().lower()
        if cleaned in ["rf", "rf_classifier", "rf_classification", "rf_regressor", "rf_regression"] or cleaned == "rf":
            raise ValueError(
                f"Unsupported algorithm '{name}'. Prohibited bare abbreviation: "
                f"use 'RandomForestClassifier' for classification or 'RandomForestRegressor' for regression."
            )
        if cleaned not in cls.CANONICAL_NAMES:
            valid_list = sorted(list(set(cls.SUPPORTED_ALGORITHMS.keys())))
            raise ValueError(
                f"Unsupported classification algorithm: '{name}'. "
                f"Valid canonical algorithms: {valid_list}"
            )
        return cls.CANONICAL_NAMES[cleaned]

    @classmethod
    def get_supported_algorithms(cls) -> list[str]:
        return sorted(list(cls.SUPPORTED_ALGORITHMS.keys()))

    @property
    def task_type(self) -> str:
        return "CLASSIFICATION"

    @property
    def canonical_name(self) -> str:
        return self.to_canonical_name(self.algorithm_name)

    def _build_estimator(self) -> Any:
        canon_name = self.canonical_name
        cls = self.SUPPORTED_ALGORITHMS[canon_name]
        params = dict(self.hyperparameters)

        if canon_name == "LogisticRegression":
            if "max_iter" not in params:
                params["max_iter"] = 1000
            if "random_state" not in params and self.random_state is not None:
                params["random_state"] = self.random_state
        elif canon_name == "RandomForestClassifier":
            if "random_state" not in params and self.random_state is not None:
                params["random_state"] = self.random_state
            if "n_estimators" not in params:
                params["n_estimators"] = 100
        elif canon_name == "GradientBoostingClassifier":
            if "random_state" not in params and self.random_state is not None:
                params["random_state"] = self.random_state
            if "n_estimators" not in params:
                params["n_estimators"] = 100

        return cls(**params)

