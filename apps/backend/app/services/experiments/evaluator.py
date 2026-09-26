"""
Experiment Evaluation & Threshold Optimization Module.
Handles CV aggregation, classification/regression metrics, and threshold tuning.
"""

from typing import Any
import numpy as np
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


class ExperimentEvaluator:
    """Computes evaluation metrics and performs threshold optimization."""

    @staticmethod
    def compute_classification_metrics(y_true: np.ndarray, y_pred: np.ndarray, y_prob: np.ndarray | None = None) -> dict[str, float]:
        metrics = {
            "accuracy": float(accuracy_score(y_true, y_pred)),
            "precision": float(precision_score(y_true, y_pred, zero_division=0)),
            "recall": float(recall_score(y_true, y_pred, zero_division=0)),
            "f1": float(f1_score(y_true, y_pred, zero_division=0)),
        }
        if y_prob is not None:
            try:
                metrics["roc_auc"] = float(roc_auc_score(y_true, y_prob))
            except Exception:
                metrics["roc_auc"] = 0.5
        return metrics

    @staticmethod
    def compute_regression_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> dict[str, float]:
        mse = float(mean_squared_error(y_true, y_pred))
        return {
            "mse": mse,
            "rmse": float(np.sqrt(mse)),
            "mae": float(mean_absolute_error(y_true, y_pred)),
            "r2": float(r2_score(y_true, y_pred)),
        }

    @staticmethod
    def optimize_decision_threshold(y_true: np.ndarray, y_probs: np.ndarray, metric: str = "f1") -> tuple[float, float]:
        """Scans candidate thresholds [0.1, 0.9] to maximize target metric."""
        best_threshold = 0.5
        best_score = -1.0
        for t in np.linspace(0.1, 0.9, 81):
            y_pred = (y_probs >= t).astype(int)
            if metric == "f1":
                score = f1_score(y_true, y_pred, zero_division=0)
            elif metric == "accuracy":
                score = accuracy_score(y_true, y_pred)
            elif metric == "recall":
                score = recall_score(y_true, y_pred, zero_division=0)
            elif metric == "precision":
                score = precision_score(y_true, y_pred, zero_division=0)
            else:
                score = f1_score(y_true, y_pred, zero_division=0)

            if score > best_score:
                best_score = float(score)
                best_threshold = float(t)

        return best_threshold, best_score
