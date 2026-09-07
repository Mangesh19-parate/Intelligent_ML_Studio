"""
Tests for Independent State Machine Wiring (SRS v9 §2 / §8 / §10).

Validates that:
1. experiments.status is wired to ExperimentState and enforces DB CheckConstraints.
2. trained_models.status is wired to ModelState and enforces DB CheckConstraints.
3. deployments.status is wired to DeploymentState and enforces DB CheckConstraints.
4. All four status columns across tables are strictly decoupled and independent.
"""

import uuid
import pytest
from sqlalchemy.exc import IntegrityError

from tests.conftest import engine, TestingSessionLocal
from app.config.state_machines import (
    ProjectState,
    ExperimentState,
    ModelState,
    DeploymentState,
    validate_transition,
    can_transition,
    InvalidStateTransitionError,
)
from app.models.project import Project
from app.models.experiment import Experiment
from app.models.trained_model import TrainedModel
from app.models.deployment import Deployment
from app.models.user import User
from app.models.role import Role


@pytest.fixture
def setup_hierarchy(db_session):
    """Sets up user and project records for foreign key constraints."""
    role = db_session.query(Role).first()
    user = User(
        id=uuid.uuid4(),
        email=f"state_test_{uuid.uuid4().hex[:8]}@example.com",
        password_hash="hashed_pw",
        full_name="State Test User",
        role_id=role.id,
    )
    db_session.add(user)
    db_session.flush()

    project = Project(
        id=uuid.uuid4(),
        owner_id=user.id,
        project_name="State Wiring Test Project",
        task_type="REGRESSION",
        target_column="target",
        pipeline_stage="DATA",
    )
    db_session.add(project)
    db_session.commit()
    db_session.refresh(user)
    db_session.refresh(project)
    return user, project


# =============================================================================
# 1. EXPERIMENT STATE WIRING & CONSTRAINTS
# =============================================================================

def test_experiment_state_all_canonical_values_persist(db_session, setup_hierarchy):
    """Verifies that every canonical ExperimentState enum value can be persisted to experiments.status."""
    _, project = setup_hierarchy

    for state in ExperimentState:
        exp = Experiment(
            id=uuid.uuid4(),
            project_id=project.id,
            status=state.value,
            task_type="REGRESSION",
        )
        db_session.add(exp)
        db_session.commit()
        db_session.refresh(exp)
        assert exp.status == state.value


def test_experiment_state_invalid_value_rejected(db_session, setup_hierarchy):
    """Verifies that illegal status strings violate chk_experiment_status constraint."""
    _, project = setup_hierarchy

    exp = Experiment(
        id=uuid.uuid4(),
        project_id=project.id,
        status="INVALID_EXPERIMENT_STATUS",
        task_type="REGRESSION",
    )
    db_session.add(exp)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


# =============================================================================
# 2. MODEL STATE WIRING & CONSTRAINTS
# =============================================================================

def test_model_state_all_canonical_values_persist(db_session, setup_hierarchy):
    """Verifies that every canonical ModelState enum value can be persisted to trained_models.status."""
    _, project = setup_hierarchy

    exp = Experiment(
        id=uuid.uuid4(),
        project_id=project.id,
        status=ExperimentState.TRAINING.value,
        task_type="REGRESSION",
    )
    db_session.add(exp)
    db_session.commit()

    for state in ModelState:
        model = TrainedModel(
            id=uuid.uuid4(),
            experiment_id=exp.id,
            algorithm_name="LinearRegression",
            status=state.value,
        )
        db_session.add(model)
        db_session.commit()
        db_session.refresh(model)
        assert model.status == state.value


def test_model_state_invalid_value_rejected(db_session, setup_hierarchy):
    """Verifies that illegal status strings violate chk_trained_model_status constraint."""
    _, project = setup_hierarchy

    exp = Experiment(
        id=uuid.uuid4(),
        project_id=project.id,
        status=ExperimentState.TRAINING.value,
        task_type="REGRESSION",
    )
    db_session.add(exp)
    db_session.commit()

    model = TrainedModel(
        id=uuid.uuid4(),
        experiment_id=exp.id,
        algorithm_name="LinearRegression",
        status="INVALID_MODEL_STATUS",
    )
    db_session.add(model)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


# =============================================================================
# 3. DEPLOYMENT STATE WIRING & CONSTRAINTS
# =============================================================================

def test_deployment_state_all_canonical_values_persist(db_session, setup_hierarchy):
    """Verifies that every canonical DeploymentState enum value can be persisted to deployments.status."""
    user, project = setup_hierarchy

    exp = Experiment(
        id=uuid.uuid4(),
        project_id=project.id,
        status=ExperimentState.REGISTERED.value,
        task_type="REGRESSION",
    )
    db_session.add(exp)
    db_session.commit()

    model = TrainedModel(
        id=uuid.uuid4(),
        experiment_id=exp.id,
        algorithm_name="LinearRegression",
        status=ModelState.DEPLOYABLE.value,
    )
    db_session.add(model)
    db_session.commit()

    for state in DeploymentState:
        dep_id = uuid.uuid4()
        dep = Deployment(
            id=dep_id,
            model_id=model.id,
            endpoint_path=f"/api/v1/predict/{dep_id}",
            status=state.value,
            deployed_by=user.id,
        )
        db_session.add(dep)
        db_session.commit()
        db_session.refresh(dep)
        assert dep.status == state.value


def test_deployment_state_invalid_value_rejected(db_session, setup_hierarchy):
    """Verifies that illegal status strings violate chk_deployment_status constraint."""
    user, project = setup_hierarchy

    exp = Experiment(
        id=uuid.uuid4(),
        project_id=project.id,
        status=ExperimentState.REGISTERED.value,
        task_type="REGRESSION",
    )
    db_session.add(exp)
    db_session.commit()

    model = TrainedModel(
        id=uuid.uuid4(),
        experiment_id=exp.id,
        algorithm_name="LinearRegression",
        status=ModelState.DEPLOYABLE.value,
    )
    db_session.add(model)
    db_session.commit()

    dep_id = uuid.uuid4()
    dep = Deployment(
        id=dep_id,
        model_id=model.id,
        endpoint_path=f"/api/v1/predict/{dep_id}",
        status="INVALID_DEPLOYMENT_STATUS",
        deployed_by=user.id,
    )
    db_session.add(dep)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


# =============================================================================
# 4. CROSS-TABLE STATUS DECOUPLING INVARIANT (SRS v9 §2)
# =============================================================================

def test_four_status_columns_are_strictly_independent(db_session, setup_hierarchy):
    """
    Verifies that Project, Experiment, TrainedModel, and Deployment each maintain
    their own independent status columns with completely independent enum lifecycles.
    """
    user, project = setup_hierarchy

    # Set project stage to TRANSFORMED
    project.pipeline_stage = ProjectState.TRANSFORMED.value

    # Create experiment in TRAINING
    exp = Experiment(
        id=uuid.uuid4(),
        project_id=project.id,
        status=ExperimentState.TRAINING.value,
        task_type="REGRESSION",
    )
    db_session.add(exp)
    db_session.commit()

    # Create model in ARTIFACT_VERIFIED
    model = TrainedModel(
        id=uuid.uuid4(),
        experiment_id=exp.id,
        algorithm_name="LinearRegression",
        status=ModelState.ARTIFACT_VERIFIED.value,
    )
    db_session.add(model)
    db_session.commit()

    # Create deployment in GATE_PENDING
    dep_id = uuid.uuid4()
    dep = Deployment(
        id=dep_id,
        model_id=model.id,
        endpoint_path=f"/api/v1/predict/{dep_id}",
        status=DeploymentState.GATE_PENDING.value,
        deployed_by=user.id,
    )
    db_session.add(dep)
    db_session.commit()

    # Refresh all 4 entities and verify their status fields are isolated
    db_session.refresh(project)
    db_session.refresh(exp)
    db_session.refresh(model)
    db_session.refresh(dep)

    assert project.pipeline_stage == "TRANSFORMED"
    assert exp.status == "TRAINING"
    assert model.status == "ARTIFACT_VERIFIED"
    assert dep.status == "GATE_PENDING"
