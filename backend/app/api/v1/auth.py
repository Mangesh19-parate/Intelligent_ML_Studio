from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.schemas.auth import (
    RegisterRequest,
    LoginRequest,
    TokenResponse,
    RefreshTokenRequest,
    UserResponse,
)
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user"
)
def register(
    payload: RegisterRequest,
    db: Session = Depends(get_db)
):
    service = AuthService(db)
    return service.register_user(payload)

@router.post(
    "/login",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="User login with JWT generation"
)
def login(
    payload: LoginRequest,
    db: Session = Depends(get_db)
):
    service = AuthService(db)
    return service.authenticate_user(payload)

@router.post(
    "/refresh",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Refresh access token"
)
def refresh(
    payload: RefreshTokenRequest,
    db: Session = Depends(get_db)
):
    service = AuthService(db)
    return service.refresh_access_token(payload.refresh_token)

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
