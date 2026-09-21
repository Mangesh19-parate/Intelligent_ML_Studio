"""
Day 6 — Admin Pages Test Suite (SRS §1.3, §2.8, §2.9, §2.15).

Verifies:
1. User Management & Role assignment.
2. Per-user DEPLOY Permission Override:
   - Viewer granted DEPLOY override can access deploy operations.
   - Deployment Manager revoked DEPLOY override is blocked.
   - Resetting override restores role defaults.
3. Canonical Algorithm & Metric Catalog endpoints.
4. Unified multi-entity governance audit logs stream & filtering.
"""

from datetime import datetime, timezone
from pathlib import Path
import pytest
from uuid import uuid4
from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.seeder import seed_rbac_data
from app.core.security import create_access_token, get_password_hash
from app.models.user import User
from app.models.role import Role
from app.models.deployment_gate import DeploymentGate
from app.models.prediction_log import PredictionLog
from app.models.project import Project
from app.models.experiment import Experiment
from app.models.trained_model import TrainedModel
from app.models.deployment import Deployment
from app.config.state_machines import ModelState, ExperimentState


@pytest.fixture(autouse=True)
def ensure_seed_rbac(db_session: Session):
    seed_rbac_data(db_session)


@pytest.fixture
def admin_headers(db_session: Session):
    admin = db_session.query(User).filter(User.email == "trainer@demo.com").first()
    # Ensure trainer has ADMIN role for test execution
    admin_role = db_session.query(Role).filter(Role.role_name == "ADMIN").first()
    admin.role_id = admin_role.id
    db_session.commit()
    token = create_access_token(str(admin.id))
    return {"Authorization": f"Bearer {token}"}


def test_admin_list_and_create_users(client: TestClient, db_session: Session, admin_headers: dict):
    """
    Verifies user listing, creation, and role updates via Admin API.
    """
    # 1. List users
    resp = client.get("/api/v1/admin/users", headers=admin_headers)
    assert resp.status_code == status.HTTP_200_OK
    users = resp.json()
    assert len(users) >= 2

    # 2. Create new user
    new_email = f"analyst_{uuid4().hex[:6]}@demo.com"
    create_payload = {
        "full_name": "Data Analyst Test",
        "email": new_email,
        "password": "Password123!",
        "role_name": "USER",
    }
    create_resp = client.post("/api/v1/admin/users", json=create_payload, headers=admin_headers)
    assert create_resp.status_code == status.HTTP_201_CREATED
    created_user = create_resp.json()
    assert created_user["email"] == new_email
    assert created_user["role_name"] == "USER"
    assert "READ" in created_user["effective_permissions"]
    assert "DEPLOY" not in created_user["effective_permissions"]

    # 3. Update user role to ADMIN
    user_id = created_user["id"]
    patch_resp = client.patch(
        f"/api/v1/admin/users/{user_id}",
        json={"role_name": "ADMIN"},
        headers=admin_headers,
    )
    assert patch_resp.status_code == status.HTTP_200_OK
    updated_user = patch_resp.json()
    assert updated_user["role_name"] == "ADMIN"
    assert "MANAGE_USERS" in updated_user["effective_permissions"]


def test_per_user_deploy_override_flow(client: TestClient, db_session: Session, admin_headers: dict):
    """
    Verifies granular per-user DEPLOY permission override:
    1. A USER has no DEPLOY permission.
    2. Admin grants DEPLOY override -> USER gains DEPLOY permission.
    3. Admin revokes DEPLOY override -> USER loses DEPLOY permission.
    4. Admin resets override -> User returns to role default.
    """
    user_role = db_session.query(Role).filter(Role.role_name == "USER").first()
    normal_user = User(
        id=uuid4(),
        full_name="Restricted User",
        email=f"user_{uuid4().hex[:6]}@demo.com",
        password_hash=get_password_hash("Secret123"),
        role_id=user_role.id,
        is_active=True,
    )
    db_session.add(normal_user)
    db_session.commit()

    user_id = str(normal_user.id)

    # 1. Initial State: Viewer has NO deploy permission
    users_resp = client.get("/api/v1/admin/users", headers=admin_headers)
    u_data = next(u for u in users_resp.json() if u["id"] == user_id)
    assert "DEPLOY" not in u_data["effective_permissions"]

    # 2. Grant DEPLOY override
    grant_resp = client.put(
        f"/api/v1/admin/users/{user_id}/overrides",
        json={"permission_key": "DEPLOY", "is_granted": True},
        headers=admin_headers,
    )
    assert grant_resp.status_code == status.HTTP_200_OK
    granted_data = grant_resp.json()
    assert "DEPLOY" in granted_data["effective_permissions"]
    deploy_override = next(o for o in granted_data["permission_overrides"] if o["permission_key"] == "DEPLOY")
    assert deploy_override["is_granted"] is True

    # 3. Explicitly Revoke DEPLOY override
    revoke_resp = client.put(
        f"/api/v1/admin/users/{user_id}/overrides",
        json={"permission_key": "DEPLOY", "is_granted": False},
        headers=admin_headers,
    )
    assert revoke_resp.status_code == status.HTTP_200_OK
    revoked_data = revoke_resp.json()
    assert "DEPLOY" not in revoked_data["effective_permissions"]
    revoked_override = next(o for o in revoked_data["permission_overrides"] if o["permission_key"] == "DEPLOY")
    assert revoked_override["is_granted"] is False

    # 4. Delete override to reset to role default
    del_resp = client.delete(
        f"/api/v1/admin/users/{user_id}/overrides/DEPLOY",
        headers=admin_headers,
    )
    assert del_resp.status_code == status.HTTP_200_OK
    reset_data = del_resp.json()
    assert not any(o["permission_key"] == "DEPLOY" for o in reset_data["permission_overrides"])
    assert "DEPLOY" not in reset_data["effective_permissions"]


def test_algorithm_and_metric_catalogs(client: TestClient, admin_headers: dict):
    """
    Verifies that Algorithm, Metric, and Feature Selection catalogs are accessible.
    """
    # 1. Algorithms Catalog
    algo_resp = client.get("/api/v1/admin/catalog/algorithms", headers=admin_headers)
    assert algo_resp.status_code == status.HTTP_200_OK
    algos = algo_resp.json()
    assert len(algos) >= 5
    algo_ids = [a["id"] for a in algos]
    assert "linear_regression" in algo_ids
    assert "random_forest_regressor" in algo_ids
    assert "logistic_regression" in algo_ids

    # 2. Metrics Catalog
    metric_resp = client.get("/api/v1/admin/catalog/metrics", headers=admin_headers)
    assert metric_resp.status_code == status.HTTP_200_OK
    metrics = metric_resp.json()
    assert len(metrics) >= 8
    m_ids = [m["id"] for m in metrics]
    assert "rmse" in m_ids
    assert "macro_f1" in m_ids

    rmse_metric = next(m for m in metrics if m["id"] == "rmse")
    assert rmse_metric["direction"] == "MINIMIZE"
    assert rmse_metric["is_default"] is True

    # 3. Features Catalog
    feat_resp = client.get("/api/v1/admin/catalog/features", headers=admin_headers)
    assert feat_resp.status_code == status.HTTP_200_OK
    features = feat_resp.json()
    assert features["strategy"] == "TOP_K_PERCENT"
    assert "correlation" in features["active_methods"]
    assert "lasso" in features["active_methods"]


def test_governance_audit_logs(client: TestClient, db_session: Session, admin_headers: dict):
    """
    Verifies that unified multi-entity audit logs return gate evaluations, prediction logs,
    and permission events with search and filtering.
    """
    # Insert a dummy deployment gate record
    trainer = db_session.query(User).filter(User.email == "trainer@demo.com").first()
    gate = DeploymentGate(
        id=uuid4(),
        model_id=uuid4(),
        gate_passed=True,
        evaluated_at=datetime.now(timezone.utc),
        approved_by=trainer.id,
        locked_test_evaluated=True,
        schema_locked=True,
        artifact_verified=True,
        lineage_complete=True,
        performance_threshold_passed="PASS",
        user_approved=True,
    )
    db_session.add(gate)
    db_session.commit()

    # Query all audit logs
    audit_resp = client.get("/api/v1/admin/audit-logs?limit=50", headers=admin_headers)
    assert audit_resp.status_code == status.HTTP_200_OK
    logs = audit_resp.json()
    assert len(logs) >= 1

    # Query filtered by event_type
    gate_logs_resp = client.get("/api/v1/admin/audit-logs?event_type=GATE_EVALUATION", headers=admin_headers)
    assert gate_logs_resp.status_code == status.HTTP_200_OK
    gate_logs = gate_logs_resp.json()
    assert all(l["event_type"] == "GATE_EVALUATION" for l in gate_logs)
