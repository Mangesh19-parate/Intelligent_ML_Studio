from datetime import datetime
from uuid import UUID
from typing import Any
from pydantic import BaseModel, ConfigDict, Field

class ExperimentCreateRequest(BaseModel):
    algorithms: list[str] = Field(
        ...,
        min_length=1,
        description="List of algorithm names to train in the experiment",
    )
    folds: int = Field(
        default=5,
        ge=2,
        le=20,
        description="Number of inner cross-validation folds",
    )
    seed: int | None = Field(
        default=None,
        description="Random seed for cross-validation splitting and estimators",
    )

class TrainedModelResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    experiment_id: UUID
    algorithm_name: str
    hyperparameters: dict[str, Any] = Field(default_factory=dict)
    quick_cv_score: float | None = None
    status: str
    error_message: str | None = None
    created_at: datetime

class ExperimentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    project_id: UUID
    status: str
    task_type: str | None = None
    fold_count: int | None = None
    cv_seed: int | None = None
    created_at: datetime
    completed_at: datetime | None = None
    trained_models: list[TrainedModelResponse] = []

class ExperimentCreateResponse(BaseModel):
    experiment_id: UUID
    status: str
    task_type: str | None = None
    fold_count: int | None = None
    cv_seed: int | None = None
    message: str
