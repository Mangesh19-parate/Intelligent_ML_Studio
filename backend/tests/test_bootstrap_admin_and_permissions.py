"""
Unit & Integration tests for Day 4 Bootstrap CLI and Permission Primitive.
Validates:
- bootstrap_admin_account creates initial admin account idempotently.
- bootstrap_admin_account refuses execution if an ADMIN user already exists.
- require_permission evaluates role base bundle overridden by user_permission_overrides rows (grant / revoke).
- Protected demonstration route enforcement.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.core.security import create_access_token
from app.models.role import Role
from app.models.user import User
from app.models.user_permission_override import UserPermissionOverride
from scripts.bootstrap_admin import bootstrap_admin_account


def test_bootstrap_admin_creation_and_refusal(db_session: Session):
    """
    Test that bootstrap_admin_account creates the admin on first invocation,
    and strictly refuses to run if an ADMIN already exists.
    """
    # 1. Clean any existing users with ADMIN role in db_session
    admin_role = db_session.query(Role).filter(Role.role_name == "ADMIN").first()
    if admin_role:
        db_session.query(User).filter(User.role_id == admin_role.id).delete()
        db_session.commit()

    # 2. First bootstrap run -> SUCCESS
    admin_user = bootstrap_admin_account(
        email="root_admin@mlstudio.local",
        password="AdminSecurePassword123!",
        full_name="Root Admin",
        db=db_session,
    )
    assert admin_user is not None
    assert admin_user.email == "root_admin@mlstudio.local"
    assert admin_user.role.role_name == "ADMIN"

    # 3. Second bootstrap run -> REFUSAL
    with pytest.raises(RuntimeError) as exc_info:
        bootstrap_admin_account(
            email="another_admin@mlstudio.local",
            password="AnotherPassword123!",
            full_name="Second Admin",
            db=db_session,
        )
    assert "Refusing bootstrap: An administrator account already exists" in str(exc_info.value)


def test_require_permission_role_default_denial(client: TestClient, db_session: Session):
    """A user with VIEWER role lacks TRAIN permission by default -> 403 Forbidden."""
    viewer_role = db_session.query(Role).filter(Role.role_name == "VIEWER").first()
    viewer_user = User(
        full_name="Default Viewer",
        email="viewer_default@example.com",
        password_hash="hash",
        role_id=viewer_role.id,
        is_active=True,
    )
    db_session.add(viewer_user)
    db_session.commit()
    db_session.refresh(viewer_user)

    token = create_access_token(subject=str(viewer_user.id))
    headers = {"Authorization": f"Bearer {token}"}

    response = client.get("/api/v1/auth/protected-demo", headers=headers)
    assert response.status_code == 403
    assert "Missing required permission 'TRAIN'" in response.json()["detail"]


def test_require_permission_override_grant(client: TestClient, db_session: Session):
    """
    A VIEWER user who is granted an explicit user_permission_overrides row (is_granted=True, TRAIN)
    successfully accesses the route requiring TRAIN -> 200 OK.
    """
    viewer_role = db_session.query(Role).filter(Role.role_name == "VIEWER").first()
    viewer_user = User(
        full_name="Elevated Viewer",
        email="viewer_elevated@example.com",
        password_hash="hash",
        role_id=viewer_role.id,
        is_active=True,
    )
    db_session.add(viewer_user)
    db_session.commit()
    db_session.refresh(viewer_user)

    # Add override GRANT for TRAIN
    override = UserPermissionOverride(
        user_id=viewer_user.id,
        permission_key="TRAIN",
        is_granted=True,
    )
    db_session.add(override)
    db_session.commit()

    token = create_access_token(subject=str(viewer_user.id))
    headers = {"Authorization": f"Bearer {token}"}

    response = client.get("/api/v1/auth/protected-demo", headers=headers)
    assert response.status_code == 200
    assert response.json()["message"] == "Permission TRAIN verified."


def test_require_permission_override_revoke(client: TestClient, db_session: Session):
    """
    An ML_ENGINEER user who has TRAIN by default, but has an explicit user_permission_overrides row
    (is_granted=False, TRAIN), is denied access -> 403 Forbidden.
    """
    engineer_role = db_session.query(Role).filter(Role.role_name == "ML_ENGINEER").first()
    engineer_user = User(
        full_name="Revoked Engineer",
        email="engineer_revoked@example.com",
        password_hash="hash",
        role_id=engineer_role.id,
        is_active=True,
    )
    db_session.add(engineer_user)
    db_session.commit()
    db_session.refresh(engineer_user)

    # Add override REVOKE for TRAIN
    override = UserPermissionOverride(
        user_id=engineer_user.id,
        permission_key="TRAIN",
        is_granted=False,
    )
    db_session.add(override)
    db_session.commit()

    token = create_access_token(subject=str(engineer_user.id))
    headers = {"Authorization": f"Bearer {token}"}

    response = client.get("/api/v1/auth/protected-demo", headers=headers)
    assert response.status_code == 403
    assert "Missing required permission 'TRAIN'" in response.json()["detail"]
