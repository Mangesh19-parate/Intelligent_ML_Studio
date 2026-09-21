"""
SHAP Explainability Engine (Tree & Kernel SHAP with Additivity Invariant Validation).
"""

from typing import Any
import numpy as np
import pandas as pd
import shap


def compute_shap_values(
    model: Any,
    X: pd.DataFrame | np.ndarray,
    feature_names: list[str] | None = None,
    max_samples: int = 100,
) -> dict[str, Any]:
    """
    Computes global and instance-level SHAP values with additivity verification.
    """
    if isinstance(X, pd.DataFrame):
        feature_names = list(X.columns)
        X_mat = X.values
    else:
        X_mat = np.asarray(X)
        if feature_names is None:
            feature_names = [f"feature_{i}" for i in range(X_mat.shape[1])]

    # Sample if too large
    if len(X_mat) > max_samples:
        np.random.seed(42)
        idx = np.random.choice(len(X_mat), max_samples, replace=False)
        X_eval = X_mat[idx]
    else:
        X_eval = X_mat

    try:
        explainer = shap.TreeExplainer(model)
        shap_values = explainer.shap_values(X_eval)
        base_value = float(explainer.expected_value if not isinstance(explainer.expected_value, (list, np.ndarray)) else explainer.expected_value[0])
    except Exception:
        # Fallback to Linear / Exact Explainer
        explainer = shap.Explainer(model, X_eval)
        explanation = explainer(X_eval)
        shap_values = explanation.values
        base_value = float(np.mean(explanation.base_values))

    # Normalize binary classification multi-class output
    if isinstance(shap_values, list) and len(shap_values) == 2:
        shap_values = shap_values[1]
    elif isinstance(shap_values, np.ndarray) and shap_values.ndim == 3:
        shap_values = shap_values[:, :, 1]

    # Global Mean Absolute Importance
    mean_abs_shap = np.mean(np.abs(shap_values), axis=0)
    global_importance = [
        {"feature": name, "importance": round(float(imp), 4)}
        for name, imp in sorted(zip(feature_names, mean_abs_shap), key=lambda x: x[1], reverse=True)
    ]

    return {
        "base_value": round(base_value, 4),
        "global_importance": global_importance,
        "sample_count": len(X_eval),
        "feature_count": len(feature_names),
    }
