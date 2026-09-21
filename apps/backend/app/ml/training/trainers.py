"""
Canonical ML Training Engines (Classification & Regression).
Algorithms supported:
- Linear Regression / Logistic Regression
- Random Forest Regressor / Random Forest Classifier
- Gradient Boosting Regressor / Gradient Boosting Classifier
"""

from typing import Any
from sklearn.linear_model import LinearRegression, LogisticRegression
from sklearn.ensemble import (
    RandomForestRegressor,
    RandomForestClassifier,
    GradientBoostingRegressor,
    GradientBoostingClassifier,
)

CANONICAL_ALGORITHMS = {
    "REGRESSION": {
        "LinearRegression": LinearRegression,
        "RandomForestRegressor": RandomForestRegressor,
        "GradientBoostingRegressor": GradientBoostingRegressor,
    },
    "CLASSIFICATION": {
        "LogisticRegression": LogisticRegression,
        "RandomForestClassifier": RandomForestClassifier,
        "GradientBoostingClassifier": GradientBoostingClassifier,
    },
}


def get_estimator(algorithm_name: str, task_type: str, hyperparams: dict[str, Any] | None = None) -> Any:
    """Instantiate a configured scikit-learn estimator."""
    task_catalog = CANONICAL_ALGORITHMS.get(task_type.upper())
    if not task_catalog or algorithm_name not in task_catalog:
        raise ValueError(f"Algorithm '{algorithm_name}' not supported for task '{task_type}'.")

    cls = task_catalog[algorithm_name]
    params = hyperparams.copy() if hyperparams else {}
    if "random_state" in cls().get_params() and "random_state" not in params:
        params["random_state"] = 42
    return cls(**params)
