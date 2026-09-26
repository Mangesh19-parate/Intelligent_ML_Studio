"""
Smoke Integration Test: Rapid API and Platform Health Verification.
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.database import SessionLocal
from app.models.user import User
from app.models.role import Role
from app.core.security import get_password_hash, create_access_token


@pytest.fixture
def client():
    return TestClient(app)


def test_platform_smoke_api_workflow(client: TestClient):
    # 1. Health checks
    res = client.get("/health/live")
    assert res.status_code == 200
    assert res.json()["status"] == "alive"

    res = client.get("/health/ready")
    assert res.status_code == 200
    assert res.json()["ready"] is True

    # 2. Authentication flow
    db = SessionLocal()
    try:
        admin_role = db.query(Role).filter(Role.role_name == "ADMIN").first()
        admin_user = db.query(User).filter(User.email == "e2e_admin@studio.dev").first()
        if not admin_user:
            import uuid
            admin_user = User(
                id=uuid.uuid4(),
                email="e2e_admin@studio.dev",
                full_name="E2E Administrator",
                password_hash=get_password_hash("Password123!"),
                role_id=admin_role.id,
                is_active=True,
            )
            db.add(admin_user)
            db.commit()
            db.refresh(admin_user)
        token = create_access_token(str(admin_user.id))
    finally:
        db.close()

    headers = {"Authorization": f"Bearer {token}"}

    # 3. Project Creation
    proj_resp = client.post(
        "/api/v1/projects",
        json={
            "project_name": "E2E Churn Classification",
            "task_type": "UNDETERMINED",
            "description": "End-to-end automated platform validation project",
        },
        headers=headers,
    )
    assert proj_resp.status_code == 201
    project = proj_resp.json()
    assert project["task_type"] == "UNDETERMINED"

    # 4. Catalog inspection
    algo_resp = client.get("/api/v1/admin/catalog/algorithms", headers=headers)
    assert algo_resp.status_code == 200
    assert len(algo_resp.json()) >= 5

    metric_resp = client.get("/api/v1/admin/catalog/metrics", headers=headers)
    assert metric_resp.status_code == 200
    assert len(metric_resp.json()) >= 8

    # 5. Worker health inspection
    worker_resp = client.get("/health/worker")
    assert worker_resp.status_code == 200
    assert worker_resp.json()["status"] in ("UP", "DEGRADED")
