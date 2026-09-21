from datetime import datetime
from uuid import UUID
from typing import Any, Optional
from pydantic import BaseModel, Field


class PermissionOverrideDetail(BaseModel):
    permission_key: str
    is_granted: bool
    created_at: Optional[datetime] = None


class UserAdminResponse(BaseModel):
    id: UUID
    full_name: str
    email: str
    role_name: str
    role_id: UUID
    is_active: bool
    created_at: Optional[datetime] = None
    effective_permissions: list[str] = Field(default_factory=list)
    permission_overrides: list[PermissionOverrideDetail] = Field(default_factory=list)


class UserCreateRequest(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=150)
    email: str
    password: str = Field(..., min_length=6)
    role_name: str = Field(default="USER")


class UserUpdateRequest(BaseModel):
    full_name: Optional[str] = None
    role_name: Optional[str] = None
    is_active: Optional[bool] = None


class PermissionOverrideRequest(BaseModel):
    permission_key: str = Field(..., description="Permission key e.g. DEPLOY, TRAIN, EDIT_DATA, READ, EXPORT, MANAGE_USERS")
    is_granted: bool = Field(..., description="True to explicitly grant, False to explicitly revoke")


class AlgorithmCatalogItem(BaseModel):
    id: str
    display_name: str
    task_type: str
    is_baseline: bool
    sklearn_class: str
    description: str


class MetricCatalogItem(BaseModel):
    id: str
    display_name: str
    task_type: str
    direction: Optional[str] = None
    is_primary_candidate: bool
    is_default: bool = False


class FeatureSelectionCatalog(BaseModel):
    strategy: str
    alpha: float
    k_min: int
    k_max: int
    min_applied_methods: int
    active_methods: list[str]
    deferred_methods: list[str]


class AuditLogItem(BaseModel):
    id: str
    event_type: str  # GATE_EVALUATION, PREDICTION, USER_CHANGE
    timestamp: datetime
    actor: Optional[str] = None
    target_id: Optional[str] = None
    status: str
    summary: str
    details: dict[str, Any] = Field(default_factory=dict)
