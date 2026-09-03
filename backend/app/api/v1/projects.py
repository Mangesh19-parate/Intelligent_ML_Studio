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
