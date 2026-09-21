from uuid import UUID
from datetime import datetime
from typing import Any
from pydantic import BaseModel

class DQISubScores(BaseModel):
    missingness: float
    duplicate_rate: float
    outlier_prevalence: float | None = None
    type_consistency: float

class DQIEffectiveWeights(BaseModel):
    missingness: float
    duplicate_rate: float
    outlier_prevalence: float | None = None
    type_consistency: float

class DQIResponse(BaseModel):
    sub_scores: DQISubScores
    effective_weights: DQIEffectiveWeights
    overall_index: float

class TaskTypeSuggestionResponse(BaseModel):
    suggested_task_type: str
    confidence: str
    unique_count: int
    unique_ratio: float
    sample_values: list[Any]
    target_column: str | None = None
    is_ambiguous: bool

class CorrelationMatrixResponse(BaseModel):
    columns: list[str]
    matrix: list[list[float | None]]

class ProfilingReportResponse(BaseModel):
    dataset_id: str
    project_id: str
    dataset_split_id: str
    total_rows: int
    total_columns: int
    duplicate_row_count: int
    column_stats: dict[str, Any]
    correlation_matrix: CorrelationMatrixResponse
    missingness_summary: dict[str, Any]
    data_quality_index: DQIResponse
    task_type_suggestion: TaskTypeSuggestionResponse | None = None
    recommendations: list[dict[str, Any]] | None = None
    generated_at: str
