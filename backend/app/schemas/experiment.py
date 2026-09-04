from datetime import datetime
from uuid import UUID
from typing import Any
from pydantic import BaseModel, ConfigDict, Field
from app.schemas.model_metric import ModelMetricResponse

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
    selection_metric: str | None = Field(
        default=None,
        description="Primary metric for model selection (e.g. RMSE, macro_f1)",
    )
    selection_direction: str | None = Field(
        default=None,
        description="Direction for primary metric: MAXIMIZE or MINIMIZE",
    )

class TrainedModelResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, protected_namespaces=())


    id: UUID
    experiment_id: UUID
    algorithm_name: str
    hyperparameters: dict[str, Any] = Field(default_factory=dict)
    quick_cv_score: float | None = None
    fit_diagnosis: str | None = None
    model_selection_score: float | None = None
    status: str
    error_message: str | None = None
    created_at: datetime
    metrics: list[ModelMetricResponse] = Field(default_factory=list)

class ExperimentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    project_id: UUID
    status: str
    task_type: str | None = None
    fold_count: int | None = None
    cv_seed: int | None = None
    selection_metric: str | None = None
    selection_direction: str | None = "MAXIMIZE"
    selected_model_id: UUID | None = None
    locked_test_consumed: bool = False
    locked_test_consumed_at: datetime | None = None
    created_at: datetime
    completed_at: datetime | None = None
    trained_models: list[TrainedModelResponse] = []

class ExperimentCreateResponse(BaseModel):
    experiment_id: UUID
    status: str
    task_type: str | None = None
    fold_count: int | None = None
    cv_seed: int | None = None
    selection_metric: str | None = None
    selection_direction: str | None = None
    message: str

class TransformationSnapshotResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    experiment_id: UUID
    config_json: list[dict[str, Any]] | dict[str, Any]
    created_at: datetime | None = None

class FeatureSelectionSnapshotResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    experiment_id: UUID
    final_selected_features: list[str] | list[Any]
    final_selection_method: str
    created_at: datetime | None = None

class WinningModelLineageResponse(BaseModel):
    id: UUID
    algorithm_name: str
    artifact_path: str | None = None
    artifact_checksum: str | None = None
    preprocessing_snapshot_id: UUID | None = None
    feature_selection_snapshot_id: UUID | None = None

class ExperimentLineageResponse(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    experiment_id: UUID
    project_id: UUID
    status: str
    experiment_config: dict[str, Any] | None = None
    dataset_content_hash: str | None = None
    environment_capture_method: str | None = None
    code_version: str | None = None
    python_version: str | None = None
    sklearn_version: str | None = None
    numpy_version: str | None = None
    pandas_version: str | None = None
    model_library_versions: dict[str, Any] = Field(default_factory=dict)
    transformation_snapshot: dict[str, Any] | None = None
    feature_selection_snapshot: dict[str, Any] | None = None
    winning_model: dict[str, Any] | None = None
    created_at: datetime | str | None = None
    completed_at: datetime | str | None = None


