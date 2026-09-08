from uuid import UUID as PyUUID
from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_permission
from app.models.user import User
from app.services.admin_service import AdminService
from app.schemas.admin import (
    UserAdminResponse,
    UserCreateRequest,
    UserUpdateRequest,
    PermissionOverrideRequest,
    AlgorithmCatalogItem,
    MetricCatalogItem,
    FeatureSelectionCatalog,
    AuditLogItem,
)

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.get(
    "/users",
    response_model=list[UserAdminResponse],
    status_code=status.HTTP_200_OK,
    summary="List all registered platform users with permissions and overrides",
)
def list_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("MANAGE_USERS")),
):
    service = AdminService(db)
    return service.list_users()


@router.post(
    "/users",
    response_model=UserAdminResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new user account with role",
)
def create_user(
    payload: UserCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("MANAGE_USERS")),
):
    service = AdminService(db)
    return service.create_user(payload)


@router.patch(
    "/users/{user_id}",
    response_model=UserAdminResponse,
    status_code=status.HTTP_200_OK,
    summary="Update a user's role, name, or active status",
)
def update_user(
    user_id: PyUUID,
    payload: UserUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("MANAGE_USERS")),
):
    service = AdminService(db)
    return service.update_user(user_id, payload)


@router.put(
    "/users/{user_id}/overrides",
    response_model=UserAdminResponse,
    status_code=status.HTTP_200_OK,
    summary="Set or update a granular permission override for a user (e.g. DEPLOY override)",
)
def set_permission_override(
    user_id: PyUUID,
    payload: PermissionOverrideRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("MANAGE_USERS")),
):
    service = AdminService(db)
    return service.set_permission_override(user_id, payload)


@router.delete(
    "/users/{user_id}/overrides/{permission_key}",
    response_model=UserAdminResponse,
    status_code=status.HTTP_200_OK,
    summary="Remove a permission override, reverting user to role defaults",
)
def delete_permission_override(
    user_id: PyUUID,
    permission_key: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("MANAGE_USERS")),
):
    service = AdminService(db)
    return service.delete_permission_override(user_id, permission_key)


@router.get(
    "/catalog/algorithms",
    response_model=list[AlgorithmCatalogItem],
    status_code=status.HTTP_200_OK,
    summary="Retrieve canonical algorithm catalog metadata",
)
def get_algorithm_catalog(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = AdminService(db)
    return service.get_algorithm_catalog()


@router.get(
    "/catalog/metrics",
    response_model=list[MetricCatalogItem],
    status_code=status.HTTP_200_OK,
    summary="Retrieve canonical metric catalog and optimization directions",
)
def get_metric_catalog(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = AdminService(db)
    return service.get_metric_catalog()


@router.get(
    "/catalog/features",
    response_model=FeatureSelectionCatalog,
    status_code=status.HTTP_200_OK,
    summary="Retrieve canonical feature selection heuristics and selector defaults",
)
def get_feature_catalog(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = AdminService(db)
    return service.get_feature_selection_catalog()


@router.get(
    "/audit-logs",
    response_model=list[AuditLogItem],
    status_code=status.HTTP_200_OK,
    summary="Retrieve platform-wide governance and inference audit logs",
)
def get_audit_logs(
    event_type: Optional[str] = Query(default=None, description="Filter by GATE_EVALUATION, INFERENCE_REQUEST, VALIDATION_FAILURE, PERMISSION_OVERRIDE"),
    limit: int = Query(default=100, ge=1, le=500),
    search: Optional[str] = Query(default=None, description="Search term across summaries or target IDs"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("MANAGE_USERS")),
):
    service = AdminService(db)
    return service.get_audit_logs(event_type=event_type, limit=limit, search=search)
