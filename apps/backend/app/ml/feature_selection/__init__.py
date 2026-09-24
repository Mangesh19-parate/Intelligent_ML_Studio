"""
ML Feature Selection Module.
Implements the 4-technique Rank-Aggregation Feature Selection Ensemble (SRS §2.7).
"""

from app.services.selectors import (
    calculate_srs_rank_scores,
    aggregate_ensemble_scores,
    resolve_top_k,
    apply_top_k_percent_selection,
    CORRELATION_SELECTOR,
    LASSO_SELECTOR,
    RANDOM_FOREST_IMPORTANCE_SELECTOR,
    PERMUTATION_IMPORTANCE_SELECTOR,
    CorrelationSelector,
    LassoSelector,
    RandomForestImportanceSelector,
    PermutationImportanceSelector,
)

__all__ = [
    "calculate_srs_rank_scores",
    "aggregate_ensemble_scores",
    "resolve_top_k",
    "apply_top_k_percent_selection",
    "CORRELATION_SELECTOR",
    "LASSO_SELECTOR",
    "RANDOM_FOREST_IMPORTANCE_SELECTOR",
    "PERMUTATION_IMPORTANCE_SELECTOR",
    "CorrelationSelector",
    "LassoSelector",
    "RandomForestImportanceSelector",
    "PermutationImportanceSelector",
]
