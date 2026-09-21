"""
System Metrics & Observability Endpoint (P1.5).
Exposes task queue depth, task outcomes, and latency percentiles.
"""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.dependencies import require_permission
from app.core.metrics import get_system_metrics
from app.models.user import User

router = APIRouter(tags=["Metrics & Monitoring"])


@router.get(
    "/metrics",
    status_code=status.HTTP_200_OK,
    summary="Get real-time system metrics (queue depth, task counts, latency percentiles) (READ permission required)"
)
def get_metrics_endpoint(
    current_user: User = Depends(require_permission("READ")),
    db: Session = Depends(get_db),
):
    return get_system_metrics(db)
