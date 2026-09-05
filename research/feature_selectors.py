"""
Feature Selectors and Extensions for ML Studio Research Track (SRS §9).

Implements the 8-method feature selection comparison matrix:
1. No selection (baseline - all features retained with score 1.0)
2. Correlation (baseline selector - Day 5 reuse)
3. Lasso (baseline selector - Day 5 reuse)
4. Random Forest importance (baseline selector - Day 5 reuse)
5. Permutation (baseline selector - Day 5 reuse)
6. RFE (NEW baseline selector - recursive feature elimination)
7. Rank aggregation (proposed ensemble Method A - Day 5 reuse)
8. Rank aggregation + stability (proposed extension Method B - SRS §9)
"""

from dataclasses import dataclass
from typing import Any
import sys
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.feature_selection import RFE
from sklearn.linear_model import LinearRegression, LogisticRegression

# Ensure backend package can be imported without DB dependency
BACKEND_PATH = Path(__file__).resolve().parent.parent / "backend"
if str(BACKEND_PATH) not in sys.path:
    sys.path.insert(0, str(BACKEND_PATH))

from app.services.feature_selection_service import FeatureSelectionService


@dataclass
class SelectionResult:
    """
    Result container for a feature selection run.
    """
    method_name: str
    feature_names: list[str]
    raw_scores: np.ndarray
    rank_scores: np.ndarray
    ranks: np.ndarray
    selected_features: list[str]
    k_selected: int


# -----------------------------------------------------------------------------
# Baseline Selectors
# -----------------------------------------------------------------------------

def no_selection_baseline(
    X: pd.DataFrame | np.ndarray,
    y: pd.Series | np.ndarray = None,
    task_type: str = "REGRESSION",
    feature_names: list[str] | None = None,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Trivial baseline: every feature receives equal rank score 1.0.
    Returns: (raw_scores, ranks, rank_scores)
    """
    p = X.shape[1] if hasattr(X, "shape") else len(feature_names or [])
    if p == 0:
        return np.array([]), np.array([]), np.array([])
    raw_scores = np.ones(p, dtype=np.float64)
    ranks = np.ones(p, dtype=np.float64)
    rank_scores = np.ones(p, dtype=np.float64)
    return raw_scores, ranks, rank_scores


def correlation_importance(
    X: pd.DataFrame | np.ndarray,
    y: pd.Series | np.ndarray,
    task_type: str,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Correlation baseline: Reuses Day 5 FeatureSelectionService.compute_correlation_scores.
    """
    X_arr = np.asarray(X)
    y_arr = np.asarray(y)
    raw = FeatureSelectionService.compute_correlation_scores(X_arr, y_arr, task_type)
    ranks, rank_scores = FeatureSelectionService.calculate_technique_rank_scores(raw)
    return raw, ranks, rank_scores


def lasso_importance(
    X: pd.DataFrame | np.ndarray,
    y: pd.Series | np.ndarray,
    task_type: str,
    seed: int = 42,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Lasso (L1) baseline: Reuses Day 5 FeatureSelectionService.compute_lasso_scores.
    """
    X_arr = np.asarray(X)
    y_arr = np.asarray(y)
    raw = FeatureSelectionService.compute_lasso_scores(X_arr, y_arr, task_type, seed=seed)
    ranks, rank_scores = FeatureSelectionService.calculate_technique_rank_scores(raw)
    return raw, ranks, rank_scores


def random_forest_importance(
    X: pd.DataFrame | np.ndarray,
    y: pd.Series | np.ndarray,
    task_type: str,
    seed: int = 42,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Random Forest baseline: Reuses Day 5 FeatureSelectionService.compute_random_forest_scores.
    """
    X_arr = np.asarray(X)
    y_arr = np.asarray(y)
    raw = FeatureSelectionService.compute_random_forest_scores(X_arr, y_arr, task_type, seed=seed)
    ranks, rank_scores = FeatureSelectionService.calculate_technique_rank_scores(raw)
    return raw, ranks, rank_scores


def permutation_importance_score(
    X: pd.DataFrame | np.ndarray,
    y: pd.Series | np.ndarray,
    task_type: str,
    seed: int = 42,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Permutation baseline: Reuses Day 5 FeatureSelectionService.compute_permutation_scores.
    """
    X_arr = np.asarray(X)
    y_arr = np.asarray(y)
    raw = FeatureSelectionService.compute_permutation_scores(X_arr, y_arr, task_type, seed=seed)
    ranks, rank_scores = FeatureSelectionService.calculate_technique_rank_scores(raw)
    return raw, ranks, rank_scores


from sklearn.preprocessing import StandardScaler

def rfe_importance(
    X: pd.DataFrame | np.ndarray,
    y: pd.Series | np.ndarray,
    task_type: str,
    seed: int = 42,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    RFE baseline (NEW): Wrapped scikit-learn RFE around a simple linear model.
    Converts RFE ranking (1 is best) into rank-aggregation-compatible scores.
    """
    X_arr = np.asarray(X)
    y_arr = np.asarray(y)
    p = X_arr.shape[1]
    if p == 0:
        return np.array([]), np.array([]), np.array([])

    norm_task = task_type.upper().strip()
    if norm_task == "REGRESSION":
        estimator = LinearRegression()
        X_scaled = X_arr
    else:
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X_arr)
        estimator = LogisticRegression(max_iter=1000, random_state=seed, tol=1e-3)

    rfe = RFE(estimator=estimator, n_features_to_select=1, step=1)
    rfe.fit(X_scaled, y_arr)

    # Convert ranking_ (1=best, p=worst) to raw importance score where higher is better
    raw = (p + 1 - rfe.ranking_).astype(np.float64)
    ranks, rank_scores = FeatureSelectionService.calculate_technique_rank_scores(raw)
    return raw, ranks, rank_scores


# -----------------------------------------------------------------------------
# Proposed Ensemble Methods (A and B)
# -----------------------------------------------------------------------------

def rank_aggregation_ensemble(
    X: pd.DataFrame | np.ndarray,
    y: pd.Series | np.ndarray,
    task_type: str,
    seed: int = 42,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Method A: Proposed Rank Aggregation Ensemble (SRS §2.7).
    Averages normalized rank scores from the 4 Day 5 baseline selectors:
    (Correlation, Lasso, Random Forest, Permutation).
    """
    X_arr = np.asarray(X)
    y_arr = np.asarray(y)
    p = X_arr.shape[1]
    if p == 0:
        return np.array([]), np.array([]), np.array([])

    # Compute individual technique rank scores
    _, _, r_corr = correlation_importance(X_arr, y_arr, task_type)
    _, _, r_lasso = lasso_importance(X_arr, y_arr, task_type, seed=seed)
    _, _, r_rf = random_forest_importance(X_arr, y_arr, task_type, seed=seed)
    _, _, r_perm = permutation_importance_score(X_arr, y_arr, task_type, seed=seed)

    # Average normalized rank scores
    stacked = np.vstack([r_corr, r_lasso, r_rf, r_perm])
    ensemble_score = np.mean(stacked, axis=0)

    ranks, normalized_ensemble_scores = FeatureSelectionService.calculate_technique_rank_scores(ensemble_score)
    return ensemble_score, ranks, normalized_ensemble_scores


# -----------------------------------------------------------------------------
# Dispatcher and Top-K Selector
# -----------------------------------------------------------------------------

METHOD_MAP = {
    "no_selection": no_selection_baseline,
    "correlation": correlation_importance,
    "lasso": lasso_importance,
    "random_forest": random_forest_importance,
    "permutation": permutation_importance_score,
    "rfe": rfe_importance,
    "rank_aggregation": rank_aggregation_ensemble,
    # "rank_aggregation_stability" is handled in stability module
}


def select_features(
    X: pd.DataFrame,
    y: pd.Series,
    task_type: str,
    method: str,
    k_features: int | float | None = None,
    seed: int = 42,
    stability_vector: np.ndarray | None = None,
    alpha: float = 0.5,
) -> SelectionResult:
    """
    Runs feature selection for any of the 8 methods and returns selected feature names.

    Args:
        X: DataFrame of features.
        y: Series of target.
        task_type: "REGRESSION" or "CLASSIFICATION".
        method: One of the 8 method names.
        k_features: Number of features to select (integer, float fraction, or None for p//2).
        seed: Random seed.
        stability_vector: Feature stability vector for Method B.
        alpha: Weight for importance vs stability in Method B.
    """
    feature_names = list(X.columns)
    p = len(feature_names)
    norm_method = method.lower().strip().replace(" ", "_").replace("+", "_").replace("-", "_")

    if norm_method == "no_selection":
        raw, ranks, rank_scores = no_selection_baseline(X, y, task_type, feature_names)
        k = p
        selected = list(feature_names)
    elif norm_method in ["rank_aggregation_stability", "rank_aggregation_plus_stability"]:
        # Method B: Rank aggregation + stability
        ens_score, _, _ = rank_aggregation_ensemble(X, y, task_type, seed=seed)
        if stability_vector is None:
            # Fallback if stability vector not provided: default to ensemble score
            stability_vector = np.ones(p, dtype=np.float64)
        
        final_scores = alpha * ens_score + (1.0 - alpha) * stability_vector
        ranks, rank_scores = FeatureSelectionService.calculate_technique_rank_scores(final_scores)
        raw = final_scores

        k = _resolve_k(k_features, p)
        # Select top-k features by rank_scores (highest score first)
        sorted_indices = np.argsort(-rank_scores, kind="stable")
        selected = [feature_names[i] for i in sorted_indices[:k]]
    elif norm_method in METHOD_MAP:
        fn = METHOD_MAP[norm_method]
        if norm_method in ["lasso", "random_forest", "permutation", "rfe", "rank_aggregation"]:
            raw, ranks, rank_scores = fn(X, y, task_type, seed=seed)
        else:
            raw, ranks, rank_scores = fn(X, y, task_type)

        k = _resolve_k(k_features, p)
        sorted_indices = np.argsort(-rank_scores, kind="stable")
        selected = [feature_names[i] for i in sorted_indices[:k]]
    else:
        valid_methods = list(METHOD_MAP.keys()) + ["rank_aggregation_stability"]
        raise ValueError(f"Unknown method '{method}'. Valid methods: {valid_methods}")

    return SelectionResult(
        method_name=method,
        feature_names=feature_names,
        raw_scores=raw,
        rank_scores=rank_scores,
        ranks=ranks,
        selected_features=selected,
        k_selected=len(selected),
    )


def _resolve_k(k_features: int | float | None, p: int) -> int:
    """Helper to determine integer number of features to select."""
    if p <= 1:
        return max(1, p)
    if k_features is None:
        return max(1, p // 2)
    if isinstance(k_features, float) and 0.0 < k_features <= 1.0:
        return max(1, int(round(p * k_features)))
    if isinstance(k_features, int):
        return min(p, max(1, k_features))
    return max(1, p // 2)
