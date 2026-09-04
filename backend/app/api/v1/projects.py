from uuid import UUID
from fastapi import APIRouter, Depends, status, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.dependencies import require_permission
from app.models.user import User
from app.schemas.project import ProjectCreate, ProjectUpdate, ProjectResponse
from app.services.project_service import ProjectService

router = APIRouter(prefix="/projects", tags=["Projects"])

@router.post(
    "",
    response_model=ProjectResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new ML project"
)
def create_project(
    payload: ProjectCreate,
    current_user: User = Depends(require_permission("EDIT_DATA")),
    db: Session = Depends(get_db),
):
    service = ProjectService(db)
    return service.create_project(payload, current_user)

@router.get(
    "",
    response_model=list[ProjectResponse],
    status_code=status.HTTP_200_OK,
    summary="List user projects (or all projects if user has MANAGE_USERS permission)"
)
def list_projects(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    current_user: User = Depends(require_permission("READ")),
    db: Session = Depends(get_db),
):
    service = ProjectService(db)
    return service.list_projects(current_user, skip=skip, limit=limit)

@router.get(
    "/{id}",
    response_model=ProjectResponse,
    status_code=status.HTTP_200_OK,
    summary="Get project by ID"
)
def get_project(
    id: UUID,
    current_user: User = Depends(require_permission("READ")),
    db: Session = Depends(get_db),
):
    service = ProjectService(db)
    return service.get_project_by_id(id, current_user)

@router.put(
    "/{id}",
    response_model=ProjectResponse,
    status_code=status.HTTP_200_OK,
    summary="Update project details"
)
def update_project(
    id: UUID,
    payload: ProjectUpdate,
    current_user: User = Depends(require_permission("EDIT_DATA")),
    db: Session = Depends(get_db),
):
    service = ProjectService(db)
    return service.update_project(id, payload, current_user)

@router.delete(
    "/{id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a project"
)
def delete_project(
    id: UUID,
    current_user: User = Depends(require_permission("EDIT_DATA")),
    db: Session = Depends(get_db),
):
    service = ProjectService(db)
    service.delete_project(id, current_user)

@router.get(
    "/{id}/recommendations",
    response_model=list[dict],
    status_code=status.HTTP_200_OK,
    summary="List generated diagnostics recommendations for a project"
)
def get_project_recommendations(
    id: UUID,
    current_user: User = Depends(require_permission("READ")),
    db: Session = Depends(get_db),
):
    service = ProjectService(db)
    project = service.get_project_by_id(id, current_user)

    from app.models.recommendation import Recommendation
    recs = (
        db.query(Recommendation)
        .filter(Recommendation.project_id == project.id)
        .order_by(Recommendation.created_at.desc())
        .all()
    )
    return [
        {
            "id": str(r.id),
            "project_id": str(r.project_id),
            "finding": r.finding,
            "evidence": r.evidence,
            "recommended_action": r.recommended_action,
            "risk_note": r.risk_note,
            "confidence": r.confidence,
            "status": r.status,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in recs
    ]

@router.put(
    "/{id}/task-type",
    response_model=ProjectResponse,
    status_code=status.HTTP_200_OK,
    summary="Confirm or override task type for a project"
)
def update_project_task_type(
    id: UUID,
    payload: dict,
    current_user: User = Depends(require_permission("EDIT_DATA")),
    db: Session = Depends(get_db),
):
    service = ProjectService(db)
    project = service.get_project_by_id(id, current_user)

    chosen_task_type = payload.get("task_type")
    if chosen_task_type not in ["REGRESSION", "CLASSIFICATION"]:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="task_type must be either 'REGRESSION' or 'CLASSIFICATION'."
        )

    project_model = service.project_repo.get_by_id(project.id)
    project_model.task_type = chosen_task_type
    project_model.task_type_confidence = "MANUAL"
    db.add(project_model)
    db.commit()
    db.refresh(project_model)
    return ProjectResponse.model_validate(project_model)

