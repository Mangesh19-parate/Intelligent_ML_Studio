"""
ML Studio — Entity State Machines (Frozen)
Reference: Software Requirements Specification (SRS) v4 / Architectural Contract §2 & §8

This module defines four strictly decoupled entity state machine enums, their canonical
member names, and their authoritative VALID_TRANSITIONS maps:

1. ProjectState: Macro-lifecycle of a machine learning workbench project.
2. ExperimentState: Lifecycle of an experiment run (CREATED -> CONFIGURED -> TRAINING ->
   EVALUATED -> TEST_CONSUMED -> REGISTERED, plus TRAINING_FAILED and ARTIFACT_WRITE_FAILED
   side-states with retry transitions).
3. ModelState: Integrity and deployment-readiness of a trained model artifact
   (TRAINED -> ARTIFACT_VERIFIED -> DEPLOYABLE, plus ARTIFACT_INVALID).
4. DeploymentState: Real-time serving endpoint lifecycle
   (CREATED -> GATE_PENDING -> GATE_PASSED | GATE_BLOCKED -> APPROVED -> DEPLOYED ->
   PAUSED -> RETIRED).

CRITICAL ARCHITECTURAL INVARIANT:
These are four independent columns on four different database tables (projects, experiments,
trained_models, deployments) — never a single shared status field.
"""

from __future__ import annotations

from enum import Enum
from typing import Dict, List, Set, Type, TypeVar, Union


class InvalidStateTransitionError(ValueError):
    """Raised when an illegal state machine transition is attempted."""

    def __init__(self, machine_name: str, current_state: str, target_state: str, allowed_states: List[str]):
        super().__init__(
            f"Invalid transition for {machine_name}: cannot transition from '{current_state}' to '{target_state}'. "
            f"Allowed target states from '{current_state}' are: {allowed_states or 'None (terminal state)'}."
        )
        self.machine_name = machine_name
        self.current_state = current_state
        self.target_state = target_state
        self.allowed_states = allowed_states


# ============================================================================
# 1. PROJECT STATE MACHINE (Table: projects.pipeline_stage)
# ============================================================================

class ProjectState(str, Enum):
    """
    Project macro-lifecycle stages.
    Tracks progression through the end-to-end workbench lifecycle.
    """
    DATA = "DATA"
    SPLIT = "SPLIT"
    PROFILED = "PROFILED"
    TRANSFORMED = "TRANSFORMED"
    FEATURE_SELECTED = "FEATURE_SELECTED"
    TRAINING = "TRAINING"
    TRAINED = "TRAINED"
    EVALUATED = "EVALUATED"
    GATE_PASSED = "GATE_PASSED"
    DEPLOYED = "DEPLOYED"
    ARCHIVED = "ARCHIVED"


PROJECT_VALID_TRANSITIONS: Dict[ProjectState, List[ProjectState]] = {
    ProjectState.DATA: [ProjectState.SPLIT, ProjectState.ARCHIVED],
    ProjectState.SPLIT: [ProjectState.PROFILED, ProjectState.TRANSFORMED, ProjectState.DATA, ProjectState.ARCHIVED],
    ProjectState.PROFILED: [ProjectState.TRANSFORMED, ProjectState.SPLIT, ProjectState.ARCHIVED],
    ProjectState.TRANSFORMED: [ProjectState.FEATURE_SELECTED, ProjectState.TRAINING, ProjectState.PROFILED, ProjectState.ARCHIVED],
    ProjectState.FEATURE_SELECTED: [ProjectState.TRAINING, ProjectState.TRANSFORMED, ProjectState.ARCHIVED],
    ProjectState.TRAINING: [ProjectState.TRAINED, ProjectState.FEATURE_SELECTED, ProjectState.TRANSFORMED, ProjectState.ARCHIVED],
    ProjectState.TRAINED: [ProjectState.EVALUATED, ProjectState.TRAINING, ProjectState.ARCHIVED],
    ProjectState.EVALUATED: [ProjectState.GATE_PASSED, ProjectState.TRAINING, ProjectState.ARCHIVED],
    ProjectState.GATE_PASSED: [ProjectState.DEPLOYED, ProjectState.TRAINING, ProjectState.ARCHIVED],
    ProjectState.DEPLOYED: [ProjectState.GATE_PASSED, ProjectState.ARCHIVED],
    ProjectState.ARCHIVED: [ProjectState.DATA],  # Reactivation pathway
}


# ============================================================================
# 2. EXPERIMENT STATE MACHINE (Table: experiments.status)
# ============================================================================

class ExperimentState(str, Enum):
    """
    Experiment run lifecycle.
    Governs creation, configuration freezing, inner CV fold training,
    Locked Test consumption, registry storage, and error recovery.
    """
    CREATED = "CREATED"
    CONFIGURED = "CONFIGURED"
    TRAINING = "TRAINING"
    EVALUATED = "EVALUATED"
    TEST_CONSUMED = "TEST_CONSUMED"
    REGISTERED = "REGISTERED"
    TRAINING_FAILED = "TRAINING_FAILED"
    ARTIFACT_WRITE_FAILED = "ARTIFACT_WRITE_FAILED"


EXPERIMENT_VALID_TRANSITIONS: Dict[ExperimentState, List[ExperimentState]] = {
    ExperimentState.CREATED: [
        ExperimentState.CONFIGURED,
    ],
    ExperimentState.CONFIGURED: [
        ExperimentState.TRAINING,
    ],
    ExperimentState.TRAINING: [
        ExperimentState.EVALUATED,
        ExperimentState.TRAINING_FAILED,
    ],
    ExperimentState.EVALUATED: [
        ExperimentState.TEST_CONSUMED,
        ExperimentState.ARTIFACT_WRITE_FAILED,
    ],
    ExperimentState.TEST_CONSUMED: [
        ExperimentState.REGISTERED,
        ExperimentState.ARTIFACT_WRITE_FAILED,
    ],
    ExperimentState.TRAINING_FAILED: [
        ExperimentState.TRAINING,    # Retry training execution
        ExperimentState.CONFIGURED,  # Reconfigure parameters
    ],
    ExperimentState.ARTIFACT_WRITE_FAILED: [
        ExperimentState.EVALUATED,     # Retry evaluation packaging
        ExperimentState.TEST_CONSUMED, # Retry locked test bundle
        ExperimentState.REGISTERED,    # Retry catalog registration
    ],
    ExperimentState.REGISTERED: [],  # Terminal state
}


# ============================================================================
# 3. MODEL STATE MACHINE (Table: trained_models.status)
# ============================================================================

class ModelState(str, Enum):
    """
    Trained model artifact verification and readiness lifecycle.
    Tracks fitted pipeline binary verification against SHA-256 checksums.
    """
    TRAINED = "TRAINED"
    ARTIFACT_VERIFIED = "ARTIFACT_VERIFIED"
    DEPLOYABLE = "DEPLOYABLE"
    ARTIFACT_INVALID = "ARTIFACT_INVALID"


MODEL_VALID_TRANSITIONS: Dict[ModelState, List[ModelState]] = {
    ModelState.TRAINED: [
        ModelState.ARTIFACT_VERIFIED,
        ModelState.ARTIFACT_INVALID,
    ],
    ModelState.ARTIFACT_VERIFIED: [
        ModelState.DEPLOYABLE,
        ModelState.ARTIFACT_INVALID,
    ],
    ModelState.ARTIFACT_INVALID: [
        ModelState.TRAINED,  # Retry / re-package artifact
    ],
    ModelState.DEPLOYABLE: [],  # Terminal readiness state
}


# ============================================================================
# 4. DEPLOYMENT STATE MACHINE (Table: deployments.status)
# ============================================================================

class DeploymentState(str, Enum):
    """
    Real-time serving endpoint lifecycle.
    Governs gate verification, stakeholder approval, active traffic serving,
    pausing, and decommissioning.
    """
    CREATED = "CREATED"
    GATE_PENDING = "GATE_PENDING"
    GATE_PASSED = "GATE_PASSED"
    GATE_BLOCKED = "GATE_BLOCKED"
    APPROVED = "APPROVED"
    DEPLOYED = "DEPLOYED"
    PAUSED = "PAUSED"
    RETIRED = "RETIRED"


DEPLOYMENT_VALID_TRANSITIONS: Dict[DeploymentState, List[DeploymentState]] = {
    DeploymentState.CREATED: [
        DeploymentState.GATE_PENDING,
    ],
    DeploymentState.GATE_PENDING: [
        DeploymentState.GATE_PASSED,
        DeploymentState.GATE_BLOCKED,
    ],
    DeploymentState.GATE_BLOCKED: [
        DeploymentState.GATE_PENDING,  # Re-evaluate gate conditions
        DeploymentState.RETIRED,       # Reject / dismiss deployment
    ],
    DeploymentState.GATE_PASSED: [
        DeploymentState.APPROVED,
        DeploymentState.GATE_BLOCKED,  # Invalidation if gate criteria regressed
    ],
    DeploymentState.APPROVED: [
        DeploymentState.DEPLOYED,
        DeploymentState.RETIRED,
    ],
    DeploymentState.DEPLOYED: [
        DeploymentState.PAUSED,
        DeploymentState.RETIRED,
    ],
    DeploymentState.PAUSED: [
        DeploymentState.DEPLOYED,  # Resume serving
        DeploymentState.RETIRED,   # Decommission
    ],
    DeploymentState.RETIRED: [],  # Terminal state
}


# ============================================================================
# 5. TRANSITION VALIDATION UTILITIES
# ============================================================================

StateMachineEnumType = Union[ProjectState, ExperimentState, ModelState, DeploymentState]

STATE_MACHINE_REGISTRY: Dict[Type[Enum], Dict[Any, List[Any]]] = {
    ProjectState: PROJECT_VALID_TRANSITIONS,
    ExperimentState: EXPERIMENT_VALID_TRANSITIONS,
    ModelState: MODEL_VALID_TRANSITIONS,
    DeploymentState: DEPLOYMENT_VALID_TRANSITIONS,
}


def get_valid_transitions(current_state: StateMachineEnumType) -> List[StateMachineEnumType]:
    """Returns the list of valid next states from the given current state."""
    state_cls = type(current_state)
    if state_cls not in STATE_MACHINE_REGISTRY:
        raise ValueError(f"Unknown state machine type: {state_cls.__name__}")
    transitions = STATE_MACHINE_REGISTRY[state_cls]
    return transitions.get(current_state, [])


def can_transition(
    current_state: StateMachineEnumType,
    target_state: StateMachineEnumType,
) -> bool:
    """
    Checks whether a state machine transition is permissible.

    Returns:
        True if transition is allowed, False otherwise.
    """
    if type(current_state) is not type(target_state):
        return False
    valid_targets = get_valid_transitions(current_state)
    return target_state in valid_targets


def validate_transition(
    current_state: StateMachineEnumType,
    target_state: StateMachineEnumType,
) -> None:
    """
    Validates a state machine transition, raising InvalidStateTransitionError if illegal.

    Raises:
        InvalidStateTransitionError: If the transition is not allowed.
    """
    state_cls = type(current_state)
    machine_name = state_cls.__name__
    
    if type(current_state) is not type(target_state):
        raise InvalidStateTransitionError(
            machine_name=machine_name,
            current_state=str(current_state.value),
            target_state=str(target_state.value if hasattr(target_state, "value") else target_state),
            allowed_states=[s.value for s in get_valid_transitions(current_state)],
        )

    valid_targets = get_valid_transitions(current_state)
    if target_state not in valid_targets:
        raise InvalidStateTransitionError(
            machine_name=machine_name,
            current_state=current_state.value,
            target_state=target_state.value,
            allowed_states=[s.value for s in valid_targets],
        )
