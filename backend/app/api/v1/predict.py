from uuid import UUID
from fastapi import APIRouter, Depends, Body, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.deployment import PredictResponse, PredictExplainResponse
from app.services.prediction_service import PredictionService

router = APIRouter(prefix="/predict", tags=["Model Serving & Inference"])


@router.post(
    "/{deployment_id}",
    response_model=PredictResponse,
    status_code=status.HTTP_200_OK,
    summary="Execute low-latency prediction against a LIVE deployment endpoint",
)
def predict(
    deployment_id: UUID,
    payload: dict = Body(..., description="Feature-value mapping matching the deployment input schema"),
    db: Session = Depends(get_db),
):
    """
    Decoupled fast prediction endpoint.
    - Rejects if deployment status is not LIVE.
    - Validates feature schema and records audit log.
    - Returns base prediction and class probabilities (if classification).
    
    ARCHITECTURAL NOTE (Day 11 / SRS §2.14 & §2.16):
    No API-key or separate external-consumer auth layer is being added — deployment status LIVE
    remains the only gate, per the SRS's explicit deferral of rate limiting/API-key throttling
    as out of scope for this prototype. Do not add auth machinery today.
    """
    service = PredictionService(db)
    response, _ = service.predict(deployment_id=deployment_id, payload=payload)
    return response


@router.post(
    "/{deployment_id}/explain",
    response_model=PredictExplainResponse,
    status_code=status.HTTP_200_OK,
    summary="Execute prediction with instance-level SHAP explanation breakdown",
)
def predict_with_explanation(
    deployment_id: UUID,
    payload: dict = Body(..., description="Feature-value mapping matching the deployment input schema"),
    db: Session = Depends(get_db),
):
    """
    Full prediction with local SHAP feature contributions.
    - Measures and logs prediction latency and SHAP explanation latency distinctly.
    """
    service = PredictionService(db)
    return service.predict_with_explanation(deployment_id=deployment_id, payload=payload)
