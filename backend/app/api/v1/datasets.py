from uuid import UUID
from fastapi import APIRouter, Depends, UploadFile, File, status, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.dependencies import require_permission
from app.models.user import User
from app.schemas.dataset import (
    DatasetResponse,
    DatasetColumnResponse,
    DatasetDetailResponse,
)
from app.services.dataset_service import DatasetService
from app.services.project_service import ProjectService

router = APIRouter(tags=["Datasets"])

@router.post(
    "/projects/{id}/datasets",
    response_model=DatasetDetailResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload dataset and detect structural schema"
)
async def upload_dataset(
    id: UUID,
    file: UploadFile = File(...),
    current_user: User = Depends(require_permission("EDIT_DATA")),
    db: Session = Depends(get_db),
):
    # Verify project access
    project_service = ProjectService(db)
    project = project_service.get_project_by_id(id, current_user)

    # Read uploaded file content
    content = await file.read()
    if not content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty."
        )

    dataset_service = DatasetService(db)
    
    # 1. Structural upload (saves file and creates dataset record)
    dataset = dataset_service.upload(
        project_id=project.id,
        filename=file.filename or "dataset.csv",
        content=content,
        uploaded_by_id=current_user.id
    )

    # 2. Structural schema detection (creates dataset_columns records)
    columns = dataset_service.detect_structural_schema(dataset.id)

    column_responses = [
        DatasetColumnResponse.model_validate(col) for col in columns
    ]

    return DatasetDetailResponse(
        id=dataset.id,
        project_id=dataset.project_id,
        file_path=dataset.file_path,
        version_number=dataset.version_number,
        row_count=dataset.row_count,
        column_count=dataset.column_count,
        stage=dataset.stage,
        uploaded_by=dataset.uploaded_by,
        created_at=dataset.created_at,
        columns=column_responses,
    )

@router.get(
    "/projects/{id}/datasets",
    response_model=list[DatasetResponse],
    status_code=status.HTTP_200_OK,
    summary="List dataset versions for a project"
)
def list_project_datasets(
    id: UUID,
    current_user: User = Depends(require_permission("READ")),
    db: Session = Depends(get_db),
):
    project_service = ProjectService(db)
    project = project_service.get_project_by_id(id, current_user)
    
    dataset_service = DatasetService(db)
    return dataset_service.get_datasets_for_project(project.id)

@router.get(
    "/datasets/{id}/columns",
    response_model=list[DatasetColumnResponse],
    status_code=status.HTTP_200_OK,
    summary="Get structural column metadata for a dataset"
)
def get_dataset_columns(
    id: UUID,
    current_user: User = Depends(require_permission("READ")),
    db: Session = Depends(get_db),
):
    dataset_service = DatasetService(db)
    dataset = dataset_service.dataset_repo.get_by_id(id)
    if not dataset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dataset not found")

    # Verify project access
    project_service = ProjectService(db)
    project_service.get_project_by_id(dataset.project_id, current_user)

    return dataset_service.get_columns_for_dataset(dataset.id)
