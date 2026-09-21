from datetime import datetime
from uuid import UUID
from typing import Any, Optional
from pydantic import BaseModel, Field


class StructuralGuaranteeItem(BaseModel):
    id: str
    title: str
    description: str
    invariant_rule: str
    is_guaranteed: bool = True


class PerExperimentSignals(BaseModel):
    fit_diagnosis: str = Field(..., description="GOOD_FIT, POTENTIAL_OVERFIT, POTENTIAL_UNDERFIT_WEAK_SIGNAL, INSUFFICIENT_DATA, NOT_EVALUATED")
    generalization_gap: Optional[float] = None
    evidence_strength: str = Field(..., description="STRONG, MODERATE, LIMITED, INSUFFICIENT_EVIDENCE, NOT_APPLIED")
    selected_features_count: int = 0
    total_features_count: int = 0
    artifact_checksum_status: str = Field(..., description="VERIFIED, MISMATCH, MISSING, PENDING")
    artifact_checksum: Optional[str] = None
    locked_test_status: str = Field(..., description="EVALUATED, CONSUMED, NOT_EVALUATED")
    locked_test_score: Optional[float] = None
    gate_status: str = Field(..., description="PASSED, BLOCKED, PENDING, NOT_EVALUATED")
    gate_conditions_passed: int = 0
    gate_conditions_total: int = 6


class RiskFlagItem(BaseModel):
    risk_type: str
    severity: str = Field(..., description="LOW, MEDIUM, HIGH, CRITICAL")
    finding: str
    description: str
    remediation: str


class ExperimentHealthResponse(BaseModel):
    experiment_id: UUID
    project_id: UUID
    status: str
    champion_model_id: Optional[UUID] = None
    champion_algorithm: Optional[str] = None
    selection_metric: str
    selection_direction: str
    structural_guarantees: list[StructuralGuaranteeItem]
    signals: PerExperimentSignals
    risks_flagged_count: int
    risks_summary: str
    risks: list[RiskFlagItem]
    overall_health: str = Field(..., description="HEALTHY, WARNING, CRITICAL")
    generated_at: datetime
