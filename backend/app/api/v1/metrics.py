"""
System Metrics & Observability Endpoint (P1.5).
Exposes task queue depth, task outcomes, and latency percentiles.
"""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.metrics import get_system_metrics

router = APIRouter(tags=["Metrics & Monitoring"])


@router.get(
    "/metrics",
    status_code=status.HTTP_200_OK,
    summary="Get real-time system metrics (queue depth, task counts, latency percentiles)"
)
def get_metrics_endpoint(db: Session = Depends(get_db)):
    return get_system_metrics(db)
