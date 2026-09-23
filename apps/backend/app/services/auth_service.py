import json
import time
import hmac
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
from app.services.email_service import EmailService
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
    TwoFactorResendRequest,
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

        if not EmailService.is_valid_email(payload.email):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Invalid email address format. Please enter a valid email address."
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
        if not EmailService.is_valid_email(payload.email):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Invalid email address format. Please enter a valid email address."
            )

        user = self.user_repo.get_by_email(payload.email.strip().lower())
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

        # 2FA Enforcement Gate (Email OTP flow)
        if user.is_two_factor_enabled:
            # Generate 6-digit Email OTP
            otp_code = EmailService.generate_otp(digits=6)
            expires_at = time.time() + 600  # 10 minute validity
            otp_hash = hashlib.sha256(otp_code.strip().encode("utf-8")).hexdigest()

            # Preserve any existing permanent TOTP secret
            totp_secret = None
            if user.two_factor_secret:
                if not user.two_factor_secret.startswith("{"):
                    totp_secret = user.two_factor_secret
                else:
                    try:
                        parsed = json.loads(user.two_factor_secret)
                        totp_secret = parsed.get("totp_secret")
                    except Exception:
                        totp_secret = None

            user.two_factor_secret = json.dumps({
                "type": "email_otp",
                "otp_hash": otp_hash,
                "expires_at": expires_at,
                "totp_secret": totp_secret,
            })
            self.db.commit()

            # Dispatch OTP to the user's verified email address
            sent = EmailService.send_otp_email(
                to_email=user.email,
                otp_code=otp_code,
                user_name=user.full_name,
                expire_minutes=10,
            )
            if not sent:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Failed to deliver two-factor verification code via email. Please check your SMTP settings or try again.",
                )

            # Issue a short-lived (10 minute) 2FA challenge token
            two_factor_token = create_access_token(
                subject=str(user.id),
                expires_delta=timedelta(minutes=10),
                extra_claims={"purpose": "2fa_challenge", "email": user.email},
                session_version=getattr(user, "session_version", 1) or 1,
            )
            masked_email = EmailService.mask_email(user.email)
            return LoginResponse(
                requires_2fa=True,
                two_factor_token=two_factor_token,
                email_masked=masked_email,
                message=f"A 6-digit verification code has been sent to {masked_email}.",
                token_type="bearer",
            )

        # Standard direct login if 2FA was explicitly disabled
        sv = getattr(user, "session_version", 1) or 1
        access_token = create_access_token(subject=str(user.id), session_version=sv)
        refresh_token = create_refresh_token(subject=str(user.id), session_version=sv)
        user_response = self._build_user_response(user)

        return LoginResponse(
            requires_2fa=False,
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            user=user_response,
        )

    def resend_two_factor_otp(self, payload: TwoFactorResendRequest) -> dict:
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
        if not user or not user.is_active:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User account is inactive or not found.")

        # Generate fresh 6-digit Email OTP
        otp_code = EmailService.generate_otp(digits=6)
        expires_at = time.time() + 600
        otp_hash = hashlib.sha256(otp_code.strip().encode("utf-8")).hexdigest()

        totp_secret = None
        if user.two_factor_secret:
            if not user.two_factor_secret.startswith("{"):
                totp_secret = user.two_factor_secret
            else:
                try:
                    parsed = json.loads(user.two_factor_secret)
                    totp_secret = parsed.get("totp_secret")
                except Exception:
                    totp_secret = None

        user.two_factor_secret = json.dumps({
            "type": "email_otp",
            "otp_hash": otp_hash,
            "expires_at": expires_at,
            "totp_secret": totp_secret,
        })
        self.db.commit()

        # Dispatch fresh email
        sent = EmailService.send_otp_email(
            to_email=user.email,
            otp_code=otp_code,
            user_name=user.full_name,
            expire_minutes=10,
        )
        if not sent:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Failed to deliver verification code via email. Please check your SMTP settings or try again.",
            )

        masked_email = EmailService.mask_email(user.email)
        return {
            "message": f"A new 6-digit verification code has been sent to {masked_email}.",
            "email_masked": masked_email,
        }

    def setup_two_factor(self, user_id: UUID | str) -> TwoFactorSetupResponse:
        user = self.user_repo.get_by_id(str(user_id))
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

        secret = TOTPService.generate_secret()
        plain_backup_codes, _ = TOTPService.generate_backup_codes(count=8)
        otpauth_url = TOTPService.generate_otpauth_uri(secret=secret, account_name=user.email)

        # Send test notification to user's email
        test_otp = EmailService.generate_otp(digits=6)
        EmailService.send_otp_email(user.email, test_otp, user.full_name, expire_minutes=10)

        return TwoFactorSetupResponse(
            secret=secret,
            otpauth_url=otpauth_url,
            backup_codes=plain_backup_codes,
        )

    def confirm_two_factor(self, user_id: UUID | str, payload: TwoFactorConfirmRequest) -> dict:
        user = self.user_repo.get_by_id(str(user_id))
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

        # Verify code
        is_valid = TOTPService.verify_totp(payload.secret, payload.code)
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid verification code. Please check your verification code and try again."
            )

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
        if not user or not user.is_active or not user.is_two_factor_enabled:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Two-factor authentication is not active for this account."
            )

        clean_code = payload.code.strip()
        verified = False
        totp_secret_to_restore = None

        # 1. Attempt Email OTP & TOTP Verification from user.two_factor_secret
        if user.two_factor_secret:
            secret_data = None
            if user.two_factor_secret.startswith("{"):
                try:
                    secret_data = json.loads(user.two_factor_secret)
                except Exception:
                    secret_data = None

            if isinstance(secret_data, dict):
                totp_secret_to_restore = secret_data.get("totp_secret")

                # 1a. Check Email OTP match
                if secret_data.get("otp_hash"):
                    incoming_hash = hashlib.sha256(clean_code.encode("utf-8")).hexdigest()
                    if hmac.compare_digest(incoming_hash, secret_data.get("otp_hash", "")):
                        if time.time() > secret_data.get("expires_at", 0):
                            raise HTTPException(
                                status_code=status.HTTP_401_UNAUTHORIZED,
                                detail="Verification code has expired. Please click 'Resend Code' to receive a new code."
                            )
                        verified = True

                # 1b. Check TOTP match if available
                if not verified and totp_secret_to_restore:
                    if TOTPService.verify_totp(totp_secret_to_restore, clean_code):
                        verified = True
            else:
                # Raw secret string
                if TOTPService.verify_totp(user.two_factor_secret, clean_code):
                    verified = True
                    totp_secret_to_restore = user.two_factor_secret

        # 2. Fallback to Emergency Backup Recovery Codes
        if not verified and user.two_factor_backup_codes:
            existing_hashes = json.loads(user.two_factor_backup_codes or "[]")
            is_backup_valid, remaining_hashes = TOTPService.verify_and_consume_backup_code(clean_code, existing_hashes)
            if is_backup_valid:
                verified = True
                user.two_factor_backup_codes = json.dumps(remaining_hashes)

        if not verified:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid verification code. Please enter the 6-digit OTP sent to your email."
            )

        # Successfully verified: restore permanent secret or clear single-use state
        user.two_factor_secret = totp_secret_to_restore
        self.db.commit()

        # Issue session tokens
        sv = getattr(user, "session_version", 1) or 1
        access_token = create_access_token(subject=str(user.id), session_version=sv)
        refresh_token = create_refresh_token(subject=str(user.id), session_version=sv)
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

        # Validate code if secret is present
        if user.two_factor_secret:
            secret_str = user.two_factor_secret
            if secret_str.startswith("{"):
                try:
                    parsed = json.loads(secret_str)
                    secret_str = parsed.get("totp_secret") or ""
                except Exception:
                    secret_str = ""

            if secret_str:
                is_totp_valid = TOTPService.verify_totp(secret_str, payload.code)
                if not is_totp_valid and user.two_factor_backup_codes:
                    existing_hashes = json.loads(user.two_factor_backup_codes or "[]")
                    is_backup_valid, _ = TOTPService.verify_and_consume_backup_code(payload.code, existing_hashes)
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
            delivery_method="EMAIL",
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

        token_session_version = payload.get("session_version")
        if token_session_version is not None and getattr(user, "session_version", None) is not None:
            if token_session_version < user.session_version:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Refresh token invalidated due to password reset or session revocation."
                )

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
        sv = getattr(user, "session_version", 1) or 1
        new_access = create_access_token(subject=str(user.id), session_version=sv)
        new_refresh = create_refresh_token(subject=str(user.id), session_version=sv)
        user_response = self._build_user_response(user)

        return TokenResponse(
            access_token=new_access,
            refresh_token=new_refresh,
            token_type="bearer",
            user=user_response,
        )

    def revoke_refresh_token(self, refresh_token_str: str) -> bool:
        """
        Revokes a refresh token on logout by recording its SHA-256 hash in RevokedToken table.
        """
        if not refresh_token_str or not isinstance(refresh_token_str, str):
            return False
        
        payload = decode_token(refresh_token_str)
        user_id = payload.get("sub")
        token_hash = hashlib.sha256(refresh_token_str.encode("utf-8")).hexdigest()

        existing = self.db.query(RevokedToken).filter(RevokedToken.token_hash == token_hash).first()
        if not existing:
            parsed_uid = None
            if user_id:
                try:
                    parsed_uid = PyUUID(str(user_id)) if not isinstance(user_id, PyUUID) else user_id
                except Exception:
                    parsed_uid = None
            if parsed_uid:
                revoked_record = RevokedToken(
                    token_hash=token_hash,
                    user_id=parsed_uid,
                )
                self.db.add(revoked_record)
                self.db.commit()
        return True
