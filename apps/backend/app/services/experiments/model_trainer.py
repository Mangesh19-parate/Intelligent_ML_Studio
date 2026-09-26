"""
Model Trainer Orchestrator Module.
Coordinates isolated algorithm training, cross-validation execution, and artifact serialization.
"""

from typing import Any
import numpy as np
from sklearn.linear_model import LogisticRegression, LinearRegression, Ridge
from sklearn.ensemble import (
    RandomForestClassifier,
    RandomForestRegressor,
    GradientBoostingClassifier,
    GradientBoostingRegressor,
)


class ModelTrainer:
    """Instantiates and fits canonical algorithms with reproducibility guarantees."""

    ALGORITHM_MAP = {
        "LogisticRegression": lambda seed: LogisticRegression(random_state=seed, max_iter=1000),
        "LinearRegression": lambda seed: LinearRegression(),
        "Ridge": lambda seed: Ridge(random_state=seed),
        "RandomForestClassifier": lambda seed: RandomForestClassifier(n_estimators=100, random_state=seed),
        "RandomForestRegressor": lambda seed: RandomForestRegressor(n_estimators=100, random_state=seed),
        "GradientBoostingClassifier": lambda seed: GradientBoostingClassifier(n_estimators=100, random_state=seed),
        "GradientBoostingRegressor": lambda seed: GradientBoostingRegressor(n_estimators=100, random_state=seed),
    }

    @classmethod
    def get_model_instance(cls, algorithm_name: str, random_seed: int = 42) -> Any:
        factory = cls.ALGORITHM_MAP.get(algorithm_name)
        if not factory:
            raise ValueError(f"Unsupported algorithm: {algorithm_name}")
        return factory(random_seed)

    @classmethod
    def fit_model(cls, algorithm_name: str, X: np.ndarray, y: np.ndarray, random_seed: int = 42) -> Any:
        model = cls.get_model_instance(algorithm_name, random_seed)
        model.fit(X, y)
        return model
