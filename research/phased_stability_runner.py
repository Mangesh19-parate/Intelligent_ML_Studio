"""
Phased Stability Runner for ML Studio Research Track (SRS §2, ADR-005).

Implements the explicit Four-Phase execution protocol:
    Phase 1 — Generate the population:
        Run repeated selections across Development partition using RANK_AGGREGATION (BaseScore only).
    Phase 2 — Compute stability:
        Stability_j = selection frequency for feature j across Phase 1's completed runs.
    Phase 3 — Apply the combined score:
        FinalScore_j = alpha * BaseScore_j + (1 - alpha) * Stability_j (alpha = 0.7 default / 0.5 protocol).
    Phase 4 — Evaluate RANK_AGGREGATION_STABILITY:
        Select Top-K by FinalScore_j and evaluate predictive performance via canonical CV path.
"""

from typing import Any, Sequence
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.metrics import mean_squared_error, f1_score
from sklearn.model_selection import KFold, StratifiedKFold
from sklearn.preprocessing import StandardScaler

from research.dataset_loader import load_dataset
from research.outer_split import create_split, partition_data
from research.feature_selectors import rank_aggregation_ensemble, _resolve_k
from research.stability import StabilityScorer


class PhasedStabilityExecutionResult:
    """Encapsulates the structured output of the 4-phase stability execution."""

    def __init__(
        self,
        dataset_name: str,
        task_type: str,
        n_features: int,
        k_selected: int,
        alpha: float,
        phase1_population_size: int,
        phase2_stability_scores: dict[str, float],
        phase3_combined_scores: dict[str, float],
        phase4_cv_scores: list[float],
        mean_cv_score: float,
        std_cv_score: float,
        metric_name: str,
        selected_features_final: list[str],
    ):
        self.dataset_name = dataset_name
        self.task_type = task_type
        self.n_features = n_features
        self.k_selected = k_selected
        self.alpha = alpha
        self.phase1_population_size = phase1_population_size
        self.phase2_stability_scores = phase2_stability_scores
        self.phase3_combined_scores = phase3_combined_scores
        self.phase4_cv_scores = phase4_cv_scores
        self.mean_cv_score = mean_cv_score
        self.std_cv_score = std_cv_score
        self.metric_name = metric_name
        self.selected_features_final = selected_features_final

    def to_dict(self) -> dict[str, Any]:
        return {
            "dataset": self.dataset_name,
            "task_type": self.task_type,
            "n_features": self.n_features,
            "k_selected": self.k_selected,
            "alpha": self.alpha,
            "phase1_population_size": self.phase1_population_size,
            "phase2_stability_scores": self.phase2_stability_scores,
            "phase3_combined_scores": self.phase3_combined_scores,
            "phase4_cv_scores": self.phase4_cv_scores,
            "mean_cv_score": self.mean_cv_score,
            "std_cv_score": self.std_cv_score,
            "metric_name": self.metric_name,
            "selected_features_final": self.selected_features_final,
        }


class PhasedStabilityRunner:
    """
    Executes the 4-phase stability workflow on the Development partition.
    Guarantees strict isolation of Locked Test partition.
    """

    def __init__(
        self,
        dataset_name: str,
        n_splits: int = 5,
        n_repeats: int = 8,
        alpha: float = 0.7,
        seed: int = 1000,
        k_features: int | float | None = None,
    ):
        self.dataset_name = dataset_name.lower().replace("-", "_").replace(" ", "_")
        self.n_splits = n_splits
        self.n_repeats = n_repeats
        self.alpha = float(alpha)
        self.seed = seed
        self.k_features = k_features

    def execute_four_phases(
        self,
        X_dev: pd.DataFrame,
        y_dev: pd.Series,
        task_type: str,
    ) -> PhasedStabilityExecutionResult:
        """
        Executes Phase 1 -> Phase 2 -> Phase 3 -> Phase 4 on the Development partition.
        """
        feature_names = list(X_dev.columns)
        p = len(feature_names)
        k = _resolve_k(self.k_features, p)
        norm_task = task_type.upper().strip()

        # =========================================================================
        # PHASE 1: Generate the population (Repeated RANK_AGGREGATION runs)
        # =========================================================================
        phase1_subsets: list[list[str]] = []
        phase1_rank_scores_list: list[np.ndarray] = []

        for rep in range(self.n_repeats):
            rep_seed = self.seed + rep
            if norm_task == "CLASSIFICATION":
                cv = StratifiedKFold(n_splits=self.n_splits, shuffle=True, random_state=rep_seed)
                splits = cv.split(X_dev, y_dev)
            else:
                cv = KFold(n_splits=self.n_splits, shuffle=True, random_state=rep_seed)
                splits = cv.split(X_dev)

            for train_idx, _ in splits:
                X_tr = X_dev.iloc[train_idx]
                y_tr = y_dev.iloc[train_idx]

                _, _, rank_scores = rank_aggregation_ensemble(
                    X_tr, y_tr, norm_task, seed=rep_seed
                )
                sorted_idx = np.argsort(-rank_scores, kind="stable")
                top_k = [feature_names[i] for i in sorted_idx[:k]]

                phase1_subsets.append(top_k)
                phase1_rank_scores_list.append(rank_scores)

        # =========================================================================
        # PHASE 2: Compute stability from Phase 1's output
        # =========================================================================
        stability_dict = StabilityScorer.compute_stability_from_subsets(
            phase1_subsets, feature_names
        )
        stability_vec = np.array([stability_dict[f] for f in feature_names], dtype=np.float64)

        # =========================================================================
        # PHASE 3: Apply the combined score
        # FinalScore_j = alpha * BaseScore_j + (1 - alpha) * Stability_j
        # =========================================================================
        # BaseScore_j: Compute on full Development partition (or average across Phase 1)
        _, _, base_dev_rank_scores = rank_aggregation_ensemble(
            X_dev, y_dev, norm_task, seed=self.seed
        )
        final_scores_vec = (
            self.alpha * base_dev_rank_scores + (1.0 - self.alpha) * stability_vec
        )
        final_scores_dict = {f: float(final_scores_vec[i]) for i, f in enumerate(feature_names)}

        # Sort features by combined score (descending, with stable tie-break)
        final_sorted_idx = np.argsort(-final_scores_vec, kind="stable")
        final_selected_features = [feature_names[i] for i in final_sorted_idx[:k]]

        # =========================================================================
        # PHASE 4: Evaluate RANK_AGGREGATION_STABILITY predictive performance
        # =========================================================================
        eval_scores: list[float] = []
        metric_name = "RMSE" if norm_task == "REGRESSION" else "F1_MACRO"

        for rep in range(self.n_repeats):
            rep_seed = self.seed + rep
            if norm_task == "CLASSIFICATION":
                cv = StratifiedKFold(n_splits=self.n_splits, shuffle=True, random_state=rep_seed)
                splits = cv.split(X_dev, y_dev)
            else:
                cv = KFold(n_splits=self.n_splits, shuffle=True, random_state=rep_seed)
                splits = cv.split(X_dev)

            for train_idx, val_idx in splits:
                X_tr, X_val = X_dev.iloc[train_idx], X_dev.iloc[val_idx]
                y_tr, y_val = y_dev.iloc[train_idx], y_dev.iloc[val_idx]

                # Nested Inner CV: Estimate stability strictly from X_tr (zero val leakage)
                inner_splits_count = min(3, len(X_tr))
                if norm_task == "CLASSIFICATION":
                    inner_cv = StratifiedKFold(n_splits=inner_splits_count, shuffle=True, random_state=rep_seed + 1)
                    inner_splits = list(inner_cv.split(X_tr, y_tr))
                else:
                    inner_cv = KFold(n_splits=inner_splits_count, shuffle=True, random_state=rep_seed + 1)
                    inner_splits = list(inner_cv.split(X_tr))

                inner_subsets = []
                for in_idx, (in_tr_idx, _) in enumerate(inner_splits):
                    X_in_tr = X_tr.iloc[in_tr_idx]
                    y_in_tr = y_tr.iloc[in_tr_idx]
                    _, _, in_ranks = rank_aggregation_ensemble(
                        X_in_tr, y_in_tr, norm_task, seed=rep_seed + 100 + in_idx
                    )
                    in_sorted = np.argsort(-in_ranks, kind="stable")
                    inner_subsets.append([feature_names[i] for i in in_sorted[:k]])

                inner_stab_dict = StabilityScorer.compute_stability_from_subsets(
                    inner_subsets, feature_names
                )
                inner_stab_vec = np.array([inner_stab_dict[f] for f in feature_names], dtype=np.float64)

                # Select features on this training fold slice using inner stability
                _, _, fold_base_scores = rank_aggregation_ensemble(
                    X_tr, y_tr, norm_task, seed=rep_seed
                )
                fold_final_scores = (
                    self.alpha * fold_base_scores + (1.0 - self.alpha) * inner_stab_vec
                )
                fold_sorted_idx = np.argsort(-fold_final_scores, kind="stable")
                fold_selected_feats = [feature_names[i] for i in fold_sorted_idx[:k]]

                # Fit and predict with reference model
                scaler = StandardScaler()
                X_tr_sc = scaler.fit_transform(X_tr[fold_selected_feats])
                X_val_sc = scaler.transform(X_val[fold_selected_feats])

                if norm_task == "REGRESSION":
                    model = RandomForestRegressor(
                        n_estimators=50, max_depth=10, random_state=rep_seed, n_jobs=-1
                    )
                    model.fit(X_tr_sc, y_tr)
                    preds = model.predict(X_val_sc)
                    score = float(np.sqrt(mean_squared_error(y_val, preds)))
                else:
                    model = RandomForestClassifier(
                        n_estimators=50, max_depth=10, random_state=rep_seed, n_jobs=-1
                    )
                    model.fit(X_tr_sc, y_tr)
                    preds = model.predict(X_val_sc)
                    score = float(f1_score(np.asarray(y_val), preds, average="macro"))

                eval_scores.append(score)

        return PhasedStabilityExecutionResult(
            dataset_name=self.dataset_name,
            task_type=norm_task,
            n_features=p,
            k_selected=k,
            alpha=self.alpha,
            phase1_population_size=len(phase1_subsets),
            phase2_stability_scores=stability_dict,
            phase3_combined_scores=final_scores_dict,
            phase4_cv_scores=eval_scores,
            mean_cv_score=float(np.mean(eval_scores)),
            std_cv_score=float(np.std(eval_scores, ddof=1)) if len(eval_scores) > 1 else 0.0,
            metric_name=metric_name,
            selected_features_final=final_selected_features,
        )


def run_phased_stability_experiment(
    dataset_name: str,
    alpha: float = 0.7,
    n_splits: int = 5,
    n_repeats: int = 8,
    seed: int = 1000,
) -> PhasedStabilityExecutionResult:
    """
    Loads dataset, creates 80% Development partition, and runs the 4-phase stability procedure.
    """
    X, y, task_type = load_dataset(dataset_name)
    split_info = create_split(X, y, task_type, locked_test_pct=20, seed=seed)
    (X_dev, y_dev), _ = partition_data(X, y, split_info)

    runner = PhasedStabilityRunner(
        dataset_name=dataset_name,
        n_splits=n_splits,
        n_repeats=n_repeats,
        alpha=alpha,
        seed=seed,
    )
    return runner.execute_four_phases(X_dev, y_dev, task_type)
