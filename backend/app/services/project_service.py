from uuid import UUID
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.models.project import Project
from app.models.user import User
from app.repositories.project_repository import ProjectRepository
from app.schemas.project import ProjectCreate, ProjectUpdate, ProjectResponse

class ProjectService:
    def __init__(self, db: Session):
        self.db = db
        self.project_repo = ProjectRepository(db)

    def list_projects(self, current_user: User, skip: int = 0, limit: int = 100) -> list[Project]:
        user_permissions = {p.permission_key for p in current_user.role.permissions} if current_user.role and current_user.role.permissions else set()
        
        # If user has MANAGE_USERS permission, allow viewing all projects
        if "MANAGE_USERS" in user_permissions:
            return self.project_repo.get_all_ordered(skip=skip, limit=limit)
        
        # Otherwise, only return projects owned by the user
        return self.project_repo.get_by_owner(owner_id=current_user.id, skip=skip, limit=limit)

    def get_project_by_id(self, project_id: UUID | str, current_user: User) -> Project:
        project = self.project_repo.get_by_id(project_id)
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found"
            )

        user_permissions = {p.permission_key for p in current_user.role.permissions} if current_user.role and current_user.role.permissions else set()
        if "MANAGE_USERS" not in user_permissions and project.owner_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have access to this project"
            )

        return project

    def create_project(self, payload: ProjectCreate, current_user: User) -> Project:
        project = Project(
            owner_id=current_user.id,
            project_name=payload.project_name.strip(),
            task_type="UNDETERMINED",
            target_column=payload.target_column.strip() if payload.target_column else None,
            pipeline_stage="DATA",
            data_quality_index=None,  # Stays null on Day 1
        )
        return self.project_repo.create(project)

    def update_project(self, project_id: UUID | str, payload: ProjectUpdate, current_user: User) -> Project:
        project = self.get_project_by_id(project_id, current_user)
        
        if payload.project_name is not None:
            project.project_name = payload.project_name.strip()
        if payload.task_type is not None:
            project.task_type = payload.task_type
        if payload.target_column is not None:
            project.target_column = payload.target_column.strip() if payload.target_column else None
        if payload.pipeline_stage is not None:
            project.pipeline_stage = payload.pipeline_stage

        return self.project_repo.update(project)

    def delete_project(self, project_id: UUID | str, current_user: User) -> None:
        project = self.get_project_by_id(project_id, current_user)
        self.project_repo.delete(project)
