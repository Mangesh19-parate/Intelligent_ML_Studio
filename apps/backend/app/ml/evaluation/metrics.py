"""
Multi-Metric Evaluation Suite for Classification & Regression.
"""

import numpy as np
import pandas as pd
from sklearn.metrics import (
    mean_absolute_error,
    mean_squared_error,
    r2_score,
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    roc_auc_score,
    log_loss,
    confusion_matrix,
)


def evaluate_regression(
    y_true: np.ndarray | list[float] | pd.Series,
    y_pred: np.ndarray | list[float] | pd.Series,
    n: int,
    p: int,
) -> dict[str, float]:
    """Computes complete regression metrics."""
    y_true_arr = np.asarray(y_true, dtype=np.float64)
    y_pred_arr = np.asarray(y_pred, dtype=np.float64)

    mae = float(mean_absolute_error(y_true_arr, y_pred_arr))
    mse = float(mean_squared_error(y_true_arr, y_pred_arr))
    rmse = float(np.sqrt(mse))
    r2 = float(r2_score(y_true_arr, y_pred_arr))

    if n > p + 1 and (1 - r2) >= 0:
        adj_r2 = float(1 - (1 - r2) * (n - 1) / (n - p - 1))
    else:
        adj_r2 = r2

    return {
        "MAE": round(mae, 4),
        "MSE": round(mse, 4),
        "RMSE": round(rmse, 4),
        "R2": round(r2, 4),
        "ADJUSTED_R2": round(adj_r2, 4),
    }


def evaluate_classification(
    y_true: np.ndarray | list[int] | pd.Series,
    y_pred: np.ndarray | list[int] | pd.Series,
    y_prob: np.ndarray | None = None,
) -> dict[str, float]:
    """Computes complete classification metrics."""
    y_true_arr = np.asarray(y_true, dtype=int)
    y_pred_arr = np.asarray(y_pred, dtype=int)

    acc = float(accuracy_score(y_true_arr, y_pred_arr))
    prec = float(precision_score(y_true_arr, y_pred_arr, zero_division=0, average="weighted"))
    rec = float(recall_score(y_true_arr, y_pred_arr, zero_division=0, average="weighted"))
    f1 = float(f1_score(y_true_arr, y_pred_arr, zero_division=0, average="weighted"))

    metrics = {
        "ACCURACY": round(acc, 4),
        "PRECISION": round(prec, 4),
        "RECALL": round(rec, 4),
        "F1": round(f1, 4),
    }

    if y_prob is not None:
        try:
            if y_prob.ndim == 1 or y_prob.shape[1] == 2:
                prob_col = y_prob[:, 1] if y_prob.ndim == 2 else y_prob
                metrics["ROC_AUC"] = round(float(roc_auc_score(y_true_arr, prob_col)), 4)
            metrics["LOG_LOSS"] = round(float(log_loss(y_true_arr, y_prob)), 4)
        except Exception:
            pass

    return metrics
