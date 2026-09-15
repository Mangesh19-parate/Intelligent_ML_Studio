import json
import hashlib
from uuid import UUID
from datetime import timedelta
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.core.security import (
    get_password_hash,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
)
from app.core.totp import TOTPService
from app.models.user import User
from app.models.revoked_token import RevokedToken
from app.repositories.user_repository import UserRepository
from app.schemas.auth import (
    SignupRequest,
    LoginRequest,
    TokenResponse,
    LoginResponse,
    UserResponse,
    RoleResponse,
    PermissionResponse,
    TwoFactorSetupResponse,
    TwoFactorConfirmRequest,
    TwoFactorVerifyLoginRequest,
    TwoFactorDisableRequest,
    TwoFactorStatusResponse,
)

class AuthService:
    def __init__(self, db: Session):
        self.db = db
        self.user_repo = UserRepository(db)

    def _build_user_response(self, user: User) -> UserResponse:
        effective_perms = set()
        if user.role and user.role.permissions:
            effective_perms.update(p.permission_key for p in user.role.permissions)
        if hasattr(user, "permission_overrides") and user.permission_overrides:
            for override in user.permission_overrides:
                if override.is_granted:
                    effective_perms.add(override.permission_key)
                else:
                    effective_perms.discard(override.permission_key)

        permissions = sorted(list(effective_perms))
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
            is_two_factor_enabled=bool(user.is_two_factor_enabled),
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
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Default USER role configuration is missing. Please initialize RBAC seed."
            )

        new_user = User(
            full_name=payload.full_name.strip(),
            email=payload.email.lower().strip(),
            password_hash=get_password_hash(payload.password),
            role_id=role.id,
            is_active=True,
            is_two_factor_enabled=False,
        )
        created_user = self.user_repo.create(new_user)
        return self._build_user_response(created_user)

    def authenticate_user(self, payload: LoginRequest) -> LoginResponse:
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

        # 2FA Enforcement Gate
        if user.is_two_factor_enabled and user.two_factor_secret:
            # Issue a short-lived (5 minute) 2FA challenge token
            two_factor_token = create_access_token(
                subject=str(user.id),
                expires_delta=timedelta(minutes=5),
                extra_claims={"purpose": "2fa_challenge"}
            )
            return LoginResponse(
                requires_2fa=True,
                two_factor_token=two_factor_token,
                token_type="bearer",
            )

        # Standard direct login
        access_token = create_access_token(subject=str(user.id))
        refresh_token = create_refresh_token(subject=str(user.id))
        user_response = self._build_user_response(user)

        return LoginResponse(
            requires_2fa=False,
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            user=user_response,
        )

    def setup_two_factor(self, user_id: UUID | str) -> TwoFactorSetupResponse:
        user = self.user_repo.get_by_id(str(user_id))
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

        secret = TOTPService.generate_secret()
        plain_backup_codes, _ = TOTPService.generate_backup_codes(count=8)
        otpauth_url = TOTPService.generate_otpauth_uri(secret=secret, account_name=user.email)

        return TwoFactorSetupResponse(
            secret=secret,
            otpauth_url=otpauth_url,
            backup_codes=plain_backup_codes,
        )

    def confirm_two_factor(self, user_id: UUID | str, payload: TwoFactorConfirmRequest) -> dict:
        user = self.user_repo.get_by_id(str(user_id))
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

        # Verify test code against the unconfirmed secret
        is_valid = TOTPService.verify_totp(payload.secret, payload.code)
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid verification code. Please check your authenticator app and try again."
            )

        # Hash backup codes for secure storage
        hashed_codes = [
            hashlib.sha256(code.replace("-", "").strip().upper().encode("utf-8")).hexdigest()
            for code in payload.backup_codes
            if code.strip()
        ]

        user.is_two_factor_enabled = True
        user.two_factor_secret = payload.secret.strip().replace(" ", "").upper()
        user.two_factor_backup_codes = json.dumps(hashed_codes)
        self.db.commit()

        return {"message": "Two-factor authentication enabled successfully."}

    def verify_two_factor_login(self, payload: TwoFactorVerifyLoginRequest) -> TokenResponse:
        token_payload = decode_token(payload.two_factor_token)
        if not token_payload or token_payload.get("purpose") != "2fa_challenge":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired two-factor authentication session. Please log in again."
            )

        user_id = token_payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token subject.")

        user = self.user_repo.get_by_id(user_id)
        if not user or not user.is_active or not user.is_two_factor_enabled or not user.two_factor_secret:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Two-factor authentication is not configured for this account."
            )

        # 1. First attempt TOTP verification
        is_totp_valid = TOTPService.verify_totp(user.two_factor_secret, payload.code)

        # 2. If TOTP fails, attempt backup recovery code
        if not is_totp_valid:
            existing_hashes = json.loads(user.two_factor_backup_codes or "[]")
            is_backup_valid, remaining_hashes = TOTPService.verify_and_consume_backup_code(payload.code, existing_hashes)
            if is_backup_valid:
                user.two_factor_backup_codes = json.dumps(remaining_hashes)
                self.db.commit()
            else:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid two-factor code or recovery key."
                )

        # 2FA passed — issue session tokens
        access_token = create_access_token(subject=str(user.id))
        refresh_token = create_refresh_token(subject=str(user.id))
        user_response = self._build_user_response(user)

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            user=user_response,
        )

    def disable_two_factor(self, user_id: UUID | str, payload: TwoFactorDisableRequest) -> dict:
        user = self.user_repo.get_by_id(str(user_id))
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

        if not verify_password(payload.password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect password. Password verification required to disable 2FA."
            )

        if user.two_factor_secret:
            is_totp_valid = TOTPService.verify_totp(user.two_factor_secret, payload.code)
            if not is_totp_valid:
                existing_hashes = json.loads(user.two_factor_backup_codes or "[]")
                is_backup_valid, remaining_hashes = TOTPService.verify_and_consume_backup_code(payload.code, existing_hashes)
                if not is_backup_valid:
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Invalid two-factor code. Accurate 2FA code is required to disable protection."
                    )

        user.is_two_factor_enabled = False
        user.two_factor_secret = None
        user.two_factor_backup_codes = None
        self.db.commit()

        return {"message": "Two-factor authentication disabled successfully."}

    def get_two_factor_status(self, user_id: UUID | str) -> TwoFactorStatusResponse:
        user = self.user_repo.get_by_id(str(user_id))
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

        hashed_codes = json.loads(user.two_factor_backup_codes or "[]")
        return TwoFactorStatusResponse(
            is_two_factor_enabled=bool(user.is_two_factor_enabled),
            remaining_backup_codes=len(hashed_codes),
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

        token_hash = hashlib.sha256(refresh_token_str.encode("utf-8")).hexdigest()
        
        # P1.3 REUSE DETECTION: Check if token was previously consumed
        existing_revocation = self.db.query(RevokedToken).filter(RevokedToken.token_hash == token_hash).first()
        if existing_revocation:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token reuse detected. This token was already rotated."
            )

        # Invalidate the consumed refresh token
        revoked_record = RevokedToken(
            token_hash=token_hash,
            user_id=user.id,
        )
        self.db.add(revoked_record)
        self.db.commit()

        # Issue rotated token pair
        new_access = create_access_token(subject=str(user.id))
        new_refresh = create_refresh_token(subject=str(user.id))
        user_response = self._build_user_response(user)

        return TokenResponse(
            access_token=new_access,
            refresh_token=new_refresh,
            token_type="bearer",
            user=user_response,
        )
