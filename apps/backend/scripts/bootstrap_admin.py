"""
Bootstrap Administrator Account CLI
Reference: Software Requirements Specification (SRS) v4 / §1.3

Usage:
    python -m scripts.bootstrap_admin --email admin@mlstudio.local --password SuperSecret123!
    python scripts/bootstrap_admin.py --email admin@mlstudio.local --password SuperSecret123!

Idempotent bootstrap: Refuses execution with an error if an ADMIN account already exists in the system.
"""

import argparse
import sys
import os
from pathlib import Path

# Add backend directory to sys.path if invoked directly as a script
backend_root = Path(__file__).resolve().parent.parent
if str(backend_root) not in sys.path:
    sys.path.insert(0, str(backend_root))

from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.core.seeder import seed_rbac_data
from app.core.security import get_password_hash
from app.models.role import Role
from app.models.user import User


def bootstrap_admin_account(
    email: str,
    password: str,
    full_name: str = "System Administrator",
    db: Session | None = None,
) -> User:
    """
    Programmatic entrypoint to bootstrap the initial ADMIN account.

    Raises:
        RuntimeError: If an admin account already exists.
        ValueError: If email or password is empty or invalid.
    """
    if not email or not email.strip():
        raise ValueError("Email must not be empty.")
    if not password or len(password) < 6:
        raise ValueError("Password must be at least 6 characters.")

    session_managed = False
    if db is None:
        db = SessionLocal()
        session_managed = True

    try:
        # 1. Ensure canonical RBAC structure is seeded
        seed_rbac_data(db)

        # 2. Query for the canonical ADMIN role
        admin_role = db.query(Role).filter(Role.role_name == "ADMIN").first()
        if not admin_role:
            raise RuntimeError("ADMIN role is not seeded in the database.")

        # 3. Check if ANY user with the ADMIN role already exists (Refusal Check)
        existing_admin = db.query(User).filter(User.role_id == admin_role.id).first()
        if existing_admin:
            raise RuntimeError(
                f"Refusing bootstrap: An administrator account already exists (ID: {existing_admin.id}, Email: {existing_admin.email})."
            )

        # 4. Check if a user with this specific email already exists
        existing_email_user = db.query(User).filter(User.email == email.lower().strip()).first()
        if existing_email_user:
            raise RuntimeError(
                f"Refusing bootstrap: A user with email '{email}' already exists."
            )

        # 5. Create new Admin user
        admin_user = User(
            full_name=full_name.strip(),
            email=email.lower().strip(),
            password_hash=get_password_hash(password),
            role_id=admin_role.id,
            is_active=True,
        )
        db.add(admin_user)
        db.commit()
        db.refresh(admin_user)
        return admin_user
    finally:
        if session_managed and db is not None:
            db.close()


def main():
    parser = argparse.ArgumentParser(
        description="Bootstrap the initial ML Studio administrator account."
    )
    parser.add_argument(
        "--email", "-e",
        required=True,
        help="Email address for the initial administrator",
    )
    parser.add_argument(
        "--password", "-p",
        required=True,
        help="Password for the initial administrator",
    )
    parser.add_argument(
        "--full-name", "-n",
        default="System Administrator",
        help="Full name for the initial administrator",
    )

    args = parser.parse_args()

    try:
        user = bootstrap_admin_account(
            email=args.email,
            password=args.password,
            full_name=args.full_name,
        )
        print(f"SUCCESS: Administrator account '{user.email}' (ID: {user.id}) created successfully.")
        sys.exit(0)
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
