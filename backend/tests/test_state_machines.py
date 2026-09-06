"""
Unit tests for ML Studio Entity State Machines.
Validates the four decoupled state machines (ProjectState, ExperimentState, ModelState, DeploymentState),
their canonical members, valid transitions, side-state retry pathways, and invalid transition handling.
"""

import pytest
from app.config.state_machines import (
    ProjectState,
    PROJECT_VALID_TRANSITIONS,
    ExperimentState,
    EXPERIMENT_VALID_TRANSITIONS,
    ModelState,
    MODEL_VALID_TRANSITIONS,
    DeploymentState,
    DEPLOYMENT_VALID_TRANSITIONS,
    InvalidStateTransitionError,
    can_transition,
    validate_transition,
    get_valid_transitions,
)


# ============================================================================
# 1. ENUM INTEGRITY & MEMBERSHIP TESTS
# ============================================================================

def test_project_state_members():
    """Verify all canonical ProjectState enum values."""
    expected = {
        "DATA", "SPLIT", "PROFILED", "TRANSFORMED", "FEATURE_SELECTED",
        "TRAINING", "TRAINED", "EVALUATED", "GATE_PASSED", "DEPLOYED", "ARCHIVED"
    }
    actual = {s.value for s in ProjectState}
    assert actual == expected
    assert len(PROJECT_VALID_TRANSITIONS) == len(ProjectState)


def test_experiment_state_members():
    """Verify all canonical ExperimentState enum values including side-states."""
    expected = {
        "CREATED", "CONFIGURED", "TRAINING", "EVALUATED",
        "TEST_CONSUMED", "REGISTERED", "TRAINING_FAILED", "ARTIFACT_WRITE_FAILED"
    }
    actual = {s.value for s in ExperimentState}
    assert actual == expected
    assert len(EXPERIMENT_VALID_TRANSITIONS) == len(ExperimentState)


def test_model_state_members():
    """Verify all canonical ModelState enum values."""
    expected = {"TRAINED", "ARTIFACT_VERIFIED", "DEPLOYABLE", "ARTIFACT_INVALID"}
    actual = {s.value for s in ModelState}
    assert actual == expected
    assert len(MODEL_VALID_TRANSITIONS) == len(ModelState)


def test_deployment_state_members():
    """Verify all canonical DeploymentState enum values."""
    expected = {
        "CREATED", "GATE_PENDING", "GATE_PASSED", "GATE_BLOCKED",
        "APPROVED", "DEPLOYED", "PAUSED", "RETIRED"
    }
    actual = {s.value for s in DeploymentState}
    assert actual == expected
    assert len(DEPLOYMENT_VALID_TRANSITIONS) == len(DeploymentState)


# ============================================================================
# 2. EXPERIMENT STATE TRANSITION & RETRY TESTS
# ============================================================================

def test_experiment_happy_path_progression():
    """Verify standard linear flow: CREATED -> CONFIGURED -> TRAINING -> EVALUATED -> TEST_CONSUMED -> REGISTERED."""
    flow = [
        ExperimentState.CREATED,
        ExperimentState.CONFIGURED,
        ExperimentState.TRAINING,
        ExperimentState.EVALUATED,
        ExperimentState.TEST_CONSUMED,
        ExperimentState.REGISTERED,
    ]
    for i in range(len(flow) - 1):
        curr_state = flow[i]
        next_state = flow[i + 1]
        assert can_transition(curr_state, next_state) is True
        validate_transition(curr_state, next_state)  # Should not raise


def test_experiment_training_failure_and_retry():
    """Verify TRAINING -> TRAINING_FAILED -> TRAINING retry flow."""
    assert can_transition(ExperimentState.TRAINING, ExperimentState.TRAINING_FAILED) is True
    assert can_transition(ExperimentState.TRAINING_FAILED, ExperimentState.TRAINING) is True
    assert can_transition(ExperimentState.TRAINING_FAILED, ExperimentState.CONFIGURED) is True
    
    # Cannot skip directly to REGISTERED from TRAINING_FAILED
    assert can_transition(ExperimentState.TRAINING_FAILED, ExperimentState.REGISTERED) is False
    with pytest.raises(InvalidStateTransitionError):
        validate_transition(ExperimentState.TRAINING_FAILED, ExperimentState.REGISTERED)


def test_experiment_artifact_write_failure_and_retry():
    """Verify EVALUATED/TEST_CONSUMED -> ARTIFACT_WRITE_FAILED -> recovery."""
    assert can_transition(ExperimentState.EVALUATED, ExperimentState.ARTIFACT_WRITE_FAILED) is True
    assert can_transition(ExperimentState.TEST_CONSUMED, ExperimentState.ARTIFACT_WRITE_FAILED) is True
    assert can_transition(ExperimentState.ARTIFACT_WRITE_FAILED, ExperimentState.REGISTERED) is True


def test_experiment_registered_is_terminal():
    """Verify REGISTERED state allows no forward transitions."""
    assert get_valid_transitions(ExperimentState.REGISTERED) == []
    assert can_transition(ExperimentState.REGISTERED, ExperimentState.CREATED) is False


# ============================================================================
# 3. MODEL STATE TRANSITION TESTS
# ============================================================================

def test_model_happy_path_and_invalid_artifacts():
    """Verify ModelState transitions and artifact invalidation/retry."""
    assert can_transition(ModelState.TRAINED, ModelState.ARTIFACT_VERIFIED) is True
    assert can_transition(ModelState.ARTIFACT_VERIFIED, ModelState.DEPLOYABLE) is True
    
    # Invalidation transitions
    assert can_transition(ModelState.TRAINED, ModelState.ARTIFACT_INVALID) is True
    assert can_transition(ModelState.ARTIFACT_VERIFIED, ModelState.ARTIFACT_INVALID) is True
    assert can_transition(ModelState.ARTIFACT_INVALID, ModelState.TRAINED) is True

    # Cannot skip from TRAINED directly to DEPLOYABLE without verification
    assert can_transition(ModelState.TRAINED, ModelState.DEPLOYABLE) is False
    with pytest.raises(InvalidStateTransitionError):
        validate_transition(ModelState.TRAINED, ModelState.DEPLOYABLE)


# ============================================================================
# 4. DEPLOYMENT STATE TRANSITION TESTS
# ============================================================================

def test_deployment_gate_and_lifecycle():
    """Verify DeploymentState gate blocking, approval, pause/resume and retirement."""
    # Gate blocking and unblocking
    assert can_transition(DeploymentState.CREATED, DeploymentState.GATE_PENDING) is True
    assert can_transition(DeploymentState.GATE_PENDING, DeploymentState.GATE_BLOCKED) is True
    assert can_transition(DeploymentState.GATE_BLOCKED, DeploymentState.GATE_PENDING) is True
    assert can_transition(DeploymentState.GATE_BLOCKED, DeploymentState.RETIRED) is True

    # Gate passed to deployment
    assert can_transition(DeploymentState.GATE_PENDING, DeploymentState.GATE_PASSED) is True
    assert can_transition(DeploymentState.GATE_PASSED, DeploymentState.APPROVED) is True
    assert can_transition(DeploymentState.APPROVED, DeploymentState.DEPLOYED) is True

    # Pause and resume
    assert can_transition(DeploymentState.DEPLOYED, DeploymentState.PAUSED) is True
    assert can_transition(DeploymentState.PAUSED, DeploymentState.DEPLOYED) is True
    assert can_transition(DeploymentState.PAUSED, DeploymentState.RETIRED) is True


# ============================================================================
# 5. CROSS-MACHINE ISOLATION TESTS
# ============================================================================

def test_cross_machine_transitions_prohibited():
    """Verify transitions between completely different state machine enums are rejected."""
    assert can_transition(ProjectState.DATA, ExperimentState.CREATED) is False
    with pytest.raises(InvalidStateTransitionError) as exc_info:
        validate_transition(ProjectState.DATA, ExperimentState.CREATED)
    assert "Invalid transition for ProjectState" in str(exc_info.value)
