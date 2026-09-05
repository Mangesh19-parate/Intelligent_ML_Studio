from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Body
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import require_permission
from app.models.user import User
from app.models.trained_model import TrainedModel
from app.schemas.model_metric import ModelMetricResponse
from app.schemas.explainability import (
    GlobalExplainabilityResponse,
    LocalExplainabilityResponse,
)
from app.repositories.experiment_repository import ExperimentRepository
from app.services.explainability_service import ExplainabilityService

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


@router.get(
    "/{id}/explainability",
    response_model=GlobalExplainabilityResponse,
    status_code=status.HTTP_200_OK,
    summary="Get global SHAP explanation summary for a trained model (READ permission required)",
)
def get_global_explainability(
    id: UUID,
    background_sample_size: int = 200,
    current_user: User = Depends(require_permission("READ")),
    db: Session = Depends(get_db),
):
    """
    Returns global SHAP summary (mean absolute SHAP per feature).
    Enforces caching: checks `explainability_summaries` table first.
    Returns 422 if model has no artifact (i.e. non-winning candidate).
    """
    service = ExplainabilityService(db)
    return service.global_shap_summary(model_id=id, background_sample_size=background_sample_size)


@router.post(
    "/{id}/explainability/local",
    response_model=LocalExplainabilityResponse,
    status_code=status.HTTP_200_OK,
    summary="Compute instance-level SHAP explanation for a given input row (READ permission required)",
)
def get_local_explainability(
    id: UUID,
    input_row: dict = Body(..., description="Feature-value dict matching the model input schema"),
    current_user: User = Depends(require_permission("READ")),
    db: Session = Depends(get_db),
):
    """
    Computes local SHAP explanation (contributions and base value) for an instance.
    Precursor to Day 10 deployment /predict/.../explain.
    """
    service = ExplainabilityService(db)
    return service.local_shap_explanation(model_id=id, input_row=input_row)
