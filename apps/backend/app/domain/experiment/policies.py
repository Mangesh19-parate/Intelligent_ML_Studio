"""
Domain Validation Policies and Invariants for Experiments.
"""

from typing import Any
from app.domain.experiment.state import ExperimentState, VALID_EXPERIMENT_TRANSITIONS


class DomainValidationError(ValueError):
    """Raised when a business domain rule is violated."""
    pass


def validate_cv_folds(folds: int) -> int:
    """Ensures cross-validation fold count satisfies statistical stability requirements (2 <= k <= 20)."""
    if not isinstance(folds, int) or folds < 2 or folds > 20:
        raise DomainValidationError(f"Invalid fold count: {folds}. Cross-validation requires between 2 and 20 folds.")
    return folds


def validate_metric_direction(metric_name: str, direction: str | None = None) -> str:
    """
    Infers or validates canonical optimization direction for metrics.
    """
    loss_metrics = {"rmse", "mae", "mse", "log_loss", "brier_score"}
    score_metrics = {"accuracy", "f1", "macro_f1", "weighted_f1", "r2", "adjusted_r2", "roc_auc", "precision", "recall"}
    
    clean_metric = metric_name.lower().strip()
    if direction:
        clean_dir = direction.upper().strip()
        if clean_dir not in {"MINIMIZE", "MAXIMIZE"}:
            raise DomainValidationError(f"Invalid optimization direction '{direction}'. Must be MINIMIZE or MAXIMIZE.")
        return clean_dir

    if clean_metric in loss_metrics:
        return "MINIMIZE"
    return "MAXIMIZE"


def validate_transition(current_state: str | ExperimentState, target_state: str | ExperimentState) -> None:
    """Validates that a lifecycle state transition is legally permissible."""
    curr_enum = ExperimentState(current_state) if isinstance(current_state, str) else current_state
    target_enum = ExperimentState(target_state) if isinstance(target_state, str) else target_state

    valid_targets = VALID_EXPERIMENT_TRANSITIONS.get(curr_enum, set())
    if target_enum not in valid_targets and curr_enum != target_enum:
        raise DomainValidationError(
            f"Illegal state transition from {curr_enum.value} to {target_enum.value}."
        )
