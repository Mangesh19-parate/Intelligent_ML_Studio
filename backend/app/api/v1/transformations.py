from uuid import UUID
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.dependencies import require_permission
from app.models.user import User
from app.schemas.transformation import (
    TransformationConfigUpdate,
    TransformationConfigResponse,
    TransformationPreviewRequest,
    TransformationPreviewResponse,
)
from app.services.transformation_service import TransformationService

router = APIRouter(prefix="/projects", tags=["Transformations"])

@router.get(
    "/{id}/transformations",
    response_model=list[TransformationConfigResponse],
    status_code=status.HTTP_200_OK,
    summary="List all column transformation configurations for a project",
)
def get_transformations(
    id: UUID,
    current_user: User = Depends(require_permission("READ")),
    db: Session = Depends(get_db),
):
    service = TransformationService(db)
    return service.get_project_configs(id)

@router.put(
    "/{id}/transformations/{column}",
    response_model=TransformationConfigResponse,
    status_code=status.HTTP_200_OK,
    summary="Update transformation strategies for a specific column",
)
def update_column_transformation(
    id: UUID,
    column: str,
    payload: TransformationConfigUpdate,
    current_user: User = Depends(require_permission("EDIT_DATA")),
    db: Session = Depends(get_db),
):
    service = TransformationService(db)
    return service.update_column_transformations(id, column, payload)

@router.post(
    "/{id}/transformations/preview",
    response_model=TransformationPreviewResponse,
    status_code=status.HTTP_200_OK,
    summary="Preview transformation effect on a temporary sample of Development partition data",
)
def preview_transformation(
    id: UUID,
    payload: TransformationPreviewRequest,
    current_user: User = Depends(require_permission("EDIT_DATA")),
    db: Session = Depends(get_db),
):
    service = TransformationService(db)
    return service.preview_transformation(id, payload.column, sample_size=payload.sample_size)
