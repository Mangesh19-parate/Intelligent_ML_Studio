"""
Stability Scorer and Selection Stability Metric for ML Studio Research Track (SRS §9).

Implements:
1. Selection frequency per feature:
       Stability(feature j) = (number of runs where j is selected) / (total runs)
       FinalScore_j = alpha * EnsembleScore_j + (1 - alpha) * Stability_j
2. Pairwise Jaccard Index across folds/repeats:
       Jaccard(A, B) = |A ∩ B| / |A ∪ B|
       Mean Pairwise Jaccard = (2 / M(M-1)) * sum_{i < j} Jaccard(S_i, S_j)
3. Kuncheva Stability Index (corrected for chance agreement):
       K(A, B) = (|A ∩ B| * p - |A| * |B|) / (min(|A|, |B|) * p - |A| * |B|)
       Kuncheva = (2 / M(M-1)) * sum_{i < j} K(S_i, S_j)
4. Nogueira et al. (2018) Stability Index:
       1 - (p / (p - k_bar)) * sum_j (s_j^2 / (k_bar * (1 - k_bar / p)))

METHODOLOGICAL DISCIPLINE (SRS §9):
Stability is computed strictly via repeated Cross-Validation on the Development partition
only. The Locked Test partition NEVER enters this computation.
"""

import json
from itertools import combinations
from typing import Sequence
import numpy as np
import pandas as pd
from sklearn.model_selection import KFold, StratifiedKFold


def compute_pairwise_jaccard(subsets: Sequence[Sequence[str]]) -> float:
    """
    Computes mean pairwise Jaccard similarity across all pairs of feature subsets.
    Returns value in [0.0, 1.0].
    """
    m = len(subsets)
    if m < 2:
        return 1.0 if m == 1 and len(subsets[0]) > 0 else 0.0

    sets = [set(s) for s in subsets]
    jaccards = []
    for s1, s2 in combinations(sets, 2):
        union_len = len(s1.union(s2))
        if union_len == 0:
            jaccards.append(1.0)
        else:
            jaccards.append(len(s1.intersection(s2)) / float(union_len))

    return float(np.mean(jaccards)) if jaccards else 0.0


def compute_kuncheva_index(
    subsets: Sequence[Sequence[str]],
    total_features: int,
) -> float:
    """
    Computes the Kuncheva Stability Index across all pairs of feature subsets,
    corrected for chance overlap under random selection.
    
    K(A, B) = (|A ∩ B| * p - |A| * |B|) / (min(|A|, |B|) * p - |A| * |B|)
    Returns value in [-1.0, 1.0], where 0 indicates chance agreement, 1 indicates identity.
    """
    m = len(subsets)
    p = total_features
    if m < 2 or p <= 1:
        return 1.0 if m >= 1 and p > 0 else 0.0

    sets = [set(s) for s in subsets]
    indices = []
    for s1, s2 in combinations(sets, 2):
        k1 = len(s1)
        k2 = len(s2)
        r = len(s1.intersection(s2))
        
        denom = (min(k1, k2) * p) - (k1 * k2)
        if denom == 0:
            indices.append(1.0 if k1 == k2 == r else 0.0)
        else:
            num = (r * p) - (k1 * k2)
            indices.append(float(num) / float(denom))

    return float(np.mean(indices)) if indices else 0.0


def compute_nogueira_stability(
    selection_indicator_matrix: np.ndarray,
) -> float:
    """
    Computes Nogueira et al. (2018) stability index from a binary selection matrix (M runs, p features).
    Properly handles arbitrary and varying feature subset sizes across folds.
    """
    arr = np.asarray(selection_indicator_matrix, dtype=np.float64)
    if arr.ndim != 2 or arr.shape[0] < 2 or arr.shape[1] <= 1:
        return 1.0 if arr.ndim == 2 and arr.shape[1] > 0 else 0.0

    m, p = arr.shape
    # Feature selection frequencies
    p_hat = np.mean(arr, axis=0)  # shape (p,)
    # Sample variance per feature
    s2 = (m / (m - 1.0)) * p_hat * (1.0 - p_hat)
    k_bar = float(np.sum(p_hat))

    if k_bar == 0 or k_bar == p:
        return 1.0

    denom = k_bar * (1.0 - k_bar / float(p))
    if denom == 0:
        return 1.0

    stab = 1.0 - (float(p) / float(p - 1.0)) * (float(np.sum(s2)) / (float(m) * denom))
    return float(np.clip(stab, -1.0, 1.0))


def compute_selection_stability(
    runs_df: pd.DataFrame,
    dataset_name: str,
    method: str,
    all_features: Sequence[str] | None = None,
) -> dict[str, float]:
    """
    Computes feature selection stability for a given (dataset, method) pair from runs_df.

    Implements exact formula from SRS §9.2:
        Stability(feature j) = (number of runs where j is selected) / (total runs)

    Reads from runs_df's `selected_features` column across all fold/run rows
    for the specified (dataset_name, method) pair.
    Locked Test plays no role in this computation at all.
    """
    if runs_df is None or runs_df.empty:
        if all_features:
            return {f: 0.0 for f in all_features}
        return {}

    norm_dataset = dataset_name.lower().strip().replace("-", "_").replace(" ", "_")
    norm_method = method.lower().strip().replace("-", "_").replace(" ", "_")

    # Filter matching rows
    df_datasets = runs_df["dataset"].astype(str).str.lower().str.strip().str.replace("-", "_").str.replace(" ", "_")
    df_methods = runs_df["method"].astype(str).str.lower().str.strip().str.replace("-", "_").str.replace(" ", "_")
    mask = (df_datasets == norm_dataset) & (df_methods == norm_method)
    subset_df = runs_df[mask]

    total_runs = len(subset_df)
    if total_runs == 0:
        if all_features:
            return {f: 0.0 for f in all_features}
        return {}

    # Parse selected features per row
    parsed_subsets: list[list[str]] = []
    discovered_features: set[str] = set()

    for val in subset_df["selected_features"]:
        if isinstance(val, (list, tuple, set)):
            feats = list(val)
        elif isinstance(val, str):
            val_trimmed = val.strip()
            if val_trimmed.startswith("[") and val_trimmed.endswith("]"):
                try:
                    feats = json.loads(val_trimmed)
                except Exception:
                    feats = [s.strip(" '\"") for s in val_trimmed[1:-1].split(",") if s.strip()]
            else:
                feats = [val_trimmed]
        else:
            feats = []
        parsed_subsets.append(feats)
        discovered_features.update(feats)

    target_features = list(all_features) if all_features is not None else sorted(discovered_features)

    counts = {f: 0 for f in target_features}
    for feat_list in parsed_subsets:
        feat_set = set(feat_list)
        for f in target_features:
            if f in feat_set:
                counts[f] += 1

    return {f: counts[f] / float(total_runs) for f in target_features}


class StabilityScorer:
    """
    Computes feature selection stability across repeated CV subsamples and
    blends stability with rank importance scores.
    """

    def __init__(self, alpha: float = 0.7):
        """
        Args:
            alpha: Weight assigned to feature importance (0.0 <= alpha <= 1.0).
                   Stability receives weight (1.0 - alpha). Default: 0.7.
        """
        if not (0.0 <= alpha <= 1.0):
            raise ValueError(f"alpha must be in [0.0, 1.0], got {alpha}")
        self.alpha = float(alpha)

    @staticmethod
    def compute_stability_from_subsets(
        selected_subsets: Sequence[Sequence[str]],
        all_feature_names: Sequence[str],
    ) -> dict[str, float]:
        """
        Calculates selection frequency for each feature across a list of selected feature sets.
        """
        total_runs = len(selected_subsets)
        if total_runs == 0:
            return {f: 0.0 for f in all_feature_names}

        counts = {f: 0 for f in all_feature_names}
        for subset in selected_subsets:
            subset_set = set(subset)
            for f in all_feature_names:
                if f in subset_set:
                    counts[f] += 1

        return {f: counts[f] / float(total_runs) for f in all_feature_names}

    @staticmethod
    def compute_stability_from_matrix(
        selection_indicator_matrix: np.ndarray | pd.DataFrame,
    ) -> np.ndarray:
        """
        Given a binary matrix of shape (n_runs, n_features) where 1 indicates selected:
        Computes Stability_j = mean(indicator_j across runs).
        """
        arr = np.asarray(selection_indicator_matrix, dtype=np.float64)
        if arr.ndim != 2:
            raise ValueError(f"Expected 2D matrix (n_runs, n_features), got shape {arr.shape}")
        if arr.shape[0] == 0:
            return np.zeros(arr.shape[1], dtype=np.float64)
        return np.mean(arr, axis=0)

    def compute_final_score(
        self,
        importance_scores: np.ndarray | Sequence[float],
        stability_scores: np.ndarray | Sequence[float],
        alpha: float | None = None,
    ) -> np.ndarray:
        """
        Combines Importance and Stability using:
        FinalScore_j = alpha * Importance_j + (1 - alpha) * Stability_j
        """
        eff_alpha = self.alpha if alpha is None else float(alpha)
        imp = np.asarray(importance_scores, dtype=np.float64)
        stab = np.asarray(stability_scores, dtype=np.float64)

        if imp.shape != stab.shape:
            raise ValueError(f"Shape mismatch: importance {imp.shape} vs stability {stab.shape}")

        return eff_alpha * imp + (1.0 - eff_alpha) * stab

    @classmethod
    def estimate_stability_on_development(
        cls,
        X_dev: pd.DataFrame,
        y_dev: pd.Series,
        task_type: str,
        n_splits: int = 5,
        n_repeats: int = 2,
        seed: int = 42,
        k_features: int | float | None = None,
    ) -> tuple[np.ndarray, dict[str, float]]:
        """
        Computes the feature stability vector by running repeated CV on the Development partition.
        NOTE: Locked Test partition is NEVER passed or accessed here.

        Returns:
            (stability_vector_array, stability_dict)
        """
        from research.feature_selectors import rank_aggregation_ensemble, _resolve_k

        feature_names = list(X_dev.columns)
        p = len(feature_names)
        k = _resolve_k(k_features, p)

        selected_subsets: list[list[str]] = []
        norm_task = task_type.upper().strip()

        for rep in range(n_repeats):
            rep_seed = seed + rep * 1000
            if norm_task == "CLASSIFICATION":
                cv = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=rep_seed)
                splits = cv.split(X_dev, y_dev)
            else:
                cv = KFold(n_splits=n_splits, shuffle=True, random_state=rep_seed)
                splits = cv.split(X_dev)

            for train_idx, _ in splits:
                X_tr = X_dev.iloc[train_idx]
                y_tr = y_dev.iloc[train_idx]

                # Run baseline rank aggregation on this training slice
                ens_scores, _, rank_scores = rank_aggregation_ensemble(
                    X_tr, y_tr, norm_task, seed=rep_seed
                )
                sorted_idx = np.argsort(-rank_scores, kind="stable")
                top_k = [feature_names[i] for i in sorted_idx[:k]]
                selected_subsets.append(top_k)

        stab_dict = cls.compute_stability_from_subsets(selected_subsets, feature_names)
        stab_vec = np.array([stab_dict[f] for f in feature_names], dtype=np.float64)
        return stab_vec, stab_dict
