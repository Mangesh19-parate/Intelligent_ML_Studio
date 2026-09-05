from datetime import datetime
from uuid import UUID
from typing import Any
from pydantic import BaseModel, ConfigDict, Field


class DeploymentGateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, protected_namespaces=())

    id: UUID
    model_id: UUID
    locked_test_evaluated: bool
    schema_locked: bool
    artifact_verified: bool
    lineage_complete: bool
    performance_threshold_passed: str
    user_approved: bool
    gate_passed: bool
    evaluated_at: datetime


class DeploymentGateApproveResponse(BaseModel):
    message: str
    gate: DeploymentGateResponse


class DeploymentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, protected_namespaces=())

    id: UUID
    model_id: UUID
    endpoint_path: str
    status: str
    deployed_by: UUID | None = None
    deployed_at: datetime
    log_retention_days: int


class DeploymentStatusUpdateRequest(BaseModel):
    status: str = Field(..., description="Target status: PAUSED or RETIRED (or LIVE if resuming from PAUSED)")


class PredictionLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    deployment_id: UUID
    request_id: UUID
    schema_hash: str
    payload_mode: str
    input_payload: dict[str, Any] | None = None
    prediction_output: Any | None = None
    latency_ms: int
    explanation_requested: bool
    explanation_latency_ms: int | None = None
    status: str
    requested_at: datetime


class PredictResponse(BaseModel):
    prediction: Any
    probabilities: dict[str, float] | list[float] | None = None
    latency_ms: int
    request_id: UUID


class PredictExplainResponse(BaseModel):
    prediction: Any
    probabilities: dict[str, float] | list[float] | None = None
    latency_ms: int
    explanation_latency_ms: int
    total_latency_ms: int
    request_id: UUID
    explanation: dict[str, Any]
