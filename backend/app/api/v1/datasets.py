from uuid import UUID
from fastapi import APIRouter, Depends, UploadFile, File, Form, status, HTTPException, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.dependencies import require_permission
from app.models.user import User
from app.schemas.dataset import (
    DatasetResponse,
    DatasetColumnResponse,
    DatasetDetailResponse,
    DatasetSplitCreate,
    DatasetSplitSummaryResponse,
    DatasetDevelopmentPreviewResponse,
)
from app.services.dataset_service import DatasetService
from app.services.dataset_split_service import DatasetSplitService
from app.services.project_service import ProjectService

router = APIRouter(tags=["Datasets"])

async def _process_dataset_upload(
    project_id: UUID,
    file: UploadFile,
    current_user: User,
    db: Session,
) -> DatasetDetailResponse:
    # Verify project access
    project_service = ProjectService(db)
    project = project_service.get_project_by_id(project_id, current_user)

    # Read uploaded file content
    content = await file.read()
    if not content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty."
        )

    dataset_service = DatasetService(db)
    
    # 1. Structural upload (computes SHA-256 hash, saves file and creates dataset record)
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
        content_hash=dataset.content_hash,
        uploaded_by=dataset.uploaded_by,
        created_at=dataset.created_at,
        columns=column_responses,
    )

@router.post(
    "/datasets/upload",
    response_model=DatasetDetailResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload dataset via form multipart (Day 1 standard)"
)
async def upload_dataset_form(
    project_id: UUID = Form(...),
    file: UploadFile = File(...),
    current_user: User = Depends(require_permission("EDIT_DATA")),
    db: Session = Depends(get_db),
):
    return await _process_dataset_upload(project_id, file, current_user, db)

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
    return await _process_dataset_upload(id, file, current_user, db)

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

@router.post(
    "/datasets/{id}/split",
    response_model=DatasetSplitSummaryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Development / Locked Test outer split partition"
)
def create_dataset_split(
    id: UUID,
    payload: DatasetSplitCreate,
    current_user: User = Depends(require_permission("EDIT_DATA")),
    db: Session = Depends(get_db),
):
    dataset_service = DatasetService(db)
    dataset = dataset_service.dataset_repo.get_by_id(id)
    if not dataset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dataset not found")

    # Verify project edit access
    project_service = ProjectService(db)
    project_service.get_project_by_id(dataset.project_id, current_user)

    split_service = DatasetSplitService(db)
    split_summary = split_service.create_outer_split(
        dataset_id=dataset.id,
        locked_test_pct=payload.locked_test_pct,
        seed=payload.seed
    )
    return DatasetSplitSummaryResponse.model_validate(split_summary)

@router.get(
    "/datasets/{id}/split",
    response_model=DatasetSplitSummaryResponse,
    status_code=status.HTTP_200_OK,
    summary="Get outer split summary for a dataset"
)
def get_dataset_split(
    id: UUID,
    current_user: User = Depends(require_permission("EDIT_DATA")),
    db: Session = Depends(get_db),
):
    dataset_service = DatasetService(db)
    dataset = dataset_service.dataset_repo.get_by_id(id)
    if not dataset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dataset not found")

    project_service = ProjectService(db)
    project_service.get_project_by_id(dataset.project_id, current_user)

    split_service = DatasetSplitService(db)
    summary = split_service.get_split_summary(dataset.id)
    if not summary:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No outer split exists for this dataset version yet."
        )

    return DatasetSplitSummaryResponse.model_validate(summary)

@router.get(
    "/datasets/{id}/development-preview",
    response_model=DatasetDevelopmentPreviewResponse,
    status_code=status.HTTP_200_OK,
    summary="Get preview of Development partition only (first ~10 rows)"
)
def get_development_preview(
    id: UUID,
    limit: int = Query(default=10, ge=1, le=50),
    current_user: User = Depends(require_permission("EDIT_DATA")),
    db: Session = Depends(get_db),
):
    dataset_service = DatasetService(db)
    dataset = dataset_service.dataset_repo.get_by_id(id)
    if not dataset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dataset not found")

    split_service = DatasetSplitService(db)
    preview = split_service.get_development_preview(dataset.id, limit=limit)
    return DatasetDevelopmentPreviewResponse.model_validate(preview)

@router.post(
    "/datasets/{id}/profile",
    response_model=dict,
    status_code=status.HTTP_200_OK,
    summary="Trigger Data Profiling, DQI, Task-Type Detection, and Diagnostics on Development data"
)
def profile_dataset(
    id: UUID,
    current_user: User = Depends(require_permission("EDIT_DATA")),
    db: Session = Depends(get_db),
):
    dataset_service = DatasetService(db)
    dataset = dataset_service.dataset_repo.get_by_id(id)
    if not dataset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dataset not found")

    project_service = ProjectService(db)
    project = project_service.get_project_by_id(dataset.project_id, current_user)

    # Enforce outer split guard before profiling
    from app.services.pipeline_guards import require_split_exists
    from app.services.data_profiling_service import DataProfilingService

    require_split_exists(db, project.id)

    profiling_service = DataProfilingService(db)
    report = profiling_service.generate_report(dataset.id)
    return report

@router.get(
    "/datasets/{id}/profile",
    response_model=dict,
    status_code=status.HTTP_200_OK,
    summary="Get stored Data Profiling report"
)
def get_dataset_profile(
    id: UUID,
    current_user: User = Depends(require_permission("READ")),
    db: Session = Depends(get_db),
):
    dataset_service = DatasetService(db)
    dataset = dataset_service.dataset_repo.get_by_id(id)
    if not dataset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dataset not found")

    project_service = ProjectService(db)
    project_service.get_project_by_id(dataset.project_id, current_user)

    from app.services.data_profiling_service import DataProfilingService
    profiling_service = DataProfilingService(db)
    report = profiling_service.get_report(dataset.id)
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No profiling report exists for this dataset yet."
        )

    return report

