from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import require_permission
from app.models.user import User
from app.services.workspace_analytics_service import WorkspaceAnalyticsService

router = APIRouter(prefix="/workspace", tags=["Workspace Analytics"])


@router.get(
    "/summary",
    status_code=status.HTTP_200_OK,
    summary="Get aggregated workspace summary metrics (READ permission required)",
)
def get_workspace_summary(
    current_user: User = Depends(require_permission("READ")),
    db: Session = Depends(get_db),
):
    """
    Returns workspace summary: total projects, projects by derived pipeline stage,
    datasets uploaded, experiments completed, models trained, models with passed gates,
    and live deployments.
    - Scoped to the user's projects unless user has MANAGE_USERS permission (ADMIN).
    """
    service = WorkspaceAnalyticsService(db)
    return service.get_summary(current_user)
