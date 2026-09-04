from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import require_permission
from app.models.user import User
from app.models.trained_model import TrainedModel
from app.schemas.model_metric import ModelMetricResponse
from app.repositories.experiment_repository import ExperimentRepository

router = APIRouter(prefix="/models", tags=["Models & Evaluation"])

@router.get(
    "/{id}/metrics",
    response_model=list[ModelMetricResponse],
    status_code=status.HTTP_200_OK,
    summary="Get full metric breakdown for a trained model (READ permission required)",
)
def get_model_metrics(
    id: UUID,
    current_user: User = Depends(require_permission("READ")),
    db: Session = Depends(get_db),
):
    exp_repo = ExperimentRepository(db)
    model = db.query(TrainedModel).filter(TrainedModel.id == id).first()
    if not model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Trained model not found"
        )

    metrics = exp_repo.get_model_metrics(id)
    return [
        ModelMetricResponse(
            id=m.id,
            model_id=m.model_id,
            metric_name=m.metric_name,
            split=m.split,
            metric_value=float(m.metric_value) if m.metric_value is not None else None,
            metric_json=m.metric_json,
            fold_index=m.fold_index,
            created_at=m.created_at,
        )
        for m in metrics
    ]
