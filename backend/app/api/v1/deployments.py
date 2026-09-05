from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import require_permission
from app.models.user import User
from app.models.deployment import Deployment
from app.models.prediction_log import PredictionLog
from app.schemas.deployment import (
    DeploymentResponse,
    DeploymentStatusUpdateRequest,
    PredictionLogResponse,
)
from app.services.deployment_service import DeploymentService

router = APIRouter(prefix="/deployments", tags=["Model Deployments"])


@router.get(
    "/{id}",
    response_model=DeploymentResponse,
    status_code=status.HTTP_200_OK,
    summary="Get deployment details (READ permission required)",
)
def get_deployment(
    id: UUID,
    current_user: User = Depends(require_permission("READ")),
    db: Session = Depends(get_db),
):
    service = DeploymentService(db)
    deployment = service.get_by_id(id)
    if not deployment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Deployment not found",
        )
    return deployment


@router.put(
    "/{id}/status",
    response_model=DeploymentResponse,
    status_code=status.HTTP_200_OK,
    summary="Update deployment status: PAUSED or RETIRED (DEPLOY permission required)",
)
def update_deployment_status(
    id: UUID,
    payload: DeploymentStatusUpdateRequest,
    current_user: User = Depends(require_permission("DEPLOY")),
    db: Session = Depends(get_db),
):
    """
    Transitions deployment status (e.g. LIVE -> PAUSED -> RETIRED).
    Enforces that RETIRED deployments cannot be reactivated.
    """
    service = DeploymentService(db)
    return service.update_status(deployment_id=id, target_status=payload.status)


@router.get(
    "/{id}/logs",
    response_model=list[PredictionLogResponse],
    status_code=status.HTTP_200_OK,
    summary="Get inference audit logs for a deployment (READ permission required)",
)
def get_deployment_logs(
    id: UUID,
    limit: int = Query(50, ge=1, le=500),
    current_user: User = Depends(require_permission("READ")),
    db: Session = Depends(get_db),
):
    logs = (
        db.query(PredictionLog)
        .filter(PredictionLog.deployment_id == id)
        .order_by(PredictionLog.requested_at.desc())
        .limit(limit)
        .all()
    )
    return logs
