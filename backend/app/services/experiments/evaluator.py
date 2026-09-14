"""
Experiment Metrics & Evaluation Module.

Computes multi-metric evaluations, generalization gaps, and composite rankings across models.
"""

import numpy as np
from typing import Any
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    roc_auc_score,
    mean_squared_error,
    mean_absolute_error,
    r2_score,
)


def evaluate_classification_metrics(
    y_true: np.ndarray | list,
    y_pred: np.ndarray | list,
    y_proba: np.ndarray | list | None = None,
) -> dict[str, float]:
    """Computes comprehensive classification metrics."""
    y_t = np.asarray(y_true)
    y_p = np.asarray(y_pred)

    acc = float(accuracy_score(y_t, y_p))
    prec = float(precision_score(y_t, y_p, average="macro", zero_division=0))
    rec = float(recall_score(y_t, y_p, average="macro", zero_division=0))
    f1 = float(f1_score(y_t, y_p, average="macro", zero_division=0))

    metrics = {
        "Accuracy": acc,
        "Precision": prec,
        "Recall": rec,
        "F1": f1,
        "F1_Macro": f1,
    }

    if y_proba is not None:
        try:
            if len(np.unique(y_t)) == 2:
                proba_pos = y_proba[:, 1] if len(y_proba.shape) > 1 else y_proba
                metrics["ROC_AUC"] = float(roc_auc_score(y_t, proba_pos))
            else:
                metrics["ROC_AUC"] = float(roc_auc_score(y_t, y_proba, multi_class="ovr"))
        except Exception:
            pass

    return metrics


def evaluate_regression_metrics(
    y_true: np.ndarray | list,
    y_pred: np.ndarray | list,
) -> dict[str, float]:
    """Computes comprehensive regression metrics."""
    y_t = np.asarray(y_true)
    y_p = np.asarray(y_pred)

    mse = float(mean_squared_error(y_t, y_p))
    rmse = float(np.sqrt(mse))
    mae = float(mean_absolute_error(y_t, y_p))
    r2 = float(r2_score(y_t, y_p))

    return {
        "MSE": mse,
        "RMSE": rmse,
        "MAE": mae,
        "R2": r2,
    }
