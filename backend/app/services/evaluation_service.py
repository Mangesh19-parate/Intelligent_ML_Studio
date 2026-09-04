import logging
from typing import Any
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
    confusion_matrix,
)

logger = logging.getLogger(__name__)

class EvaluationService:
    """
    Evaluation & Fit Diagnostics Service (SRS §2.9, §2.10).
    
    Responsibilities:
    - Compute full multi-metric evaluation suites for Regression and Classification.
    - Compute naive baselines (mean predictor for regression, majority-class for classification).
    - Perform metric-direction-aware fit diagnostics (GOOD_FIT, POTENTIAL_OVERFIT, POTENTIAL_UNDERFIT_WEAK_SIGNAL, INSUFFICIENT_DATA).
    - Compute composite model_selection_score (secondary convenience indicator, not used for ranking).
    """

    HIGHER_IS_BETTER_METRICS = {
        "r2", "adjusted_r2", "accuracy", "f1", "f1_macro", "f1_weighted",
        "precision", "recall", "roc_auc"
    }

    LOWER_IS_BETTER_METRICS = {
        "mae", "mse", "rmse", "log_loss"
    }

    DEFAULT_OVERFIT_THRESHOLDS = {
        "r2": 0.15,
        "adjusted_r2": 0.15,
        "accuracy": 0.10,
        "f1_macro": 0.10,
        "f1_weighted": 0.10,
        "precision": 0.10,
        "recall": 0.10,
        "roc_auc": 0.10,
        "rmse": 0.15,
        "mae": 0.15,
        "mse": 0.20,
    }

    @staticmethod
    def evaluate_regression(
        y_true: np.ndarray | list[float] | pd.Series,
        y_pred: np.ndarray | list[float] | pd.Series,
        n: int,
        p: int,
    ) -> dict[str, float]:
        """
        Computes the complete regression metric suite:
        - MAE, MSE, RMSE, R2, Adjusted R2 (using n = fold sample size, p = selected features count).
        """
        y_true_arr = np.asarray(y_true, dtype=np.float64)
        y_pred_arr = np.asarray(y_pred, dtype=np.float64)

        mae = float(mean_absolute_error(y_true_arr, y_pred_arr))
        mse = float(mean_squared_error(y_true_arr, y_pred_arr))
        rmse = float(np.sqrt(mse))
        r2 = float(r2_score(y_true_arr, y_pred_arr))
        if np.isnan(r2):
            r2 = 0.0

        # Adjusted R2 formula: 1 - ((1 - R2) * (n - 1)) / (n - p - 1)
        if n > p + 1 and (n - p - 1) > 0:
            adj_r2 = float(1.0 - ((1.0 - r2) * (n - 1)) / (n - p - 1))
        else:
            adj_r2 = r2

        return {
            "mae": round(mae, 5),
            "mse": round(mse, 5),
            "rmse": round(rmse, 5),
            "r2": round(r2, 5),
            "adjusted_r2": round(adj_r2, 5),
        }

    @staticmethod
    def evaluate_classification(
        y_true: np.ndarray | list[Any] | pd.Series,
        y_pred: np.ndarray | list[Any] | pd.Series,
        y_proba: np.ndarray | None = None,
    ) -> dict[str, Any]:
        """
        Computes the complete classification metric suite:
        - Accuracy, Precision (weighted), Recall (weighted), F1 (weighted + macro),
          ROC-AUC (one-vs-rest / binary if proba available), Confusion Matrix (as JSON structure).
        """
        y_true_arr = np.asarray(y_true)
        y_pred_arr = np.asarray(y_pred)

        acc = float(accuracy_score(y_true_arr, y_pred_arr))
        prec = float(precision_score(y_true_arr, y_pred_arr, average="weighted", zero_division=0))
        rec = float(recall_score(y_true_arr, y_pred_arr, average="weighted", zero_division=0))
        f1_w = float(f1_score(y_true_arr, y_pred_arr, average="weighted", zero_division=0))
        f1_m = float(f1_score(y_true_arr, y_pred_arr, average="macro", zero_division=0))

        # Confusion Matrix
        cm = confusion_matrix(y_true_arr, y_pred_arr).tolist()

        # ROC-AUC (optional depending on proba availability and class support)
        roc_auc = None
        if y_proba is not None:
            try:
                unique_classes = np.unique(y_true_arr)
                if len(unique_classes) == 2:
                    if y_proba.ndim == 2 and y_proba.shape[1] >= 2:
                        roc_auc = float(roc_auc_score(y_true_arr, y_proba[:, 1]))
                    elif y_proba.ndim == 1:
                        roc_auc = float(roc_auc_score(y_true_arr, y_proba))
                elif len(unique_classes) > 2:
                    if y_proba.ndim == 2 and y_proba.shape[1] == len(unique_classes):
                        roc_auc = float(
                            roc_auc_score(
                                y_true_arr,
                                y_proba,
                                multi_class="ovr",
                                average="macro"
                            )
                        )
            except Exception as e:
                logger.debug(f"ROC-AUC computation skipped: {str(e)}")
                roc_auc = None

        res: dict[str, Any] = {
            "accuracy": round(acc, 5),
            "precision": round(prec, 5),
            "recall": round(rec, 5),
            "f1_weighted": round(f1_w, 5),
            "f1_macro": round(f1_m, 5),
            "confusion_matrix": cm,
        }
        if roc_auc is not None and not np.isnan(roc_auc):
            res["roc_auc"] = round(roc_auc, 5)
        else:
            res["roc_auc"] = None

        return res

    @staticmethod
    def compute_naive_baseline(
        y_train: np.ndarray | list[Any] | pd.Series,
        task_type: str
    ) -> dict[str, float]:
        """
        Computes baseline performance metrics on training partition:
        - Regression: Mean predictor (baseline R2 = 0.0 by construction, baseline MAE/MSE/RMSE computed for real).
        - Classification: Majority-class predictor's F1 & Accuracy on the fold labels (computed for real, not hardcoded to 0).
        """
        y_arr = np.asarray(y_train)

        if task_type == "REGRESSION":
            y_float = y_arr.astype(np.float64)
            y_mean = float(np.mean(y_float))
            y_pred_base = np.full_like(y_float, y_mean)

            mae = float(mean_absolute_error(y_float, y_pred_base))
            mse = float(mean_squared_error(y_float, y_pred_base))
            rmse = float(np.sqrt(mse))

            return {
                "r2": 0.0,
                "adjusted_r2": 0.0,
                "mae": round(mae, 5),
                "mse": round(mse, 5),
                "rmse": round(rmse, 5),
            }
        else:
            series = pd.Series(y_arr)
            mode_val = series.mode().iloc[0] if len(series) > 0 else y_arr[0]
            y_pred_base = np.full(len(y_arr), mode_val)

            acc = float(accuracy_score(y_arr, y_pred_base))
            f1_m = float(f1_score(y_arr, y_pred_base, average="macro", zero_division=0))
            f1_w = float(f1_score(y_arr, y_pred_base, average="weighted", zero_division=0))
            prec = float(precision_score(y_arr, y_pred_base, average="weighted", zero_division=0))
            rec = float(recall_score(y_arr, y_pred_base, average="weighted", zero_division=0))

            return {
                "accuracy": round(acc, 5),
                "f1_macro": round(f1_m, 5),
                "f1_weighted": round(f1_w, 5),
                "precision": round(prec, 5),
                "recall": round(rec, 5),
                "roc_auc": 0.5,
            }

    @classmethod
    def diagnose_fit(
        cls,
        train_metrics: dict[str, float],
        cv_mean_metrics: dict[str, float],
        baseline_metrics: dict[str, float],
        metric_name: str,
        n_val_samples: int | None = None,
        overfit_threshold: float | None = None,
        underfit_margin: float | None = None,
    ) -> str:
        """
        Implements the exact metric-direction-aware rule from SRS §2.10:
        
        Higher-is-better (Accuracy, F1, R2, ROC-AUC):
           Gap = Train - CV_Mean
        Lower-is-better (RMSE, MAE, MSE):
           Gap = CV_Mean - Train
           
        - 'INSUFFICIENT_DATA' if fold sizes are too small (< 20 rows)
        - 'POTENTIAL_OVERFIT' if Gap > threshold(metric)
        - 'POTENTIAL_UNDERFIT_WEAK_SIGNAL' if CV_Mean is only marginally above baseline AND Train is also close to baseline
        - 'GOOD_FIT' otherwise
        """
        if n_val_samples is not None and n_val_samples < 20:
            return "INSUFFICIENT_DATA"

        norm_metric = metric_name.lower().replace("-", "_").strip()
        train_val = train_metrics.get(norm_metric)
        cv_val = cv_mean_metrics.get(norm_metric)
        base_val = baseline_metrics.get(norm_metric)

        if train_val is None or cv_val is None:
            return "GOOD_FIT"

        is_higher_better = norm_metric in cls.HIGHER_IS_BETTER_METRICS or norm_metric not in cls.LOWER_IS_BETTER_METRICS

        if is_higher_better:
            gap = train_val - cv_val
            base_score = base_val if base_val is not None else 0.0

            # Configurable threshold & margin
            eff_threshold = (
                overfit_threshold
                if overfit_threshold is not None
                else cls.DEFAULT_OVERFIT_THRESHOLDS.get(norm_metric, 0.15)
            )
            eff_margin = underfit_margin if underfit_margin is not None else 0.05

            # Underfit / weak signal check
            cv_lift = cv_val - base_score
            train_lift = train_val - base_score
            if cv_lift <= eff_margin and train_lift <= (eff_margin * 2.5):
                return "POTENTIAL_UNDERFIT_WEAK_SIGNAL"

            # Overfit check
            if gap > eff_threshold:
                return "POTENTIAL_OVERFIT"

            return "GOOD_FIT"

        else:
            # Lower is better (e.g. RMSE, MAE, MSE)
            gap = cv_val - train_val
            base_score = base_val if base_val is not None else (cv_val + 1.0)

            eff_threshold = (
                overfit_threshold
                if overfit_threshold is not None
                else (cls.DEFAULT_OVERFIT_THRESHOLDS.get(norm_metric, 0.15) * max(base_score, 1.0))
            )
            eff_margin = underfit_margin if underfit_margin is not None else (0.05 * max(base_score, 1.0))

            # Underfit check: CV error is not much lower than baseline AND train error is not much lower than baseline
            cv_improvement = base_score - cv_val
            train_improvement = base_score - train_val
            if cv_improvement <= eff_margin and train_improvement <= (eff_margin * 2.5):
                return "POTENTIAL_UNDERFIT_WEAK_SIGNAL"

            # Overfit check
            if gap > eff_threshold:
                return "POTENTIAL_OVERFIT"

            return "GOOD_FIT"

    @classmethod
    def compute_model_selection_score(
        cls,
        task_type: str,
        cv_mean_metrics: dict[str, float],
        baseline_metrics: dict[str, float] | None = None,
    ) -> float:
        """
        Computes the composite convenience score (SRS §2.9):
        - Regression: normalize(R2) * 0.6 + (1 - normalize(RMSE)) * 0.4  [0..100 scale]
        - Classification: F1_weighted * 0.6 + ROC_AUC * 0.4             [0..100 scale]
        
        NOTE: This is a secondary UI convenience indicator and is NEVER used for leaderboard ranking.
        """
        if task_type == "REGRESSION":
            r2 = cv_mean_metrics.get("r2", 0.0)
            rmse = cv_mean_metrics.get("rmse", 0.0)

            norm_r2 = max(0.0, min(1.0, float(r2)))
            if baseline_metrics and baseline_metrics.get("rmse", 0.0) > 0:
                base_rmse = baseline_metrics["rmse"]
                norm_rmse = max(0.0, min(1.0, float(rmse) / float(base_rmse)))
                score = (norm_r2 * 0.6 + (1.0 - norm_rmse) * 0.4) * 100.0
            else:
                score = norm_r2 * 100.0
        else:
            f1_w = cv_mean_metrics.get("f1_weighted", cv_mean_metrics.get("f1_macro", 0.0))
            roc_auc = cv_mean_metrics.get("roc_auc")
            if roc_auc is not None and not np.isnan(roc_auc):
                score = (float(f1_w) * 0.6 + float(roc_auc) * 0.4) * 100.0
            else:
                acc = cv_mean_metrics.get("accuracy", f1_w)
                score = (float(f1_w) * 0.6 + float(acc) * 0.4) * 100.0

        return round(float(np.clip(score, 0.0, 100.0)), 2)
