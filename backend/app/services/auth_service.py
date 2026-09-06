from uuid import UUID
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.core.security import (
    get_password_hash,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
)
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.schemas.auth import (
    RegisterRequest,
    SignupRequest,
    LoginRequest,
    TokenResponse,
    UserResponse,
    RoleResponse,
    PermissionResponse,
)

class AuthService:
    def __init__(self, db: Session):
        self.db = db
        self.user_repo = UserRepository(db)

    def _build_user_response(self, user: User) -> UserResponse:
        permissions = [p.permission_key for p in user.role.permissions] if user.role and user.role.permissions else []
        role_resp = RoleResponse(
            id=user.role.id,
            role_name=user.role.role_name,
            description=user.role.description,
            permissions=[
                PermissionResponse(id=p.id, permission_key=p.permission_key)
                for p in (user.role.permissions or [])
            ]
        )
        return UserResponse(
            id=user.id,
            full_name=user.full_name,
            email=user.email,
            is_active=user.is_active,
            role=role_resp,
            permissions=permissions,
            created_at=user.created_at,
            updated_at=user.updated_at,
        )

    def signup_user(self, payload: SignupRequest, raw_body: dict | None = None) -> UserResponse:
        if raw_body and ("role" in raw_body or "role_name" in raw_body):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Specifying a role during signup is forbidden."
            )

        existing = self.user_repo.get_by_email(payload.email)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A user with this email address already exists."
            )

        role = self.user_repo.get_role_by_name("USER")
        if not role:
            role = self.user_repo.get_role_by_name("VIEWER")
            if not role:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Default role configuration is missing. Please initialize RBAC seed."
                )

        new_user = User(
            full_name=payload.full_name.strip(),
            email=payload.email.lower().strip(),
            password_hash=get_password_hash(payload.password),
            role_id=role.id,
            is_active=True,
        )
        created_user = self.user_repo.create(new_user)
        return self._build_user_response(created_user)

    def register_user(self, payload: RegisterRequest) -> UserResponse:
        existing = self.user_repo.get_by_email(payload.email)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A user with this email address already exists."
            )

        role_name = payload.role_name or "ML_ENGINEER"
        role = self.user_repo.get_role_by_name(role_name)
        if not role:
            # Fallback to VIEWER if requested role not found
            role = self.user_repo.get_role_by_name("VIEWER")
            if not role:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Default role configuration is missing. Please initialize RBAC seed."
                )

        new_user = User(
            full_name=payload.full_name.strip(),
            email=payload.email.lower().strip(),
            password_hash=get_password_hash(payload.password),
            role_id=role.id,
            is_active=True,
        )
        created_user = self.user_repo.create(new_user)
        return self._build_user_response(created_user)

    def authenticate_user(self, payload: LoginRequest) -> TokenResponse:
        user = self.user_repo.get_by_email(payload.email)
        if not user or not verify_password(payload.password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="This user account is inactive."
            )

        access_token = create_access_token(subject=str(user.id))
        refresh_token = create_refresh_token(subject=str(user.id))
        user_response = self._build_user_response(user)

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            user=user_response,
        )

    def refresh_access_token(self, refresh_token_str: str) -> TokenResponse:
        payload = decode_token(refresh_token_str)
        if not payload or payload.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired refresh token."
            )

        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token subject.")

        user = self.user_repo.get_by_id(user_id)
        if not user or not user.is_active:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or inactive.")

        new_access = create_access_token(subject=str(user.id))
        new_refresh = create_refresh_token(subject=str(user.id))
        user_response = self._build_user_response(user)

        return TokenResponse(
            access_token=new_access,
            refresh_token=new_refresh,
            token_type="bearer",
            user=user_response,
        )
