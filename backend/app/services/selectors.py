"""
Feature Selectors and SRS v9 Mathematical Rank Aggregation Engine (SRS §2.7, §8).

This module implements standalone, modular feature selectors and the exact SRS v9
rank calculation formula:
- Ties handled via average rank.
- p = 1 edge case yields rank score = 1.0 (avoids p - 1 = 0 division error).
- Normalized rank score: r_{j,T} = 1 - (rank_{j,T} - 1) / (p - 1).
- APPLIED, SKIPPED, and FAILED status tracking.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any
import warnings
import numpy as np
import pandas as pd
from scipy.stats import rankdata
from sklearn.ensemble import RandomForestRegressor, RandomForestClassifier
from sklearn.linear_model import Lasso, LogisticRegression, Ridge
from sklearn.inspection import permutation_importance
from app.config.contract import FeatureSelectionMethod, TechniqueStatus, EvidenceStrength


def compute_evidence_strength(
    applied_count: int,
    total_count: int = 4,
    min_required: int = 2,
) -> EvidenceStrength:
    """
    Computes evidence strength band based on number of contributing techniques (SRS §2.7, §8).
    - STRONG: 4 of 4 techniques applied (applied_count >= 4)
    - MODERATE: 3 of 4 techniques applied (applied_count == 3)
    - LIMITED: 2 of 4 techniques applied (applied_count == 2)
    - INSUFFICIENT_EVIDENCE: < 2 techniques applied (applied_count < min_required)
    """
    if applied_count < min_required:
        return EvidenceStrength.INSUFFICIENT_EVIDENCE
    if applied_count >= total_count:
        return EvidenceStrength.STRONG
    if applied_count == 3:
        return EvidenceStrength.MODERATE
    return EvidenceStrength.LIMITED


def calculate_srs_rank_scores(
    raw_scores: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Given raw feature importance scores for p features, compute ranks and normalized rank scores
    according to SRS v9 §2.7:
    
    1. Features ranked 1 (most important) to p (least important) based on |score|.
    2. Ties receive the average rank (e.g., scores [10, 10, 5] -> ranks [1.5, 1.5, 3.0]).
    3. p = 1 edge case: rank = 1.0, normalized rank score = 1.0 (prevents (p-1)=0 division).
    4. p > 1: r_{j,T} = 1.0 - (rank_{j,T} - 1.0) / (p - 1.0).
    5. p = 0: returns empty arrays.
    
    Returns:
        tuple of (ranks, normalized_rank_scores)
    """
    arr = np.asarray(raw_scores, dtype=np.float64)
    p = len(arr)
    if p == 0:
        return np.array([], dtype=np.float64), np.array([], dtype=np.float64)
    if p == 1:
        return np.array([1.0], dtype=np.float64), np.array([1.0], dtype=np.float64)

    # Handle NaNs or Infs gracefully by replacing with 0
    clean_scores = np.nan_to_num(arr, nan=0.0, posinf=0.0, neginf=0.0)
    abs_scores = np.abs(clean_scores)

    # rankdata with negative values assigns rank 1 to the highest score
    # method='average' assigns the average rank to ties
    ranks = rankdata(-abs_scores, method="average").astype(np.float64)

    # r_j,T = 1.0 - (rank_j,T - 1.0) / (p - 1.0)
    normalized_scores = 1.0 - (ranks - 1.0) / (p - 1.0)
    return ranks, normalized_scores.astype(np.float64)


def aggregate_ensemble_scores(
    applied_rank_scores: list[np.ndarray],
    p: int,
) -> np.ndarray:
    """
    Computes EnsembleScore per feature according to SRS §2.7:
    EnsembleScore_j = (1 / T_applied) * sum_{T in Applied} r_{j,T}
    
    If T_applied == 0 or p == 0, returns an array of zeros of length p.
    """
    if p == 0:
        return np.array([], dtype=np.float64)
    t_applied = len(applied_rank_scores)
    if t_applied == 0:
        return np.zeros(p, dtype=np.float64)

    sum_r = np.sum(np.vstack(applied_rank_scores), axis=0)
    ensemble_arr = sum_r / float(t_applied)
    return ensemble_arr.astype(np.float64)


def resolve_top_k(
    p: int,
    alpha: float = 0.25,
    k_min: int = 5,
    k_max: int = 50,
) -> int:
    """
    Resolves integer k for the TOP_K_PERCENT selection rule with k_min and k_max clamps (SRS §2.7, §8).
    
    Formula:
    1. If p <= 0: k = 0
    2. If p == 1: k = 1
    3. k_raw = max(1, int(round(p * alpha)))
    4. k = min(p, max(min(k_min, p), min(k_raw, k_max)))
    
    Guarantees:
    - Lower clamp: When k_raw < k_min, k is clamped up to min(k_min, p).
    - Upper clamp: When k_raw > k_max, k is clamped down to min(k_max, p).
    - Total bounds: 1 <= k <= p (for p >= 1).
    """
    if p <= 0:
        return 0
    if p == 1:
        return 1

    k_raw = max(1, int(round(p * alpha)))
    clamped_k = max(k_min, min(k_raw, k_max))
    return min(clamped_k, p)


def sort_features_with_tie_break(
    feature_names: list[str],
    ensemble_scores: dict[str, float] | np.ndarray,
    rank_sums: dict[str, float] | np.ndarray | None = None,
) -> list[tuple[str, float, float]]:
    """
    Sorts features using the deterministic 3-tier tie-break rule at the K boundary (SRS §2.7):
    1. Higher EnsembleScore descending (-score)
    2. Lower aggregate raw rank sum across applied techniques ascending (+rank_sum)
    3. Lexicographical feature column name ascending (name)
    
    Returns:
        List of (feature_name, ensemble_score, rank_sum) sorted in deterministic order.
    """
    p = len(feature_names)
    if p == 0:
        return []

    if isinstance(ensemble_scores, dict):
        score_arr = np.array([float(ensemble_scores.get(col, 0.0)) for col in feature_names], dtype=np.float64)
    else:
        score_arr = np.asarray(ensemble_scores, dtype=np.float64)

    if rank_sums is None:
        rank_sum_arr = np.zeros(p, dtype=np.float64)
    elif isinstance(rank_sums, dict):
        rank_sum_arr = np.array([float(rank_sums.get(col, 0.0)) for col in feature_names], dtype=np.float64)
    else:
        rank_sum_arr = np.asarray(rank_sums, dtype=np.float64)

    items = [
        (feature_names[i], float(score_arr[i]), float(rank_sum_arr[i]))
        for i in range(p)
    ]
    # 3-tier sort key: (-score, rank_sum, name)
    sorted_items = sorted(items, key=lambda item: (-item[1], item[2], item[0]))
    return sorted_items


def apply_top_k_percent_selection(
    feature_names: list[str],
    scores: dict[str, float] | np.ndarray,
    rank_sums: dict[str, float] | np.ndarray | None = None,
    alpha: float = 0.25,
    k_min: int = 5,
    k_max: int = 50,
    applied_count: int | None = None,
    min_applied_methods: int = 2,
    total_methods: int = 4,
) -> dict[str, Any]:
    """
    Applies TOP_K_PERCENT selection rule on features based on ensemble scores and 3-tier tie-breaking.
    Enforces Evidence Strength invariant:
    - If applied_count < min_applied_methods (e.g. only 1 of 4 applied), evidence strength is
      INSUFFICIENT_EVIDENCE and no feature subset is selected (selected_features = [], k_selected = 0).
    
    Returns:
        dict containing:
        - "selected_features": list of top-k feature names
        - "k_selected": number of selected features
        - "k_raw": unconstrained alpha * p feature count
        - "is_selected_map": dict mapping column name -> bool
        - "sorted_features": list of tuples (col_name, score, rank_sum) sorted descending
        - "evidence_strength": EvidenceStrength value ("STRONG", "MODERATE", "LIMITED", "INSUFFICIENT_EVIDENCE")
    """
    p = len(feature_names)
    effective_applied = applied_count if applied_count is not None else total_methods
    strength = compute_evidence_strength(effective_applied, total_count=total_methods, min_required=min_applied_methods)

    if p == 0:
        return {
            "selected_features": [],
            "k_selected": 0,
            "k_raw": 0,
            "is_selected_map": {},
            "sorted_features": [],
            "evidence_strength": strength.value,
        }

    # If insufficient evidence (< min_applied_methods applied), abort selection: no subset returned!
    if strength == EvidenceStrength.INSUFFICIENT_EVIDENCE:
        sorted_items = sort_features_with_tie_break(feature_names, scores, rank_sums)
        return {
            "selected_features": [],
            "k_selected": 0,
            "k_raw": max(1, int(round(p * alpha))),
            "is_selected_map": {col: False for col in feature_names},
            "sorted_features": sorted_items,
            "evidence_strength": strength.value,
        }

    k_raw = max(1, int(round(p * alpha)))
    k = resolve_top_k(p, alpha=alpha, k_min=k_min, k_max=k_max)

    sorted_items = sort_features_with_tie_break(feature_names, scores, rank_sums)

    selected_features = [item[0] for item in sorted_items[:k]]
    selected_set = set(selected_features)

    is_selected_map = {col: (col in selected_set) for col in feature_names}

    return {
        "selected_features": selected_features,
        "k_selected": k,
        "k_raw": k_raw,
        "is_selected_map": is_selected_map,
        "sorted_features": sorted_items,
        "evidence_strength": strength.value,
    }


@dataclass
class SelectorOutput:
    """
    Structured result payload for a feature selection technique.
    """
    method_name: str
    feature_names: list[str]
    raw_scores: np.ndarray
    ranks: np.ndarray
    rank_scores: np.ndarray
    status: TechniqueStatus = TechniqueStatus.APPLIED
    status_reason: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_feature_map(self) -> dict[str, dict[str, Any]]:
        """
        Formats output as a dictionary mapping feature column name to score breakdown.
        """
        p = len(self.feature_names)
        out: dict[str, dict[str, Any]] = {}
        if self.status == TechniqueStatus.APPLIED and len(self.raw_scores) == p:
            for idx, col in enumerate(self.feature_names):
                out[col] = {
                    "raw_score": float(self.raw_scores[idx]),
                    "rank": float(self.ranks[idx]),
                    "rank_score": float(self.rank_scores[idx]),
                    "status": self.status.value if hasattr(self.status, "value") else str(self.status),
                    "status_reason": None,
                }
        else:
            for col in self.feature_names:
                out[col] = {
                    "raw_score": None,
                    "rank": None,
                    "rank_score": None,
                    "status": self.status.value if hasattr(self.status, "value") else str(self.status),
                    "status_reason": self.status_reason,
                }
        return out


class BaseSelector(ABC):
    """
    Abstract Base Class for feature selection techniques.
    """
    name: str = "base"

    @abstractmethod
    def select(
        self,
        X: np.ndarray | pd.DataFrame,
        y: np.ndarray | pd.Series,
        task_type: str = "REGRESSION",
        feature_names: list[str] | None = None,
        seed: int = 42,
    ) -> SelectorOutput:
        """
        Executes feature scoring and returns a structured SelectorOutput.
        """
        raise NotImplementedError


class CorrelationSelector(BaseSelector):
    """
    CORRELATION_SELECTOR:
    Computes absolute Pearson correlation between each feature column and the target (SRS §2.7).
    - Numeric / Binary / Regression: Absolute Pearson correlation.
    - Multiclass: Mean absolute Pearson correlation against one-hot target classes.
    - Constant / Zero-variance columns: Handled safely with raw score 0.0.
    """
    name: str = FeatureSelectionMethod.CORRELATION.value

    def compute_raw_scores(
        self,
        X: np.ndarray,
        y: np.ndarray,
        task_type: str,
    ) -> np.ndarray:
        n_samples, p = X.shape
        scores = np.zeros(p, dtype=np.float64)

        if n_samples < 2 or p == 0:
            return scores

        y_arr = np.asarray(y)

        if task_type == "CLASSIFICATION" and len(np.unique(y_arr)) > 2:
            # Multiclass: One-hot indicator matrix for classes
            classes = np.unique(y_arr)
            one_hot_y = np.column_stack([(y_arr == c).astype(float) for c in classes])

            for j in range(p):
                col = X[:, j]
                col_std = np.std(col)
                if col_std == 0 or np.isnan(col_std):
                    scores[j] = 0.0
                    continue

                corrs = []
                for k in range(one_hot_y.shape[1]):
                    yk = one_hot_y[:, k]
                    yk_std = np.std(yk)
                    if yk_std == 0 or np.isnan(yk_std):
                        continue
                    r = np.corrcoef(col, yk)[0, 1]
                    if not np.isnan(r):
                        corrs.append(abs(float(r)))
                scores[j] = float(np.mean(corrs)) if corrs else 0.0
        else:
            # Binary classification or numeric regression
            try:
                y_numeric = y_arr.astype(float)
            except (ValueError, TypeError):
                # Categorical string labels for binary classification
                unique_classes = np.unique(y_arr)
                if len(unique_classes) == 2:
                    y_numeric = (y_arr == unique_classes[1]).astype(float)
                else:
                    y_numeric = pd.factorize(y_arr)[0].astype(float)

            y_std = np.std(y_numeric)
            if y_std == 0 or np.isnan(y_std):
                return scores

            for j in range(p):
                col = X[:, j]
                col_std = np.std(col)
                if col_std == 0 or np.isnan(col_std):
                    scores[j] = 0.0
                    continue
                r = np.corrcoef(col, y_numeric)[0, 1]
                scores[j] = abs(float(r)) if not np.isnan(r) else 0.0

        return scores

    def select(
        self,
        X: np.ndarray | pd.DataFrame,
        y: np.ndarray | pd.Series,
        task_type: str = "REGRESSION",
        feature_names: list[str] | None = None,
        seed: int = 42,
    ) -> SelectorOutput:
        if isinstance(X, pd.DataFrame):
            resolved_names = list(X.columns)
            X_arr = X.to_numpy(dtype=np.float64, copy=False)
        else:
            X_arr = np.asarray(X, dtype=np.float64)
            resolved_names = feature_names or [f"feature_{i}" for i in range(X_arr.shape[1] if X_arr.ndim > 1 else len(X_arr))]

        y_arr = y.to_numpy() if isinstance(y, pd.Series) else np.asarray(y)

        p = X_arr.shape[1] if X_arr.ndim > 1 else (len(X_arr) if len(resolved_names) == 1 else 0)
        if X_arr.ndim == 1 and p == 1:
            X_arr = X_arr.reshape(-1, 1)

        if p == 0 or len(X_arr) == 0:
            return SelectorOutput(
                method_name=self.name,
                feature_names=resolved_names,
                raw_scores=np.array([], dtype=np.float64),
                ranks=np.array([], dtype=np.float64),
                rank_scores=np.array([], dtype=np.float64),
                status=TechniqueStatus.SKIPPED,
                status_reason="Empty input data or no feature columns",
            )

        try:
            raw_scores = self.compute_raw_scores(X_arr, y_arr, task_type.upper())
            ranks, rank_scores = calculate_srs_rank_scores(raw_scores)
            return SelectorOutput(
                method_name=self.name,
                feature_names=resolved_names,
                raw_scores=raw_scores,
                ranks=ranks,
                rank_scores=rank_scores,
                status=TechniqueStatus.APPLIED,
                status_reason=None,
            )
        except Exception as e:
            return SelectorOutput(
                method_name=self.name,
                feature_names=resolved_names,
                raw_scores=np.zeros(p, dtype=np.float64),
                ranks=np.zeros(p, dtype=np.float64),
                rank_scores=np.zeros(p, dtype=np.float64),
                status=TechniqueStatus.FAILED,
                status_reason=str(e),
            )


class LassoSelector(BaseSelector):
    """
    LASSO_SELECTOR:
    Computes L1 feature importance = abs(coefficients) (SRS §2.7).
    - Regression: Lasso(alpha=0.01, max_iter=2000, random_state=seed)
    - Classification: LogisticRegression(penalty='l1', solver='liblinear'/'saga', max_iter=1000, random_state=seed, tol=1e-3)
    - Multiclass: Averages absolute coefficients across classes.
    """
    name: str = FeatureSelectionMethod.LASSO.value

    def compute_raw_scores(
        self,
        X: np.ndarray,
        y: np.ndarray,
        task_type: str,
        seed: int = 42,
    ) -> np.ndarray:
        n_samples, p = X.shape
        if p == 0:
            return np.zeros(0, dtype=np.float64)

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            if task_type == "REGRESSION":
                model = Lasso(alpha=0.01, max_iter=2000, random_state=seed)
                model.fit(X, y)
                coefs = np.abs(model.coef_)
                if coefs.ndim == 0:
                    coefs = np.array([float(coefs)])
                return coefs.astype(np.float64)
            else:
                n_classes = len(np.unique(y))
                solver = "liblinear" if n_classes <= 2 else "saga"
                model = LogisticRegression(
                    penalty="l1",
                    solver=solver,
                    max_iter=1000,
                    random_state=seed,
                    tol=1e-3,
                )
                model.fit(X, y)
                coefs = np.abs(model.coef_)
                if coefs.ndim == 2:
                    return np.mean(coefs, axis=0).astype(np.float64)
                return coefs.flatten().astype(np.float64)

    def select(
        self,
        X: np.ndarray | pd.DataFrame,
        y: np.ndarray | pd.Series,
        task_type: str = "REGRESSION",
        feature_names: list[str] | None = None,
        seed: int = 42,
    ) -> SelectorOutput:
        if isinstance(X, pd.DataFrame):
            resolved_names = list(X.columns)
            X_arr = X.to_numpy(dtype=np.float64, copy=False)
        else:
            X_arr = np.asarray(X, dtype=np.float64)
            resolved_names = feature_names or [f"feature_{i}" for i in range(X_arr.shape[1] if X_arr.ndim > 1 else len(X_arr))]

        y_arr = y.to_numpy() if isinstance(y, pd.Series) else np.asarray(y)

        p = X_arr.shape[1] if X_arr.ndim > 1 else (len(X_arr) if len(resolved_names) == 1 else 0)
        if X_arr.ndim == 1 and p == 1:
            X_arr = X_arr.reshape(-1, 1)

        if p == 0 or len(X_arr) == 0:
            return SelectorOutput(
                method_name=self.name,
                feature_names=resolved_names,
                raw_scores=np.array([], dtype=np.float64),
                ranks=np.array([], dtype=np.float64),
                rank_scores=np.array([], dtype=np.float64),
                status=TechniqueStatus.SKIPPED,
                status_reason="Empty input data or no feature columns",
            )

        if len(X_arr) < 2:
            return SelectorOutput(
                method_name=self.name,
                feature_names=resolved_names,
                raw_scores=np.zeros(p, dtype=np.float64),
                ranks=np.zeros(p, dtype=np.float64),
                rank_scores=np.zeros(p, dtype=np.float64),
                status=TechniqueStatus.SKIPPED,
                status_reason="Skipped due to insufficient sample count (< 2)",
            )

        try:
            raw_scores = self.compute_raw_scores(X_arr, y_arr, task_type.upper(), seed=seed)
            ranks, rank_scores = calculate_srs_rank_scores(raw_scores)
            return SelectorOutput(
                method_name=self.name,
                feature_names=resolved_names,
                raw_scores=raw_scores,
                ranks=ranks,
                rank_scores=rank_scores,
                status=TechniqueStatus.APPLIED,
                status_reason=None,
            )
        except Exception as e:
            return SelectorOutput(
                method_name=self.name,
                feature_names=resolved_names,
                raw_scores=np.zeros(p, dtype=np.float64),
                ranks=np.zeros(p, dtype=np.float64),
                rank_scores=np.zeros(p, dtype=np.float64),
                status=TechniqueStatus.FAILED,
                status_reason=str(e),
            )


class RandomForestImportanceSelector(BaseSelector):
    """
    RANDOM_FOREST_IMPORTANCE_SELECTOR:
    Computes Random Forest Gini / Impurity (MDI) feature importances (SRS §2.7).
    - Regression: RandomForestRegressor(n_estimators=50, max_depth=10, random_state=seed, n_jobs=1)
    - Classification: RandomForestClassifier(n_estimators=50, max_depth=10, random_state=seed, n_jobs=1)
    - Full APPLIED / SKIPPED / FAILED status tracking.
    """
    name: str = FeatureSelectionMethod.RANDOM_FOREST.value

    def compute_raw_scores(
        self,
        X: np.ndarray,
        y: np.ndarray,
        task_type: str,
        seed: int = 42,
    ) -> np.ndarray:
        n_samples, p = X.shape
        if p == 0:
            return np.zeros(0, dtype=np.float64)

        if task_type == "REGRESSION":
            rf = RandomForestRegressor(
                n_estimators=50,
                max_depth=10,
                random_state=seed,
                n_jobs=1,
            )
        else:
            rf = RandomForestClassifier(
                n_estimators=50,
                max_depth=10,
                random_state=seed,
                n_jobs=1,
            )

        rf.fit(X, y)
        return rf.feature_importances_.astype(np.float64)

    def select(
        self,
        X: np.ndarray | pd.DataFrame,
        y: np.ndarray | pd.Series,
        task_type: str = "REGRESSION",
        feature_names: list[str] | None = None,
        seed: int = 42,
    ) -> SelectorOutput:
        if isinstance(X, pd.DataFrame):
            resolved_names = list(X.columns)
            X_arr = X.to_numpy(dtype=np.float64, copy=False)
        else:
            X_arr = np.asarray(X, dtype=np.float64)
            resolved_names = feature_names or [f"feature_{i}" for i in range(X_arr.shape[1] if X_arr.ndim > 1 else len(X_arr))]

        y_arr = y.to_numpy() if isinstance(y, pd.Series) else np.asarray(y)

        p = X_arr.shape[1] if X_arr.ndim > 1 else (len(X_arr) if len(resolved_names) == 1 else 0)
        if X_arr.ndim == 1 and p == 1:
            X_arr = X_arr.reshape(-1, 1)

        if p == 0 or len(X_arr) == 0:
            return SelectorOutput(
                method_name=self.name,
                feature_names=resolved_names,
                raw_scores=np.array([], dtype=np.float64),
                ranks=np.array([], dtype=np.float64),
                rank_scores=np.array([], dtype=np.float64),
                status=TechniqueStatus.SKIPPED,
                status_reason="Empty input data or no feature columns",
            )

        if len(X_arr) < 2:
            return SelectorOutput(
                method_name=self.name,
                feature_names=resolved_names,
                raw_scores=np.zeros(p, dtype=np.float64),
                ranks=np.zeros(p, dtype=np.float64),
                rank_scores=np.zeros(p, dtype=np.float64),
                status=TechniqueStatus.SKIPPED,
                status_reason="Skipped due to insufficient sample count (< 2)",
            )

        try:
            raw_scores = self.compute_raw_scores(X_arr, y_arr, task_type.upper(), seed=seed)
            ranks, rank_scores = calculate_srs_rank_scores(raw_scores)
            return SelectorOutput(
                method_name=self.name,
                feature_names=resolved_names,
                raw_scores=raw_scores,
                ranks=ranks,
                rank_scores=rank_scores,
                status=TechniqueStatus.APPLIED,
                status_reason=None,
            )
        except Exception as e:
            return SelectorOutput(
                method_name=self.name,
                feature_names=resolved_names,
                raw_scores=np.zeros(p, dtype=np.float64),
                ranks=np.zeros(p, dtype=np.float64),
                rank_scores=np.zeros(p, dtype=np.float64),
                status=TechniqueStatus.FAILED,
                status_reason=str(e),
            )


class PermutationImportanceSelector(BaseSelector):
    """
    PERMUTATION_IMPORTANCE_SELECTOR:
    Computes Permutation Feature Importance using a fast baseline estimator (SRS §2.7).
    - Regression: Ridge(alpha=1.0, random_state=seed) + permutation_importance(n_repeats=5, random_state=seed, n_jobs=1)
    - Classification: LogisticRegression(max_iter=500, random_state=seed, tol=1e-3) + permutation_importance
    - Full APPLIED / SKIPPED / FAILED status tracking.
    """
    name: str = FeatureSelectionMethod.PERMUTATION.value

    def compute_raw_scores(
        self,
        X: np.ndarray,
        y: np.ndarray,
        task_type: str,
        seed: int = 42,
    ) -> np.ndarray:
        n_samples, p = X.shape
        if p == 0:
            return np.zeros(0, dtype=np.float64)

        if task_type == "REGRESSION":
            estimator = Ridge(alpha=1.0, random_state=seed)
        else:
            estimator = LogisticRegression(
                max_iter=500,
                random_state=seed,
                tol=1e-3,
            )

        estimator.fit(X, y)
        res = permutation_importance(
            estimator,
            X,
            y,
            n_repeats=5,
            random_state=seed,
            n_jobs=1,
        )
        scores = np.maximum(0.0, res.importances_mean)
        return scores.astype(np.float64)

    def select(
        self,
        X: np.ndarray | pd.DataFrame,
        y: np.ndarray | pd.Series,
        task_type: str = "REGRESSION",
        feature_names: list[str] | None = None,
        seed: int = 42,
    ) -> SelectorOutput:
        if isinstance(X, pd.DataFrame):
            resolved_names = list(X.columns)
            X_arr = X.to_numpy(dtype=np.float64, copy=False)
        else:
            X_arr = np.asarray(X, dtype=np.float64)
            resolved_names = feature_names or [f"feature_{i}" for i in range(X_arr.shape[1] if X_arr.ndim > 1 else len(X_arr))]

        y_arr = y.to_numpy() if isinstance(y, pd.Series) else np.asarray(y)

        p = X_arr.shape[1] if X_arr.ndim > 1 else (len(X_arr) if len(resolved_names) == 1 else 0)
        if X_arr.ndim == 1 and p == 1:
            X_arr = X_arr.reshape(-1, 1)

        if p == 0 or len(X_arr) == 0:
            return SelectorOutput(
                method_name=self.name,
                feature_names=resolved_names,
                raw_scores=np.array([], dtype=np.float64),
                ranks=np.array([], dtype=np.float64),
                rank_scores=np.array([], dtype=np.float64),
                status=TechniqueStatus.SKIPPED,
                status_reason="Empty input data or no feature columns",
            )

        if len(X_arr) < 2:
            return SelectorOutput(
                method_name=self.name,
                feature_names=resolved_names,
                raw_scores=np.zeros(p, dtype=np.float64),
                ranks=np.zeros(p, dtype=np.float64),
                rank_scores=np.zeros(p, dtype=np.float64),
                status=TechniqueStatus.SKIPPED,
                status_reason="Skipped due to insufficient sample count (< 2)",
            )

        try:
            raw_scores = self.compute_raw_scores(X_arr, y_arr, task_type.upper(), seed=seed)
            ranks, rank_scores = calculate_srs_rank_scores(raw_scores)
            return SelectorOutput(
                method_name=self.name,
                feature_names=resolved_names,
                raw_scores=raw_scores,
                ranks=ranks,
                rank_scores=rank_scores,
                status=TechniqueStatus.APPLIED,
                status_reason=None,
            )
        except Exception as e:
            return SelectorOutput(
                method_name=self.name,
                feature_names=resolved_names,
                raw_scores=np.zeros(p, dtype=np.float64),
                ranks=np.zeros(p, dtype=np.float64),
                rank_scores=np.zeros(p, dtype=np.float64),
                status=TechniqueStatus.FAILED,
                status_reason=str(e),
            )


# Canonical Singletons / Selector Constants (§2.7, §8)
CORRELATION_SELECTOR = CorrelationSelector()
LASSO_SELECTOR = LassoSelector()
RANDOM_FOREST_IMPORTANCE_SELECTOR = RandomForestImportanceSelector()
PERMUTATION_IMPORTANCE_SELECTOR = PermutationImportanceSelector()
