from uuid import UUID
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.dependencies import require_permission
from app.models.user import User
from app.schemas.feature_selection import (
    FeatureSelectionRunRequest,
    FeatureImportanceListResponse,
    FeatureSelectionFoldListResponse,
    FeatureSelectionThresholdUpdateRequest,
)
from app.services.feature_selection_service import FeatureSelectionService

router = APIRouter(prefix="/projects", tags=["Feature Engineering"])

@router.post(
    "/{id}/feature-selection/run",
    response_model=FeatureImportanceListResponse,
    status_code=status.HTTP_200_OK,
    summary="Execute CV Rank-Aggregation Feature Selection Ensemble on Development Partition",
)
def run_feature_selection(
    id: UUID,
    payload: FeatureSelectionRunRequest,
    current_user: User = Depends(require_permission("TRAIN")),
    db: Session = Depends(get_db),
):
    service = FeatureSelectionService(db)
    return service.run_cv_feature_selection(
        project_id=id,
        n_splits=payload.n_splits,
        cv_strategy=payload.cv_strategy,
        seed=payload.seed,
        threshold=payload.threshold,
    )

@router.get(
    "/{id}/feature-importance",
    response_model=FeatureImportanceListResponse,
    status_code=status.HTTP_200_OK,
    summary="Get current aggregated feature importance scores and selection status",
)
def get_feature_importance(
    id: UUID,
    current_user: User = Depends(require_permission("READ")),
    db: Session = Depends(get_db),
):
    service = FeatureSelectionService(db)
    return service.get_feature_importance_scores(project_id=id)

@router.get(
    "/{id}/experiments/{experiment_id}/folds",
    response_model=FeatureSelectionFoldListResponse,
    status_code=status.HTTP_200_OK,
    summary="Get per-fold technique scores and selection results for an experiment",
)
def get_experiment_folds(
    id: UUID,
    experiment_id: UUID,
    current_user: User = Depends(require_permission("READ")),
    db: Session = Depends(get_db),
):
    service = FeatureSelectionService(db)
    return service.get_experiment_fold_results(project_id=id, experiment_id=experiment_id)

@router.put(
    "/{id}/feature-selection/threshold",
    response_model=FeatureImportanceListResponse,
    status_code=status.HTTP_200_OK,
    summary="Update feature selection via threshold adjustment or explicit feature toggles",
)
def update_feature_selection_threshold(
    id: UUID,
    payload: FeatureSelectionThresholdUpdateRequest,
    current_user: User = Depends(require_permission("EDIT_DATA")),
    db: Session = Depends(get_db),
):
    service = FeatureSelectionService(db)
    return service.update_feature_selection(
        project_id=id,
        threshold=payload.threshold,
        selected_features=payload.selected_features,
    )
