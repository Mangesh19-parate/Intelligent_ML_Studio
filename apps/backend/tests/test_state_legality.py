"""
Unit Tests for Cross-Entity State Legality (SRS v9 §2 / Day 2).

CRITICAL ARCHITECTURAL BOUNDARY:
This test suite verifies pure cross-entity STATE-LEGALITY:
- Can a Deployment legally transition to APPROVED given:
    - deployment.status == GATE_PASSED
    - model.status == DEPLOYABLE
    - experiment.status == REGISTERED
- This test MUST NOT check the six substantive gate conditions (locked_test_evaluated,
  schema_locked, artifact_verified, lineage_complete, performance_threshold_passed, user_approved).
  That logic belongs entirely to the gate service and is tested separately.
"""

import pytest
from app.config.state_machines import (
    DeploymentState,
    ModelState,
    ExperimentState,
    ProjectState,
    can_transition,
    validate_transition,
    check_deployment_approval_state_legality,
    validate_deployment_approval_state_legality,
    InvalidStateTransitionError,
)


def test_legal_deployment_approval_triplet():
    """
    Verify that the canonical legal triplet:
    (Deployment: GATE_PASSED, Model: DEPLOYABLE, Experiment: REGISTERED)
    is approved as state-legal.
    """
    # Using Enum instances
    is_legal = check_deployment_approval_state_legality(
        deployment_current_state=DeploymentState.GATE_PASSED,
        model_state=ModelState.DEPLOYABLE,
        experiment_state=ExperimentState.REGISTERED,
    )
    assert is_legal is True

    # validate_deployment_approval_state_legality does not raise
    validate_deployment_approval_state_legality(
        deployment_current_state=DeploymentState.GATE_PASSED,
        model_state=ModelState.DEPLOYABLE,
        experiment_state=ExperimentState.REGISTERED,
    )

    # Also test case-insensitive string resolution
    assert check_deployment_approval_state_legality("GATE_PASSED", "DEPLOYABLE", "REGISTERED") is True
    validate_deployment_approval_state_legality("gate_passed", "deployable", "registered")


@pytest.mark.parametrize(
    "invalid_model_state",
    [
        ModelState.TRAINED,
        ModelState.ARTIFACT_VERIFIED,
        ModelState.ARTIFACT_INVALID,
        "TRAINED",
        "ARTIFACT_VERIFIED",
        "ARTIFACT_INVALID",
    ],
)
def test_rejection_when_model_is_not_deployable(invalid_model_state):
    """
    Even if Deployment is GATE_PASSED and Experiment is REGISTERED,
    if Model is not DEPLOYABLE, approval is illegal.
    """
    assert (
        check_deployment_approval_state_legality(
            deployment_current_state=DeploymentState.GATE_PASSED,
            model_state=invalid_model_state,
            experiment_state=ExperimentState.REGISTERED,
        )
        is False
    )

    with pytest.raises(InvalidStateTransitionError) as exc_info:
        validate_deployment_approval_state_legality(
            deployment_current_state=DeploymentState.GATE_PASSED,
            model_state=invalid_model_state,
            experiment_state=ExperimentState.REGISTERED,
        )
    assert "DEPLOYABLE" in str(exc_info.value)


@pytest.mark.parametrize(
    "invalid_experiment_state",
    [
        ExperimentState.CREATED,
        ExperimentState.CONFIGURED,
        ExperimentState.TRAINING,
        ExperimentState.EVALUATED,
        ExperimentState.TEST_CONSUMED,
        ExperimentState.TRAINING_FAILED,
        ExperimentState.ARTIFACT_WRITE_FAILED,
        "CREATED",
        "CONFIGURED",
        "TRAINING",
        "EVALUATED",
        "TEST_CONSUMED",
        "TRAINING_FAILED",
        "ARTIFACT_WRITE_FAILED",
    ],
)
def test_rejection_when_experiment_is_not_registered(invalid_experiment_state):
    """
    Even if Deployment is GATE_PASSED and Model is DEPLOYABLE,
    if Experiment is not REGISTERED, approval is illegal.
    """
    assert (
        check_deployment_approval_state_legality(
            deployment_current_state=DeploymentState.GATE_PASSED,
            model_state=ModelState.DEPLOYABLE,
            experiment_state=invalid_experiment_state,
        )
        is False
    )

    with pytest.raises(InvalidStateTransitionError) as exc_info:
        validate_deployment_approval_state_legality(
            deployment_current_state=DeploymentState.GATE_PASSED,
            model_state=ModelState.DEPLOYABLE,
            experiment_state=invalid_experiment_state,
        )
    assert "REGISTERED" in str(exc_info.value)


@pytest.mark.parametrize(
    "invalid_deployment_state",
    [
        DeploymentState.CREATED,
        DeploymentState.GATE_PENDING,
        DeploymentState.GATE_BLOCKED,
        DeploymentState.APPROVED,
        DeploymentState.DEPLOYED,
        DeploymentState.PAUSED,
        DeploymentState.RETIRED,
        "CREATED",
        "GATE_PENDING",
        "GATE_BLOCKED",
        "APPROVED",
        "DEPLOYED",
        "PAUSED",
        "RETIRED",
    ],
)
def test_rejection_when_deployment_is_not_gate_passed(invalid_deployment_state):
    """
    Even if Model is DEPLOYABLE and Experiment is REGISTERED,
    if Deployment is not in GATE_PASSED, approval is illegal.
    """
    assert (
        check_deployment_approval_state_legality(
            deployment_current_state=invalid_deployment_state,
            model_state=ModelState.DEPLOYABLE,
            experiment_state=ExperimentState.REGISTERED,
        )
        is False
    )

    with pytest.raises(InvalidStateTransitionError) as exc_info:
        validate_deployment_approval_state_legality(
            deployment_current_state=invalid_deployment_state,
            model_state=ModelState.DEPLOYABLE,
            experiment_state=ExperimentState.REGISTERED,
        )
    assert "cannot transition to APPROVED" in str(exc_info.value)


def test_state_legality_does_not_inspect_gate_conditions():
    """
    CRITICAL ARCHITECTURAL BOUNDARY:
    Verify that state legality purely checks entity states without querying or requiring
    gate condition fields (e.g. locked_test_evaluated, schema_locked, user_approved).
    """
    # A dummy mock/dict without any gate attributes passes state legality
    # as long as states are GATE_PASSED, DEPLOYABLE, REGISTERED.
    assert check_deployment_approval_state_legality(
        deployment_current_state="GATE_PASSED",
        model_state="DEPLOYABLE",
        experiment_state="REGISTERED",
    ) is True


def test_invalid_state_types_and_values():
    """Verify invalid strings or types gracefully return False / raise in validate."""
    assert check_deployment_approval_state_legality("NON_EXISTENT", "DEPLOYABLE", "REGISTERED") is False
    assert check_deployment_approval_state_legality("GATE_PASSED", "INVALID_MODEL", "REGISTERED") is False
    assert check_deployment_approval_state_legality(123, "DEPLOYABLE", "REGISTERED") is False

    with pytest.raises(ValueError):
        validate_deployment_approval_state_legality("NON_EXISTENT", "DEPLOYABLE", "REGISTERED")
