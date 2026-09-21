from fastapi import APIRouter, Depends, Request, Response, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.config import settings
from app.core.dependencies import get_current_user, require_permission
from app.models.user import User
from app.schemas.auth import (
    SignupRequest,
    LoginRequest,
    TokenResponse,
    LoginResponse,
    RefreshTokenRequest,
    UserResponse,
    TwoFactorSetupResponse,
    TwoFactorConfirmRequest,
    TwoFactorVerifyLoginRequest,
    TwoFactorResendRequest,
    TwoFactorDisableRequest,
    TwoFactorStatusResponse,
)
from app.core.rate_limiter import rate_limit_auth
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post(
    "/signup",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Sign up a new user (hardcodes role to USER, rejects any role key with 400)",
    dependencies=[Depends(rate_limit_auth(max_requests=10, window_seconds=60))]
)
@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register alias for signup",
    dependencies=[Depends(rate_limit_auth(max_requests=10, window_seconds=60))]
)
async def signup(
    request: Request,
    payload: SignupRequest,
    db: Session = Depends(get_db)
):
    try:
        raw_body = await request.json()
    except Exception:
        raw_body = {}
    service = AuthService(db)
    return service.signup_user(payload, raw_body=raw_body)

@router.post(
    "/login",
    response_model=LoginResponse,
    status_code=status.HTTP_200_OK,
    summary="User login with JWT generation and optional 2FA challenge gating",
    dependencies=[Depends(rate_limit_auth(max_requests=15, window_seconds=60))]
)
def login(
    payload: LoginRequest,
    response: Response,
    db: Session = Depends(get_db)
):
    service = AuthService(db)
    login_resp = service.authenticate_user(payload)
    
    # Only issue refresh cookie if 2FA is not required for this user
    if not login_resp.requires_2fa and login_resp.refresh_token:
        is_prod = (settings.ENV.lower() == "production")
        response.set_cookie(
            key="refresh_token",
            value=login_resp.refresh_token,
            httponly=True,
            secure=is_prod,
            samesite="lax",
            max_age=7 * 24 * 3600,
            path="/"
        )
    return login_resp

@router.post(
    "/2fa/verify-login",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Complete 2FA login challenge using 6-digit TOTP code or emergency backup key",
    dependencies=[Depends(rate_limit_auth(max_requests=15, window_seconds=60))]
)
def verify_2fa_login(
    payload: TwoFactorVerifyLoginRequest,
    response: Response,
    db: Session = Depends(get_db)
):
    service = AuthService(db)
    token_resp = service.verify_two_factor_login(payload)
    is_prod = (settings.ENV.lower() == "production")
    response.set_cookie(
        key="refresh_token",
        value=token_resp.refresh_token,
        httponly=True,
        secure=is_prod,
        samesite="lax",
        max_age=7 * 24 * 3600,
        path="/"
    )
    return token_resp

@router.post(
    "/2fa/resend",
    status_code=status.HTTP_200_OK,
    summary="Resend 6-digit verification code to the user's registered email address",
    dependencies=[Depends(rate_limit_auth(max_requests=10, window_seconds=60))]
)
def resend_2fa_otp(
    payload: TwoFactorResendRequest,
    db: Session = Depends(get_db)
):
    service = AuthService(db)
    return service.resend_two_factor_otp(payload)

@router.post(
    "/2fa/setup",
    response_model=TwoFactorSetupResponse,
    status_code=status.HTTP_200_OK,
    summary="Initialize 2FA setup: returns Base32 secret, otpauth URI, and emergency backup keys",
)
def setup_2fa(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = AuthService(db)
    return service.setup_two_factor(current_user.id)

@router.post(
    "/2fa/confirm",
    status_code=status.HTTP_200_OK,
    summary="Confirm and activate 2FA by providing a valid TOTP test code",
)
def confirm_2fa(
    payload: TwoFactorConfirmRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = AuthService(db)
    return service.confirm_two_factor(current_user.id, payload)

@router.post(
    "/2fa/disable",
    status_code=status.HTTP_200_OK,
    summary="Disable 2FA protection (requires password and valid code)",
)
def disable_2fa(
    payload: TwoFactorDisableRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = AuthService(db)
    return service.disable_two_factor(current_user.id, payload)

@router.get(
    "/2fa/status",
    response_model=TwoFactorStatusResponse,
    status_code=status.HTTP_200_OK,
    summary="Get current user 2FA enablement status and remaining backup code count",
)
def get_2fa_status(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = AuthService(db)
    return service.get_two_factor_status(current_user.id)

@router.post(
    "/refresh",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Refresh access token using body or HttpOnly cookie"
)
def refresh(
    request: Request,
    response: Response,
    payload: RefreshTokenRequest | None = None,
    db: Session = Depends(get_db)
):
    token_str = (payload.refresh_token if payload and payload.refresh_token else None) or request.cookies.get("refresh_token")
    if not token_str:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token required in request body or HttpOnly cookie."
        )
    service = AuthService(db)
    token_resp = service.refresh_access_token(token_str)
    is_prod = (settings.ENV.lower() == "production")
    response.set_cookie(
        key="refresh_token",
        value=token_resp.refresh_token,
        httponly=True,
        secure=is_prod,
        samesite="lax",
        max_age=7 * 24 * 3600,
        path="/"
    )
    return token_resp

@router.post(
    "/logout",
    status_code=status.HTTP_200_OK,
    summary="Logout, revoke refresh token server-side, and clear HttpOnly refresh cookie"
)
def logout(
    request: Request,
    response: Response,
    payload: RefreshTokenRequest | None = None,
    db: Session = Depends(get_db)
):
    token_str = (payload.refresh_token if payload and payload.refresh_token else None) or request.cookies.get("refresh_token")
    if token_str:
        service = AuthService(db)
        service.revoke_refresh_token(token_str)
    response.delete_cookie(key="refresh_token", path="/")
    return {"message": "Logged out successfully"}

@router.get(
    "/me",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Get current authenticated user profile"
)
def get_me(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = AuthService(db)
    return service._build_user_response(current_user)

@router.get(
    "/protected-demo",
    status_code=status.HTTP_200_OK,
    summary="Protected demonstration route requiring TRAIN permission"
)
def protected_demo(
    current_user: User = Depends(require_permission("TRAIN"))
):
    return {
        "status": "success",
        "message": "Permission TRAIN verified.",
        "user_id": str(current_user.id),
        "email": current_user.email,
    }

@router.get(
    "/deploy-demo",
    status_code=status.HTTP_200_OK,
    summary="Protected demonstration route requiring DEPLOY permission"
)
def deploy_demo(
    current_user: User = Depends(require_permission("DEPLOY"))
):
    return {
        "status": "success",
        "message": "Permission DEPLOY verified.",
        "user_id": str(current_user.id),
        "email": current_user.email,
    }
