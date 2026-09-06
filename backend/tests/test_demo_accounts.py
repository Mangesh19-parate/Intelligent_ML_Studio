"""
Unit & Integration tests for Day 6 Demo Accounts & Permission Overrides.
Validates:
- trainer@demo.com has role ML_ENGINEER (default bundle: READ, EDIT_DATA, TRAIN, EXPORT) without DEPLOY.
- approver@demo.com has role ML_ENGINEER + explicit DEPLOY override.
- Neither user has the ADMIN role.
- Only approver@demo.com can access routes requiring the DEPLOY permission.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.core.seeder import seed_rbac_data
from app.core.security import create_access_token
from app.models.user import User


@pytest.fixture(autouse=True)
def ensure_rbac_and_demo_accounts(db_session: Session):
    seed_rbac_data(db_session)


def test_demo_accounts_non_admin_roles(db_session: Session):
    """Verify that both trainer@demo.com and approver@demo.com exist and are NOT ADMIN."""
    trainer = db_session.query(User).filter(User.email == "trainer@demo.com").first()
    approver = db_session.query(User).filter(User.email == "approver@demo.com").first()

    assert trainer is not None, "trainer@demo.com was not seeded"
    assert approver is not None, "approver@demo.com was not seeded"

    assert trainer.role.role_name != "ADMIN", "trainer@demo.com must not be ADMIN"
    assert approver.role.role_name != "ADMIN", "approver@demo.com must not be ADMIN"

    assert trainer.role.role_name == "ML_ENGINEER"
    assert approver.role.role_name == "ML_ENGINEER"


def test_demo_accounts_permission_differences(db_session: Session):
    """
    Verify permissions:
    trainer has READ/EDIT_DATA/TRAIN/EXPORT, no DEPLOY.
    approver has explicit DEPLOY override in user_permission_overrides.
    """
    trainer = db_session.query(User).filter(User.email == "trainer@demo.com").first()
    approver = db_session.query(User).filter(User.email == "approver@demo.com").first()

    trainer_overrides = {o.permission_key: o.is_granted for o in trainer.permission_overrides}
    assert "DEPLOY" not in trainer_overrides

    approver_overrides = {o.permission_key: o.is_granted for o in approver.permission_overrides}
    assert "DEPLOY" in approver_overrides
    assert approver_overrides["DEPLOY"] is True


def test_only_approver_has_deploy_endpoint_access(client: TestClient, db_session: Session):
    """
    Accessing /api/v1/auth/deploy-demo:
    - trainer@demo.com is denied with HTTP 403 Forbidden.
    - approver@demo.com is allowed with HTTP 200 OK.
    """
    trainer = db_session.query(User).filter(User.email == "trainer@demo.com").first()
    approver = db_session.query(User).filter(User.email == "approver@demo.com").first()

    trainer_token = create_access_token(subject=str(trainer.id))
    approver_token = create_access_token(subject=str(approver.id))

    # 1. Test trainer@demo.com access -> DENIED (403)
    trainer_resp = client.get(
        "/api/v1/auth/deploy-demo",
        headers={"Authorization": f"Bearer {trainer_token}"}
    )
    assert trainer_resp.status_code == 403
    assert "Missing required permission 'DEPLOY'" in trainer_resp.json()["detail"]

    # 2. Test approver@demo.com access -> GRANTED (200)
    approver_resp = client.get(
        "/api/v1/auth/deploy-demo",
        headers={"Authorization": f"Bearer {approver_token}"}
    )
    assert approver_resp.status_code == 200
    assert approver_resp.json()["message"] == "Permission DEPLOY verified."
    assert approver_resp.json()["email"] == "approver@demo.com"
