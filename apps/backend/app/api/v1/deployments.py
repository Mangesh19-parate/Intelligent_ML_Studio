from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import require_permission, verify_project_ownership
from app.models.user import User
from app.models.deployment import Deployment
from app.models.prediction_log import PredictionLog
from app.schemas.deployment import (
    DeploymentResponse,
    DeploymentStatusUpdateRequest,
    DeploymentRollbackRequest,
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
    verify_project_ownership(deployment.model.experiment.project_id, current_user, db)
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
    deployment = service.get_by_id(id)
    if not deployment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Deployment not found",
        )
    verify_project_ownership(deployment.model.experiment.project_id, current_user, db)
    return service.update_status(deployment_id=id, target_status=payload.status)


@router.post(
    "/{id}/rollback",
    response_model=DeploymentResponse,
    status_code=status.HTTP_200_OK,
    summary="Rollback deployment to a previous target deployment (DEPLOY permission required)",
)
def rollback_deployment(
    id: UUID,
    payload: DeploymentRollbackRequest,
    current_user: User = Depends(require_permission("DEPLOY")),
    db: Session = Depends(get_db),
):
    """
    Rolls back current deployment to a previous target deployment's model version.
    Retires current deployment and provisions a new live deployment for the target model.
    """
    service = DeploymentService(db)
    deployment = service.get_by_id(id)
    if not deployment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Deployment not found",
        )
    verify_project_ownership(deployment.model.experiment.project_id, current_user, db)

    target_deployment = service.get_by_id(payload.target_deployment_id)
    if not target_deployment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Target deployment not found",
        )
    verify_project_ownership(target_deployment.model.experiment.project_id, current_user, db)

    return service.rollback_to_deployment(
        current_deployment_id=id,
        target_deployment_id=payload.target_deployment_id,
        user_id=current_user.id,
        reason=payload.reason,
    )


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
    service = DeploymentService(db)
    deployment = service.get_by_id(id)
    if not deployment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Deployment not found",
        )
    verify_project_ownership(deployment.model.experiment.project_id, current_user, db)

    logs = (
        db.query(PredictionLog)
        .filter(PredictionLog.deployment_id == id)
        .order_by(PredictionLog.requested_at.desc())
        .limit(limit)
        .all()
    )
    return logs


@router.get(
    "/{id}/monitoring",
    status_code=status.HTTP_200_OK,
    summary="Get aggregated deployment monitoring dashboard metrics (READ permission required)",
)
def get_deployment_monitoring(
    id: UUID,
    lookback_hours: int = Query(24, ge=1, le=720),
    log_limit: int = Query(50, ge=1, le=200),
    current_user: User = Depends(require_permission("READ")),
    db: Session = Depends(get_db),
):
    """
    Returns volume-over-time, latency summary (base vs explained), error rate with validation/server breakdown,
    and recent inference logs.
    """
    service = DeploymentService(db)
    deployment = service.get_by_id(id)
    if not deployment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Deployment not found",
        )
    verify_project_ownership(deployment.model.experiment.project_id, current_user, db)

    from app.services.monitoring_service import MonitoringService
    monitoring_service = MonitoringService(db)
    return monitoring_service.get_monitoring_dashboard(
        deployment_id=id,
        lookback_hours=lookback_hours,
        log_limit=log_limit,
    )

