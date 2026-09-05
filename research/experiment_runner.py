"""
Experiment Runner for ML Studio Research Track (SRS §9).

Harness for executing repeated K-Fold Cross-Validation on the Development partition.
Features:
- Per-fold feature selection (zero validation/test leakage).
- Fixed downstream model:
    * Regression: Ridge(alpha=1.0)
    * Classification: LogisticRegression(max_iter=1000, random_state=42)
- Fixed metrics:
    * Regression: RMSE
    * Classification: ROC-AUC (fallback to F1-macro for uncalibrated probas)
- Results recorded into ResultsStore with exact per-fold runtime and feature selections.
"""

from datetime import datetime, timezone
import time
from typing import Any
import numpy as np
import pandas as pd
from sklearn.metrics import mean_squared_error, roc_auc_score, f1_score
from sklearn.linear_model import Ridge, LogisticRegression
from sklearn.model_selection import KFold, StratifiedKFold
from sklearn.preprocessing import StandardScaler

from research.dataset_loader import load_dataset
from research.outer_split import create_split, partition_data
from research.feature_selectors import select_features
from research.stability import StabilityScorer
from research.results_store import ResultsStore, DEFAULT_DB_PATH


class ExperimentRunner:
    """
    Executes feature selection experiments across repeated K-Fold CV partitions.
    """

    def __init__(
        self,
        dataset_name: str,
        method_name: str,
        n_splits: int = 5,
        n_repeats: int = 2,
        seed: int = 42,
        k_features: int | float | None = None,
        alpha: float = 0.5,
        results_store: ResultsStore | None = None,
    ):
        self.dataset_name = dataset_name.lower().replace("-", "_").replace(" ", "_")
        self.method_name = method_name.lower().replace("-", "_").replace(" ", "_")
        self.n_splits = n_splits
        self.n_repeats = n_repeats
        self.seed = seed
        self.k_features = k_features
        self.alpha = alpha
        self.results_store = results_store or ResultsStore(DEFAULT_DB_PATH)

    def _get_downstream_model(self, task_type: str, fold_seed: int):
        if task_type == "REGRESSION":
            return Ridge(alpha=1.0, random_state=fold_seed)
        else:
            return LogisticRegression(max_iter=1000, random_state=fold_seed, tol=1e-3)

    def _evaluate_predictions(
        self,
        y_true: pd.Series | np.ndarray,
        y_pred: np.ndarray,
        y_proba: np.ndarray | None,
        task_type: str,
    ) -> tuple[str, float]:
        if task_type == "REGRESSION":
            rmse = float(np.sqrt(mean_squared_error(y_true, y_pred)))
            return "RMSE", rmse
        else:
            y_true_arr = np.asarray(y_true)
            if y_proba is not None and len(np.unique(y_true_arr)) == 2:
                try:
                    # Positive class probability
                    pos_proba = y_proba[:, 1] if y_proba.ndim == 2 else y_proba
                    auc = float(roc_auc_score(y_true_arr, pos_proba))
                    return "ROC_AUC", auc
                except Exception:
                    pass
            f1 = float(f1_score(y_true_arr, y_pred, average="macro"))
            return "F1_MACRO", f1

    def run(self, save_results: bool = True) -> list[dict[str, Any]]:
        """
        Executes the full repeated CV evaluation harness on the Development partition.
        NOTE: Locked Test partition is strictly isolated and NEVER accessed during CV.

        Returns:
            List of result dictionaries (one per fold).
        """
        # 1. Load dataset
        X, y, task_type = load_dataset(self.dataset_name)

        # 2. Create Outer Split (Development vs Locked Test)
        split_result = create_split(X, y, task_type, locked_test_pct=20, seed=self.seed)
        (X_dev, y_dev), _ = partition_data(X, y, split_result)

        # 3. For Method B (Rank Aggregation + Stability), compute stability vector strictly on Development set
        stability_vec = None
        if self.method_name in ["rank_aggregation_stability", "rank_aggregation_plus_stability"]:
            stability_vec, _ = StabilityScorer.estimate_stability_on_development(
                X_dev=X_dev,
                y_dev=y_dev,
                task_type=task_type,
                n_splits=self.n_splits,
                n_repeats=self.n_repeats,
                seed=self.seed,
                k_features=self.k_features,
            )

        # 4. Repeated K-Fold Cross-Validation on Development partition
        fold_records: list[dict[str, Any]] = []

        for run_idx in range(self.n_repeats):
            run_seed = self.seed + run_idx * 1000

            if task_type == "CLASSIFICATION":
                cv = StratifiedKFold(n_splits=self.n_splits, shuffle=True, random_state=run_seed)
                splits = cv.split(X_dev, y_dev)
            else:
                cv = KFold(n_splits=self.n_splits, shuffle=True, random_state=run_seed)
                splits = cv.split(X_dev)

            for fold_idx, (train_idx, val_idx) in enumerate(splits):
                start_time = time.perf_counter()

                X_train_fold = X_dev.iloc[train_idx]
                y_train_fold = y_dev.iloc[train_idx]
                X_val_fold = X_dev.iloc[val_idx]
                y_val_fold = y_dev.iloc[val_idx]

                # Run feature selection strictly on training fold
                sel_res = select_features(
                    X=X_train_fold,
                    y=y_train_fold,
                    task_type=task_type,
                    method=self.method_name,
                    k_features=self.k_features,
                    seed=run_seed + fold_idx,
                    stability_vector=stability_vec,
                    alpha=self.alpha,
                )
                selected_cols = sel_res.selected_features

                # Filter and scale features
                X_tr_sel = X_train_fold[selected_cols].to_numpy(dtype=np.float64)
                X_val_sel = X_val_fold[selected_cols].to_numpy(dtype=np.float64)

                scaler = StandardScaler()
                X_tr_scaled = scaler.fit_transform(X_tr_sel)
                X_val_scaled = scaler.transform(X_val_sel)

                # Train downstream model
                model = self._get_downstream_model(task_type, run_seed + fold_idx)
                model.fit(X_tr_scaled, y_train_fold)

                # Downstream evaluation
                y_pred = model.predict(X_val_scaled)
                y_proba = model.predict_proba(X_val_scaled) if hasattr(model, "predict_proba") else None

                metric_name, metric_val = self._evaluate_predictions(
                    y_val_fold, y_pred, y_proba, task_type
                )
                elapsed_sec = time.perf_counter() - start_time

                rec = {
                    "dataset": self.dataset_name,
                    "method": self.method_name,
                    "run_index": run_idx,
                    "fold_index": fold_idx,
                    "cv_metric_name": metric_name,
                    "cv_metric_value": float(metric_val),
                    "selected_features": selected_cols,
                    "runtime_seconds": float(elapsed_sec),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
                fold_records.append(rec)

        if save_results and fold_records:
            self.results_store.save_batch(fold_records)

        return fold_records
