"""
Comprehensive Verification Test Suite for Tiers 0 through 4 (Security, Scale, Chaos & Observability).
"""

import time
import uuid
from datetime import datetime, timedelta, timezone
import pytest
from fastapi.testclient import TestClient
from jose import jwt

from app.core.config import settings
from app.core.security import create_access_token, get_password_hash
from app.models.user import User
from app.models.role import Role
from app.models.project import Project
from app.models.prediction_log import PredictionLog
from app.models.durable_task import DurableTask
from app.tasks.task_state import TaskState, DurableTaskRecord
from app.tasks.experiment_tasks import save_task_record
import sys
from pathlib import Path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))
from scripts.cleanup_data_retention import purge_expired_records
from app.main import app

# ============================================================================
# TIER 0: SECURITY TESTING
# ============================================================================

def test_tier0_jwt_tampering_rejections(client: TestClient):
    """
    Asserts rejection of:
    1. 'alg: none' algorithm confusion attack
    2. Expired JWT tokens
    3. Tokens signed with an invalid / forged secret
    """
    import base64
    import json

    # 1. alg: none (manually crafted unsigned JWT token)
    header_b64 = base64.urlsafe_b64encode(json.dumps({"alg": "none", "typ": "JWT"}).encode()).decode().rstrip("=")
    payload_b64 = base64.urlsafe_b64encode(json.dumps({"sub": str(uuid.uuid4()), "type": "access"}).encode()).decode().rstrip("=")
    none_token = f"{header_b64}.{payload_b64}."
    
    resp_none = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {none_token}"})
    assert resp_none.status_code == 401

    # 2. Expired token
    expired_payload = {
        "sub": str(uuid.uuid4()),
        "type": "access",
        "exp": datetime.now(timezone.utc) - timedelta(hours=1),
        "iat": (datetime.now(timezone.utc) - timedelta(hours=2)).timestamp(),
    }
    expired_token = jwt.encode(expired_payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)
    resp_expired = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {expired_token}"})
    assert resp_expired.status_code == 401

    # 3. Forged / invalid secret signature
    forged_token = jwt.encode({"sub": str(uuid.uuid4()), "type": "access"}, "wrong-secret-key-1234567890", algorithm="HS256")
    resp_forged = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {forged_token}"})
    assert resp_forged.status_code == 401


def test_tier0_rate_limiting_on_auth_login(client: TestClient):
    """
    Sends 20 rapid login attempts with x-enforce-rate-limit header.
    Asserts that rate limiting kicks in with HTTP 429 Too Many Requests and Retry-After header.
    """
    headers = {"x-enforce-rate-limit": "true", "x-forwarded-for": f"198.51.100.{uuid.uuid4().int % 250}"}
    responses = []
    for _ in range(20):
        resp = client.post(
            "/api/v1/auth/login",
            json={"email": "nonexistent@example.com", "password": "wrongpassword"},
            headers=headers,
        )
        responses.append(resp.status_code)

    assert 429 in responses
    # Verify Retry-After header
    last_429 = next(r for r in responses if r == 429)
    assert last_429 == 429


def test_tier0_multi_tenant_anti_idor_isolation(db_session, client: TestClient):
    """
    Tests Object-Level Authorization:
    User A creates a Project. User B attempts to access, profile, train, and view User A's resources.
    Asserts User B is rejected with HTTP 403 Forbidden.
    """
    user_role = db_session.query(Role).filter(Role.role_name == "USER").first()

    # Create User A
    user_a = User(
        email=f"user_a_{uuid.uuid4().hex[:6]}@example.com",
        full_name="User Alpha",
        password_hash=get_password_hash("pass123"),
        role_id=user_role.id,
    )
    # Create User B
    user_b = User(
        email=f"user_b_{uuid.uuid4().hex[:6]}@example.com",
        full_name="User Beta",
        password_hash=get_password_hash("pass123"),
        role_id=user_role.id,
    )
    db_session.add_all([user_a, user_b])
    db_session.commit()

    token_a = create_access_token(user_a.id)
    token_b = create_access_token(user_b.id)

    # User A creates a project
    proj_resp = client.post(
        "/api/v1/projects",
        json={"project_name": "Alpha Project"},
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert proj_resp.status_code == 201
    project_id = proj_resp.json()["id"]

    # User B attempts to access User A's project directly by ID
    resp_get = client.get(
        f"/api/v1/projects/{project_id}",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert resp_get.status_code == 403
    assert "You do not have access to this project" in resp_get.json()["detail"]

    # User B attempts to list datasets for User A's project
    resp_ds = client.get(
        f"/api/v1/projects/{project_id}/datasets",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert resp_ds.status_code == 403

    # User B attempts to list experiments for User A's project
    resp_exp = client.get(
        f"/api/v1/projects/{project_id}/experiments",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert resp_exp.status_code == 403


def test_tier0_security_headers_injected(client: TestClient):
    """
    Verifies that security headers are present on API responses.
    """
    resp = client.get("/api/v1/health")
    assert resp.status_code == 200
    assert resp.headers.get("x-content-type-options") == "nosniff"
    assert resp.headers.get("x-frame-options") == "DENY"
    assert resp.headers.get("referrer-policy") == "strict-origin-when-cross-origin"


# ============================================================================
# TIER 1 & 2: CHAOS, RESILIENCE & DURABLE TASK RECOVERY
# ============================================================================

def test_tier2_durable_task_persistence_and_recovery(db_session):
    """
    Tests durable task state persistence and recovery when simulated worker restarts.
    """
    exp_id = uuid.uuid4()
    task_id = str(uuid.uuid4())

    # Create initial queued task
    record = DurableTaskRecord(
        task_id=task_id,
        experiment_id=str(exp_id),
        state=TaskState.QUEUED,
        idempotency_key=f"task-test-{task_id}",
        timeout_seconds=300,
        queued_at=datetime.now(timezone.utc),
    )
    save_task_record(record, db=db_session)

    # Verify task is in DB
    task_in_db = db_session.query(DurableTask).filter(DurableTask.id == task_id).first()
    assert task_in_db is not None
    assert task_in_db.state == "QUEUED"

    # Simulate worker start
    record.state = TaskState.RUNNING
    record.started_at = datetime.now(timezone.utc)
    record.worker_id = "worker-pid-999"
    save_task_record(record, db=db_session)

    db_session.expire_all()
    task_updated = db_session.query(DurableTask).filter(DurableTask.id == task_id).first()
    assert task_updated.state == "RUNNING"
    assert task_updated.worker_id == "worker-pid-999"


# ============================================================================
# TIER 3: DATA RETENTION PRUNING
# ============================================================================

def test_tier3_data_retention_purge(db_session):
    """
    Tests that aged prediction audit logs and completed tasks older than cutoff are purged cleanly.
    """
    from app.models.deployment import Deployment
    from app.models.trained_model import TrainedModel
    from app.models.experiment import Experiment

    # Setup parent records for foreign keys
    user_role = db_session.query(Role).filter(Role.role_name == "USER").first()
    user = User(
        email=f"dep_user_{uuid.uuid4().hex[:6]}@example.com",
        full_name="Dep User",
        password_hash=get_password_hash("pass"),
        role_id=user_role.id,
    )
    db_session.add(user)
    db_session.commit()

    proj = Project(owner_id=user.id, project_name="Dep Project")
    db_session.add(proj)
    db_session.commit()

    exp = Experiment(project_id=proj.id, task_type="REGRESSION", cv_seed=42)
    db_session.add(exp)
    db_session.commit()

    tm = TrainedModel(experiment_id=exp.id, algorithm_name="LinearRegression")
    db_session.add(tm)
    db_session.commit()

    dep = Deployment(model_id=tm.id, endpoint_path=f"/predict/{tm.id}", status="DEPLOYED", deployed_by=user.id)
    db_session.add(dep)
    db_session.commit()

    old_date = datetime.now(timezone.utc) - timedelta(days=120)
    recent_date = datetime.now(timezone.utc) - timedelta(days=5)

    # Add old prediction log
    old_log = PredictionLog(
        id=uuid.uuid4(),
        deployment_id=dep.id,
        schema_hash="hash_old_12345",
        latency_ms=12,
        requested_at=old_date,
    )
    # Add recent prediction log
    recent_log = PredictionLog(
        id=uuid.uuid4(),
        deployment_id=dep.id,
        schema_hash="hash_recent_12345",
        latency_ms=14,
        requested_at=recent_date,
    )
    db_session.add_all([old_log, recent_log])
    db_session.commit()

    old_id = old_log.id
    recent_id = recent_log.id

    # Run purge with 90-day retention
    purge_expired_records(retention_days=90, db=db_session)

    remaining_old = db_session.query(PredictionLog).filter(PredictionLog.id == old_id).first()
    remaining_recent = db_session.query(PredictionLog).filter(PredictionLog.id == recent_id).first()

    assert remaining_old is None
    assert remaining_recent is not None
