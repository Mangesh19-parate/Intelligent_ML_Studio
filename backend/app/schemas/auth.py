from uuid import UUID
from datetime import datetime
import re
from pydantic import BaseModel, Field, ConfigDict, field_validator

EMAIL_REGEX = re.compile(
    r"^[a-zA-Z0-9.!#$%&'*+/=?^_`{|}~-]+@[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)+$"
)

class PermissionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    permission_key: str

class RoleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    role_name: str
    description: str | None = None
    permissions: list[PermissionResponse] = []

class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    full_name: str
    email: str
    is_active: bool
    is_two_factor_enabled: bool = False
    role: RoleResponse
    permissions: list[str] = []
    created_at: datetime
    updated_at: datetime

class SignupRequest(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=150)
    email: str = Field(..., min_length=3, max_length=150)
    password: str = Field(..., min_length=6)

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        clean = v.strip().lower()
        if not EMAIL_REGEX.match(clean):
            raise ValueError("Invalid email address format. Please enter a valid email address.")
        return clean

class LoginRequest(BaseModel):
    email: str
    password: str

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        clean = v.strip().lower()
        if not EMAIL_REGEX.match(clean):
            raise ValueError("Invalid email address format. Please enter a valid email address.")
        return clean

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserResponse

class LoginResponse(BaseModel):
    requires_2fa: bool = False
    two_factor_token: str | None = None
    email_masked: str | None = None
    message: str | None = None
    access_token: str | None = None
    refresh_token: str | None = None
    token_type: str = "bearer"
    user: UserResponse | None = None

class RefreshTokenRequest(BaseModel):
    refresh_token: str | None = None

class TwoFactorSetupResponse(BaseModel):
    secret: str
    otpauth_url: str
    backup_codes: list[str]

class TwoFactorConfirmRequest(BaseModel):
    secret: str
    code: str
    backup_codes: list[str] = []

class TwoFactorVerifyLoginRequest(BaseModel):
    two_factor_token: str
    code: str

class TwoFactorResendRequest(BaseModel):
    two_factor_token: str

class TwoFactorDisableRequest(BaseModel):
    password: str
    code: str

class TwoFactorStatusResponse(BaseModel):
    is_two_factor_enabled: bool
    delivery_method: str = "EMAIL"
    remaining_backup_codes: int = 0

