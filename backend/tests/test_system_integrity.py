import io
import uuid
import pytest
import numpy as np
import pandas as pd
from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.role import Role
from app.models.user import User
from app.models.project import Project
from app.models.experiment import Experiment
from app.models.trained_model import TrainedModel
from app.models.deployment import Deployment
from app.config.state_machines import DeploymentState, validate_transition, InvalidStateTransitionError
from app.models.user_permission_override import UserPermissionOverride
from app.services.selectors import resolve_top_k, sort_features_with_tie_break, apply_top_k_percent_selection
from app.services.deployment_service import DeploymentService
from app.core.seeder import CANONICAL_ROLES
from backend.scripts.run_checkpoint2_verification import QueryMutationAuditor


def test_stale_roles_absent_in_database(db_session: Session):
    """
    INVARIANT: System strictly recognizes exactly 2 canonical roles: ADMIN and USER.
    No legacy roles (ML_ENGINEER, DATA_STEWARD, DEPLOYMENT_MANAGER, VIEWER) may exist.
    """
    roles = db_session.query(Role).all()
    role_names = {r.role_name for r in roles}
    assert role_names == {"ADMIN", "USER"}, f"Found non-canonical roles: {role_names}"
    assert len(CANONICAL_ROLES) == 2


def test_deterministic_top_k_resolution_and_tie_breaking():
    """
    INVARIANT: TOP_K_PERCENT resolves via resolve_top_k() with alpha=0.25,
    k_min=5, k_max=50, and breaks ties deterministically (score DESC, feature name ASC).
    """
    # 1. Bounds check
    assert resolve_top_k(p=10, alpha=0.25, k_min=5, k_max=50) == 5
    assert resolve_top_k(p=100, alpha=0.25, k_min=5, k_max=50) == 25
    assert resolve_top_k(p=300, alpha=0.25, k_min=5, k_max=50) == 50
    assert resolve_top_k(p=3, alpha=0.25, k_min=5, k_max=50) == 3

    # 2. Deterministic tie breaking
    # feat_b, feat_a, feat_c all have same score 0.8; feat_z has 0.9; feat_d has 0.1
    scores = {
        "feat_b": 0.8,
        "feat_a": 0.8,
        "feat_z": 0.9,
        "feat_c": 0.8,
        "feat_d": 0.1,
    }
    feature_names = list(scores.keys())
    sorted_items = sort_features_with_tie_break(feature_names, scores)
    sorted_names = [item[0] for item in sorted_items]

    # Highest score first ('feat_z': 0.9), followed by alphabetical order for tie ('feat_a', 'feat_b', 'feat_c'), then 'feat_d'
    assert sorted_names == ["feat_z", "feat_a", "feat_b", "feat_c", "feat_d"]

    # Top 3 selection
    assert sorted_names[:3] == ["feat_z", "feat_a", "feat_b"]


def test_deployment_state_machine_illegal_transitions():
    """
    INVARIANT: State machine transitions must be strictly validated.
    - CREATED cannot jump directly to DEPLOYED.
    - RETIRED can never transition to any state.
    """
    # Direct jump from CREATED to DEPLOYED is forbidden (must pass through GATE_PASSED / APPROVED)
    with pytest.raises(InvalidStateTransitionError, match="cannot transition from 'CREATED' to 'DEPLOYED'"):
        validate_transition(DeploymentState.CREATED, DeploymentState.DEPLOYED)

    # RETIRED is terminal
    with pytest.raises(InvalidStateTransitionError, match="terminal state"):
        validate_transition(DeploymentState.RETIRED, DeploymentState.DEPLOYED)

    with pytest.raises(InvalidStateTransitionError, match="terminal state"):
        validate_transition(DeploymentState.RETIRED, DeploymentState.CREATED)


from app.services.deployment_gate_service import DeploymentGateService
from fastapi import HTTPException

def test_four_eyes_separation_of_duties_governance(client, db_session, create_test_user, auth_headers):
    """
    INVARIANT: Four-Eyes Principle. The creator of a model/project cannot approve
    their own model for deployment (SRS v9 §2).
    """
    # User 1 (Creator / Trainer)
    trainer = create_test_user("trainer_4eyes@example.com", role_name="USER")
    override1 = UserPermissionOverride(user_id=trainer.id, permission_key="DEPLOY", is_granted=True)
    db_session.add(override1)

    # User 2 (Independent Approver)
    approver = create_test_user("approver_4eyes@example.com", role_name="USER")
    override2 = UserPermissionOverride(user_id=approver.id, permission_key="DEPLOY", is_granted=True)
    db_session.add(override2)
    db_session.commit()

    # Create project, experiment, model
    proj = Project(id=uuid.uuid4(), project_name="Four Eyes Project", task_type="CLASSIFICATION", owner_id=trainer.id)
    db_session.add(proj)
    db_session.flush()

    exp = Experiment(
        id=uuid.uuid4(),
        project_id=proj.id,
        status="REGISTERED",
    )
    db_session.add(exp)
    db_session.flush()

    model = TrainedModel(
        id=uuid.uuid4(),
        experiment_id=exp.id,
        algorithm_name="LogisticRegression",
        created_by=trainer.id,
    )
    db_session.add(model)
    db_session.commit()

    # 1. Trainer attempts self-approval -> must raise 403 HTTPException
    gate_service = DeploymentGateService(db_session)
    with pytest.raises(HTTPException) as exc_info:
        gate_service.check_gate(
            model_id=model.id,
            user_approved=True,
            approved_by_user_id=trainer.id,
        )
    assert exc_info.value.status_code == 403
    assert "Self-approval is forbidden" in exc_info.value.detail

    # 2. Independent approver approves -> self-approval check passes (does not raise 403)
    gate = gate_service.check_gate(
        model_id=model.id,
        user_approved=True,
        approved_by_user_id=approver.id,
    )
    assert gate.approved_by == approver.id
    assert gate.user_approved is True


def test_global_error_envelope_consistency(client, create_test_user, auth_headers):
    """
    INVARIANT: Error responses must deliver a uniform structured error envelope
    containing status_code, path, and timestamp, while preserving detail for client compatibility.
    """
    admin = create_test_user("admin_env@example.com", role_name="ADMIN")
    headers = auth_headers(admin)

    # 404 Not Found
    resp_404 = client.get(f"/api/v1/projects/{uuid.uuid4()}", headers=headers)
    assert resp_404.status_code == status.HTTP_404_NOT_FOUND
    data_404 = resp_404.json()
    assert "detail" in data_404
    assert "error" in data_404
    assert data_404["error"]["status_code"] == 404
    assert "timestamp" in data_404["error"]
    assert "path" in data_404["error"]

    # 422 Validation Error
    resp_422 = client.post("/api/v1/auth/login", json={"invalid_payload": 123})
    assert resp_422.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    data_422 = resp_422.json()
    assert "detail" in data_422
    assert "error" in data_422
    assert data_422["error"]["status_code"] == 422
    assert data_422["error"]["message"] == "Request validation failed"
    assert len(data_422["error"]["details"]) > 0


from backend.scripts.run_checkpoint2_verification import run_live_checkpoint_2

def test_model_passport_zero_mutation_guarantee(client, db_session, create_test_user, auth_headers):
    """
    INVARIANT: Model Technical Passport retrieval is strictly read-only:
    Executes exactly ZERO SQL mutations (INSERT/UPDATE/DELETE).
    """
    res = run_live_checkpoint_2(db=db_session)
    assert res["all_passed"] is True
    model_id = res["model_passport"]["model_id"]

    user = create_test_user("passport_auditor@example.com", role_name="USER")
    headers = auth_headers(user)

    engine = db_session.get_bind()
    with QueryMutationAuditor(engine) as auditor:
        resp = client.get(f"/api/v1/models/{model_id}/passport", headers=headers)

    assert resp.status_code == status.HTTP_200_OK
    assert auditor.mutation_count == 0, f"Expected 0 mutations, got {auditor.mutations}"
    assert auditor.select_count > 0
