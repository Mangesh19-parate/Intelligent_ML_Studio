"""
Experiment Runner for ML Studio Research Track (SRS §9).

Harness for executing repeated K-Fold Cross-Validation on the Development partition.
Features:
- Per-fold feature selection (zero validation/test leakage).
- Two-pass stability reweighting for Method B (RANK_AGGREGATION_STABILITY):
    Pass 1: Computes rank aggregation ensemble on each fold's training slice.
    Pass 2: Reweights scores using stability across the same run's folds:
            FinalScore_j = alpha * EnsembleScore_j + (1 - alpha) * Stability_j
- Fixed downstream reference model (RandomForest or Linear) across all methods.
- Fixed metrics:
    * Regression: RMSE
    * Classification: ROC-AUC (fallback to F1-macro for uncalibrated probas)
- Results recorded into ResultsStore with exact per-fold runtime, alpha, and feature selections.
"""

from datetime import datetime, timezone
import time
from typing import Any
import numpy as np
import pandas as pd
from sklearn.metrics import mean_squared_error, roc_auc_score, f1_score
from sklearn.linear_model import Ridge, LogisticRegression
from sklearn.ensemble import RandomForestRegressor, RandomForestClassifier
from sklearn.model_selection import KFold, StratifiedKFold
from sklearn.preprocessing import StandardScaler

from research.dataset_loader import load_dataset
from research.outer_split import create_split, partition_data
from research.feature_selectors import select_features, rank_aggregation_ensemble, _resolve_k
from research.stability import StabilityScorer
from research.results_store import ResultsStore, DEFAULT_DB_PATH
from app.services.feature_selection_service import FeatureSelectionService


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
        seed: int = 1000,
        outer_seed: int | None = None,
        start_repeat_idx: int = 0,
        k_features: int | float | None = None,
        alpha: float = 0.5,
        reference_model: str = "RandomForest",
        results_store: ResultsStore | None = None,
    ):
        self.dataset_name = dataset_name.lower().replace("-", "_").replace(" ", "_")
        self.method_name = method_name.strip()
        self.n_splits = n_splits
        self.n_repeats = n_repeats
        self.seed = seed
        self.outer_seed = outer_seed if outer_seed is not None else seed
        self.start_repeat_idx = start_repeat_idx
        self.k_features = k_features
        self.alpha = float(alpha)
        self.reference_model = reference_model
        self.results_store = results_store or ResultsStore(DEFAULT_DB_PATH)

    def _get_downstream_model(self, task_type: str, fold_seed: int):
        norm_ref = self.reference_model.lower().replace("-", "_").replace(" ", "_")
        if norm_ref in ["randomforest", "random_forest", "rf"]:
            if task_type == "REGRESSION":
                return RandomForestRegressor(n_estimators=50, max_depth=10, random_state=fold_seed, n_jobs=-1)
            else:
                return RandomForestClassifier(n_estimators=50, max_depth=10, random_state=fold_seed, n_jobs=-1)
        else:
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
        feature_names = list(X.columns)
        p = len(feature_names)
        k = _resolve_k(self.k_features, p)

        # 2. Create Outer Split (Development vs Locked Test)
        outer_seed = self.outer_seed if self.outer_seed is not None else self.seed
        split_result = create_split(X, y, task_type, locked_test_pct=20, seed=outer_seed)
        (X_dev, y_dev), _ = partition_data(X, y, split_result)

        fold_records: list[dict[str, Any]] = []
        norm_method = self.method_name.lower().replace("-", "_").replace(" ", "_")
        is_stability_method = norm_method in ["rank_aggregation_stability", "rank_aggregation_plus_stability"]

        # 3. Repeated K-Fold Cross-Validation on Development partition
        for rep_offset in range(self.n_repeats):
            run_idx = self.start_repeat_idx + rep_offset
            run_seed = self.seed + run_idx

            if task_type == "CLASSIFICATION":
                cv = StratifiedKFold(n_splits=self.n_splits, shuffle=True, random_state=run_seed)
                splits = list(cv.split(X_dev, y_dev))
            else:
                cv = KFold(n_splits=self.n_splits, shuffle=True, random_state=run_seed)
                splits = list(cv.split(X_dev))

            if is_stability_method:
                # -------------------------------------------------------------
                # Method B (RANK_AGGREGATION_STABILITY): Two-Pass Procedure
                # Pass 1: Run rank aggregation on each fold's training slice
                # -------------------------------------------------------------
                fold_ens_scores = []
                fold_pass1_selected = []

                for fold_idx, (train_idx, _) in enumerate(splits):
                    fold_seed = run_seed + fold_idx * 10
                    X_tr = X_dev.iloc[train_idx]
                    y_tr = y_dev.iloc[train_idx]

                    _, _, rank_scores = rank_aggregation_ensemble(
                        X_tr, y_tr, task_type, seed=fold_seed
                    )
                    sorted_idx = np.argsort(-rank_scores, kind="stable")
                    top_k_feats = [feature_names[i] for i in sorted_idx[:k]]

                    fold_ens_scores.append(rank_scores)
                    fold_pass1_selected.append(top_k_feats)

                # Compute feature stability across the SAME run's folds
                stab_dict = StabilityScorer.compute_stability_from_subsets(
                    fold_pass1_selected, feature_names
                )
                stab_vector = np.array([stab_dict[f] for f in feature_names], dtype=np.float64)

                # -------------------------------------------------------------
                # Pass 2: Reweight fold ensemble scores with stability
                # -------------------------------------------------------------
                for fold_idx, (train_idx, val_idx) in enumerate(splits):
                    start_time = time.perf_counter()
                    fold_seed = run_seed + fold_idx * 10

                    X_train_fold = X_dev.iloc[train_idx]
                    y_train_fold = y_dev.iloc[train_idx]
                    X_val_fold = X_dev.iloc[val_idx]
                    y_val_fold = y_dev.iloc[val_idx]

                    # FinalScore_j = alpha * EnsembleScore_j + (1 - alpha) * Stability_j
                    ens_scores = fold_ens_scores[fold_idx]
                    final_scores = self.alpha * ens_scores + (1.0 - self.alpha) * stab_vector
                    _, final_rank_scores = FeatureSelectionService.calculate_technique_rank_scores(final_scores)

                    sorted_idx = np.argsort(-final_rank_scores, kind="stable")
                    selected_cols = [feature_names[i] for i in sorted_idx[:k]]

                    # Filter and scale
                    X_tr_sel = X_train_fold[selected_cols].to_numpy(dtype=np.float64)
                    X_val_sel = X_val_fold[selected_cols].to_numpy(dtype=np.float64)

                    scaler = StandardScaler()
                    X_tr_scaled = scaler.fit_transform(X_tr_sel)
                    X_val_scaled = scaler.transform(X_val_sel)

                    # Downstream model fitting and evaluation
                    model = self._get_downstream_model(task_type, fold_seed)
                    model.fit(X_tr_scaled, y_train_fold)

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
                        "alpha": float(self.alpha),
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    }
                    fold_records.append(rec)
            else:
                # -------------------------------------------------------------
                # Standard 1-Pass Feature Selection (Baselines + Method A)
                # -------------------------------------------------------------
                for fold_idx, (train_idx, val_idx) in enumerate(splits):
                    start_time = time.perf_counter()
                    fold_seed = run_seed + fold_idx * 10

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
                        seed=fold_seed,
                    )
                    selected_cols = sel_res.selected_features

                    # Filter and scale features
                    X_tr_sel = X_train_fold[selected_cols].to_numpy(dtype=np.float64)
                    X_val_sel = X_val_fold[selected_cols].to_numpy(dtype=np.float64)

                    scaler = StandardScaler()
                    X_tr_scaled = scaler.fit_transform(X_tr_sel)
                    X_val_scaled = scaler.transform(X_val_sel)

                    # Train downstream model
                    model = self._get_downstream_model(task_type, fold_seed)
                    model.fit(X_tr_scaled, y_train_fold)

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
                        "alpha": float(self.alpha) if norm_method == "rank_aggregation" else None,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    }
                    fold_records.append(rec)

        if save_results and fold_records:
            self.results_store.save_batch(fold_records)

        return fold_records


class ResearchExperimentRunner(ExperimentRunner):
    """
    Research Experiment Runner for ML Studio Research Track (SRS §9).
    Exposes run_single() for executing individual repeats / experimental runs.
    """

    @classmethod
    def run_single(
        cls,
        dataset_name: str,
        method_name: str,
        repeat_index: int = 0,
        n_splits: int = 5,
        base_seed: int = 1000,
        outer_seed: int = 1000,
        k_features: int | float | None = None,
        alpha: float = 0.5,
        reference_model: str = "RandomForest",
        results_store: ResultsStore | None = None,
        save_results: bool = True,
    ) -> list[dict[str, Any]]:
        """
        Executes a single repeat (all n_splits folds) for a (dataset, method, repeat_index).
        """
        runner = cls(
            dataset_name=dataset_name,
            method_name=method_name,
            n_splits=n_splits,
            n_repeats=1,
            seed=base_seed,
            outer_seed=outer_seed,
            start_repeat_idx=repeat_index,
            k_features=k_features,
            alpha=alpha,
            reference_model=reference_model,
            results_store=results_store,
        )
        return runner.run(save_results=save_results)

