from datetime import datetime
from uuid import UUID
from typing import Any
from pydantic import BaseModel, ConfigDict, Field


class PassportProjectInfo(BaseModel):
    model_config = ConfigDict(from_attributes=True, protected_namespaces=())
    id: UUID
    project_name: str
    task_type: str | None = None
    target_column: str | None = None
    created_at: datetime


class PassportDatasetInfo(BaseModel):
    model_config = ConfigDict(from_attributes=True, protected_namespaces=())
    id: UUID
    version_number: int
    row_count: int
    column_count: int
    stage: str
    content_hash: str | None = None


class PassportExperimentInfo(BaseModel):
    model_config = ConfigDict(from_attributes=True, protected_namespaces=())
    id: UUID
    task_type: str | None = None
    fold_count: int | None = None
    cv_seed: int | None = None
    selection_metric: str | None = None
    selection_direction: str = "MAXIMIZE"
    locked_test_consumed: bool = False
    locked_test_consumed_at: datetime | None = None
    code_version: str | None = None
    dataset_content_hash: str | None = None
    python_version: str | None = None
    sklearn_version: str | None = None
    numpy_version: str | None = None
    pandas_version: str | None = None
    model_library_versions: dict[str, Any] | None = None
    environment_capture_method: str | None = None
    created_at: datetime
    completed_at: datetime | None = None


class PassportPreprocessingInfo(BaseModel):
    model_config = ConfigDict(from_attributes=True, protected_namespaces=())
    snapshot_id: UUID
    config_json: Any | None = None
    created_at: datetime


class PassportFeatureSelectionInfo(BaseModel):
    model_config = ConfigDict(from_attributes=True, protected_namespaces=())
    snapshot_id: UUID
    final_selection_method: str | None = None
    final_selected_features: list[str] = Field(default_factory=list)
    feature_count: int = 0
    created_at: datetime


class PassportMetricItem(BaseModel):
    model_config = ConfigDict(from_attributes=True, protected_namespaces=())
    split: str
    metric_name: str
    metric_value: float | None = None
    metric_json: Any | None = None
    fold_index: int | None = None
    created_at: datetime


class PassportExplainabilityInfo(BaseModel):
    model_config = ConfigDict(from_attributes=True, protected_namespaces=())
    has_summary: bool = False
    summary_id: UUID | None = None
    top_features: list[dict[str, Any]] = Field(default_factory=list)
    background_sample_size: int | None = None
    computed_at: datetime | None = None


class PassportGovernanceInfo(BaseModel):
    model_config = ConfigDict(from_attributes=True, protected_namespaces=())
    gate_evaluated: bool = False
    gate_is_passing: bool = False
    gate_user_approved: bool = False
    gate_approved_by_user_id: UUID | None = None
    gate_approved_at: datetime | None = None
    gate_checks: list[dict[str, Any]] = Field(default_factory=list)
    is_deployed: bool = False
    deployment_id: UUID | None = None
    deployment_status: str | None = None
    endpoint_url: str | None = None
    deployed_at: datetime | None = None


class ModelPassportResponse(BaseModel):
    """
    Authoritative Model Technical Passport Response Schema (SRS v9 §13).
    Strict SELECT + render only; direct immutable read from stored records.
    """
    model_config = ConfigDict(from_attributes=True, protected_namespaces=())

    model_id: UUID
    algorithm_name: str
    hyperparameters: dict[str, Any] = Field(default_factory=dict)
    status: str
    is_selected_champion: bool = False
    model_selection_score: float | None = None
    fit_diagnosis: str | None = None
    decision_threshold: float | None = 0.5
    artifact_path: str | None = None
    artifact_checksum: str | None = None
    created_at: datetime

    project: PassportProjectInfo
    experiment: PassportExperimentInfo
    dataset: PassportDatasetInfo | None = None
    preprocessing: PassportPreprocessingInfo | None = None
    feature_selection: PassportFeatureSelectionInfo | None = None
    metrics: list[PassportMetricItem] = Field(default_factory=list)
    metrics_summary_by_split: dict[str, dict[str, float]] = Field(default_factory=dict)
    generalization_gap: float | None = None
    explainability: PassportExplainabilityInfo | None = None
    governance: PassportGovernanceInfo
