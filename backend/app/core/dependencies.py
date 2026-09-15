from typing import Callable, Any
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import decode_token
from app.models.user import User
from app.repositories.user_repository import UserRepository

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    payload = decode_token(token)
    if not payload:
        raise credentials_exception
    
    token_type = payload.get("type")
    if token_type != "access":
        raise credentials_exception
        
    user_id: str | None = payload.get("sub")
    if user_id is None:
        raise credentials_exception

    user_repo = UserRepository(db)
    user = user_repo.get_by_id(user_id)
    if user is None:
        raise credentials_exception
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user account"
        )
    return user


def get_effective_permissions(user: User) -> set[str]:
    effective_permissions: set[str] = set()
    if user.role and user.role.permissions:
        effective_permissions.update(
            p.permission_key for p in user.role.permissions
        )
    if hasattr(user, "permission_overrides") and user.permission_overrides:
        for override in user.permission_overrides:
            if override.is_granted:
                effective_permissions.add(override.permission_key)
            else:
                effective_permissions.discard(override.permission_key)
    return effective_permissions


def verify_project_ownership(project_id: str | Any, user: User, db: Session) -> None:
    """
    Enforces object-level authorization (IDOR prevention):
    Verifies that the user owns the project or possesses MANAGE_USERS (admin) privileges.
    """
    from app.models.project import Project
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    permissions = get_effective_permissions(user)
    if "MANAGE_USERS" not in permissions and project.owner_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this project's resources"
        )


def require_permission(permission_key: str) -> Callable[[User], User]:
    """
    Dependency factory that enforces permission-based access control.
    Strictly permission-based: computes effective permissions from the user's role
    default bundle, overlaid with granular user_permission_overrides (grant / revoke).
    """
    def _permission_checker(
        current_user: User = Depends(get_current_user)
    ) -> User:
        effective_permissions = get_effective_permissions(current_user)

        # Check requested permission key
        if permission_key not in effective_permissions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied: Missing required permission '{permission_key}'"
            )

        return current_user

    return _permission_checker
