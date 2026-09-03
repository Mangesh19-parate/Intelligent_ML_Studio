from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict

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
    role: RoleResponse
    permissions: list[str] = []
    created_at: datetime
    updated_at: datetime

class RegisterRequest(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=150)
    email: str = Field(..., min_length=3, max_length=150)
    password: str = Field(..., min_length=6)
    role_name: str | None = Field(default="ML_ENGINEER")

class LoginRequest(BaseModel):
    email: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserResponse

class RefreshTokenRequest(BaseModel):
    refresh_token: str
