from typing import Literal, Optional
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict

# Strategy Types
NumericMissingStrategy = Literal["mean", "median", "arbitrary", "knn", "iterative", "none"]
CategoricalMissingStrategy = Literal["mode", "missing_category", "none"]
EncodingStrategy = Literal["ordinal", "one_hot", "none"]
ScalingStrategy = Literal["standard", "minmax", "robust", "none"]
OutlierStrategy = Literal["zscore", "iqr", "percentile", "winsorize", "none"]

ALLOWED_NUMERIC_MISSING = {"mean", "median", "arbitrary", "knn", "iterative", "none"}
ALLOWED_CATEGORICAL_MISSING = {"mode", "missing_category", "none"}
ALLOWED_ENCODING = {"ordinal", "one_hot", "none"}
ALLOWED_SCALING = {"standard", "minmax", "robust", "none"}
ALLOWED_OUTLIER = {"zscore", "iqr", "percentile", "winsorize", "none"}

class TransformationConfigUpdate(BaseModel):
    missing_value_strategy: Optional[str] = None
    encoding_strategy: Optional[str] = None
    scaling_strategy: Optional[str] = None
    outlier_strategy: Optional[str] = None
    is_active: Optional[bool] = None

class TransformationConfigResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: Optional[UUID] = None
    project_id: UUID
    column_name: str
    data_type: str  # NUMERIC, CATEGORICAL, DATETIME, MIXED
    missing_value_strategy: Optional[str] = "none"
    encoding_strategy: Optional[str] = "none"
    scaling_strategy: Optional[str] = "none"
    outlier_strategy: Optional[str] = "none"
    is_active: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class TransformationPreviewRequest(BaseModel):
    column: str = Field(..., description="Name of column to preview transformation for")
    sample_size: int = Field(default=200, ge=5, le=1000, description="Sample size of Development rows to preview")
    preview_seed: int = Field(default=42, description="Random seed for deterministic sample extraction")

class TransformationPreviewResponse(BaseModel):
    column: str
    sample_size: int
    preview_seed: int = 42
    data_type: str
    applied_strategies: dict
    before_values: list
    after_values: list
