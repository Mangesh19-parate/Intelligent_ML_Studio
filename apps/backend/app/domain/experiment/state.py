"""
Domain Experiment State Machine & Lifecycle Policies.
Authoritative contract re-exported from app.config.state_machines.
"""

from app.config.state_machines import (
    ExperimentState,
    ModelState,
    ProjectState,
    DeploymentState,
    EXPERIMENT_VALID_TRANSITIONS,
    MODEL_VALID_TRANSITIONS,
    PROJECT_VALID_TRANSITIONS,
    DEPLOYMENT_VALID_TRANSITIONS,
    validate_transition,
    InvalidStateTransitionError,
)

# Alias for compatibility
VALID_EXPERIMENT_TRANSITIONS = {k: set(v) for k, v in EXPERIMENT_VALID_TRANSITIONS.items()}

__all__ = [
    "ExperimentState",
    "ModelState",
    "ProjectState",
    "DeploymentState",
    "EXPERIMENT_VALID_TRANSITIONS",
    "MODEL_VALID_TRANSITIONS",
    "PROJECT_VALID_TRANSITIONS",
    "DEPLOYMENT_VALID_TRANSITIONS",
    "VALID_EXPERIMENT_TRANSITIONS",
    "validate_transition",
    "InvalidStateTransitionError",
]

