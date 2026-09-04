from typing import Literal, Optional, Any
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict

TechniqueStatus = Literal["APPLIED", "SKIPPED", "FAILED"]
CVStrategy = Literal["KFOLD", "STRATIFIED_KFOLD"]

class FeatureSelectionRunRequest(BaseModel):
    n_splits: int = Field(default=5, ge=2, le=20, description="Number of cross-validation folds")
    cv_strategy: Optional[CVStrategy] = Field(default=None, description="CV split strategy (default STRATIFIED_KFOLD for classification, KFOLD for regression)")
    seed: int = Field(default=42, description="Random seed for fold splitting and estimators")
    threshold: float = Field(default=0.0, ge=0.0, le=1.0, description="Minimum avg rank score to mark is_selected=True")

class FeatureImportanceItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    column_name: str
    avg_rank_score: float
    is_selected: bool

class FeatureImportanceListResponse(BaseModel):
    project_id: UUID
    experiment_id: Optional[UUID] = None
    features: list[FeatureImportanceItemResponse]

class TechniqueScoreDetail(BaseModel):
    raw_score: Optional[float] = None
    rank: Optional[float] = None
    rank_score: Optional[float] = None
    status: TechniqueStatus
    status_reason: Optional[str] = None

class FeatureSelectionFoldResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    experiment_id: UUID
    fold_index: int
    selected_features: list[str]
    technique_scores: dict[str, dict[str, Any]]

class FeatureSelectionFoldListResponse(BaseModel):
    experiment_id: UUID
    project_id: UUID
    status: str
    created_at: datetime
    completed_at: Optional[datetime] = None
    fold_count: int
    folds: list[FeatureSelectionFoldResponse]

class FeatureSelectionThresholdUpdateRequest(BaseModel):
    threshold: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="Score threshold above which features are selected")
    selected_features: Optional[list[str]] = Field(default=None, description="Explicit list of selected feature column names")
