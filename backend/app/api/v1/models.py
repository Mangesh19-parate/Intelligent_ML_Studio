from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Body, Query
from fastapi.responses import StreamingResponse
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
from app.schemas.deployment import (
    DeploymentGateResponse,
    DeploymentGateApproveResponse,
    DeploymentResponse,
)
from app.repositories.experiment_repository import ExperimentRepository
from app.services.explainability_service import ExplainabilityService
from app.services.model_registry_service import ModelRegistryService
from app.services.deployment_gate_service import DeploymentGateService
from app.services.deployment_service import DeploymentService

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
    """
    service = ExplainabilityService(db)
    return service.local_shap_explanation(model_id=id, input_row=input_row)


@router.get(
    "/{id}/download",
    status_code=status.HTTP_200_OK,
    summary="Download trained model artifact serialized in pkl or joblib format (EXPORT permission required)",
)
def download_model(
    id: UUID,
    format: str = Query("joblib", pattern="^(joblib|pkl|pickle)$", description="Serialization format: pkl or joblib"),
    current_user: User = Depends(require_permission("EXPORT")),
    db: Session = Depends(get_db),
):
    """
    Loads the fitted pipeline artifact, re-verifies cryptographic SHA-256 integrity,
    and returns a downloadable file stream in the requested format.
    """
    registry = ModelRegistryService(db)
    buffer, filename, media_type = registry.download(model_id=id, format=format)
    return StreamingResponse(
        buffer,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get(
    "/{id}/deployment-gate",
    response_model=DeploymentGateResponse,
    status_code=status.HTTP_200_OK,
    summary="Check or retrieve latest deployment gate verification status (READ permission required)",
)
def get_deployment_gate(
    id: UUID,
    current_user: User = Depends(require_permission("READ")),
    db: Session = Depends(get_db),
):
    """
    Evaluates or retrieves the 6-condition pre-deployment verification gate.
    """
    gate_service = DeploymentGateService(db)
    return gate_service.get_latest_gate(model_id=id)


@router.post(
    "/{id}/deployment-gate/approve",
    response_model=DeploymentGateApproveResponse,
    status_code=status.HTTP_200_OK,
    summary="Approve deployment gate for a model (DEPLOY permission required)",
)
def approve_deployment_gate(
    id: UUID,
    current_user: User = Depends(require_permission("DEPLOY")),
    db: Session = Depends(get_db),
):
    """
    Re-evaluates gate checks fresh and sets user_approved = true.
    """
    gate_service = DeploymentGateService(db)
    gate = gate_service.approve(model_id=id, approved_by_user_id=current_user.id)
    return DeploymentGateApproveResponse(
        message="Model deployment gate approved successfully.",
        gate=gate,
    )


@router.post(
    "/{id}/deploy",
    response_model=DeploymentResponse,
    status_code=status.HTTP_200_OK,
    summary="Deploy a verified model into production (DEPLOY permission required)",
)
def deploy_model(
    id: UUID,
    current_user: User = Depends(require_permission("DEPLOY")),
    db: Session = Depends(get_db),
):
    """
    Provisions a LIVE deployment endpoint after verifying all 6 gate conditions.
    """
    deploy_service = DeploymentService(db)
    return deploy_service.deploy(model_id=id, user_id=current_user.id)
