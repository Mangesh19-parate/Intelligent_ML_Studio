from datetime import datetime
from uuid import UUID
from typing import Any
from pydantic import BaseModel, ConfigDict, Field

class ModelMetricResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, protected_namespaces=())

    id: UUID
    model_id: UUID
    metric_name: str
    split: str
    metric_value: float | None = None
    metric_json: Any | None = None
    fold_index: int | None = None
    created_at: datetime

class ModelMetricsSummary(BaseModel):
    train: dict[str, Any] = Field(default_factory=dict)
    validation_cv_mean: dict[str, Any] = Field(default_factory=dict)
    locked_test: dict[str, Any] = Field(default_factory=dict)
    diagnostic_rerun: dict[str, Any] = Field(default_factory=dict)

class LeaderboardEntryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, protected_namespaces=())


    id: UUID
    algorithm_name: str
    hyperparameters: dict[str, Any] = Field(default_factory=dict)
    fit_diagnosis: str | None = None
    model_selection_score: float | None = None
    primary_metric_name: str
    primary_metric_value: float | None = None
    secondary_metric_name: str | None = None
    secondary_metric_value: float | None = None
    is_winner: bool = False
    locked_test_score: float | None = None
    status: str
    error_message: str | None = None
    created_at: datetime
    metrics: list[ModelMetricResponse] = Field(default_factory=list)

class LeaderboardResponse(BaseModel):
    project_id: UUID
    experiment_id: UUID
    task_type: str
    selection_metric: str
    selection_direction: str
    selected_model_id: UUID | None = None
    locked_test_consumed: bool = False
    locked_test_consumed_at: datetime | None = None
    models: list[LeaderboardEntryResponse] = Field(default_factory=list)

class SelectionRecordResponse(BaseModel):
    experiment_id: UUID
    project_id: UUID
    selection_metric: str
    selection_direction: str
    selected_model_id: UUID | None = None
    locked_test_consumed: bool = False
    locked_test_consumed_at: datetime | None = None
