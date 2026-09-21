"""
Domain Experiment State Machine & Lifecycle Policies.
"""

from enum import Enum


class ExperimentState(str, Enum):
    DRAFT = "DRAFT"
    QUEUED = "QUEUED"
    SPLITTING = "SPLITTING"
    PROFILING = "PROFILING"
    FEATURE_SELECTION = "FEATURE_SELECTION"
    TRAINING = "TRAINING"
    EVALUATING = "EVALUATING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    TRAINING_FAILED = "TRAINING_FAILED"


class ModelState(str, Enum):
    UNTRAINED = "UNTRAINED"
    TRAINING = "TRAINING"
    TRAINED = "TRAINED"
    EVALUATED = "EVALUATED"
    SELECTED_FOR_DEPLOYMENT = "SELECTED_FOR_DEPLOYMENT"
    REJECTED = "REJECTED"
    FAILED = "FAILED"


VALID_EXPERIMENT_TRANSITIONS: dict[ExperimentState, set[ExperimentState]] = {
    ExperimentState.DRAFT: {ExperimentState.QUEUED, ExperimentState.CANCELLED},
    ExperimentState.QUEUED: {ExperimentState.SPLITTING, ExperimentState.TRAINING, ExperimentState.CANCELLED, ExperimentState.FAILED},
    ExperimentState.SPLITTING: {ExperimentState.PROFILING, ExperimentState.FEATURE_SELECTION, ExperimentState.TRAINING, ExperimentState.FAILED},
    ExperimentState.PROFILING: {ExperimentState.FEATURE_SELECTION, ExperimentState.TRAINING, ExperimentState.FAILED},
    ExperimentState.FEATURE_SELECTION: {ExperimentState.TRAINING, ExperimentState.FAILED},
    ExperimentState.TRAINING: {ExperimentState.EVALUATING, ExperimentState.COMPLETED, ExperimentState.FAILED, ExperimentState.TRAINING_FAILED},
    ExperimentState.EVALUATING: {ExperimentState.COMPLETED, ExperimentState.FAILED},
    ExperimentState.COMPLETED: set(),
    ExperimentState.FAILED: {ExperimentState.QUEUED},
    ExperimentState.TRAINING_FAILED: {ExperimentState.QUEUED},
    ExperimentState.CANCELLED: set(),
}
