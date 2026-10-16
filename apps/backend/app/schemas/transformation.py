from typing import Literal, Optional
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict

# Strategy Types
NumericMissingStrategy = Literal["mean", "median", "arbitrary", "knn", "iterative", "end_tail", "none"]
CategoricalMissingStrategy = Literal["mode", "missing_category", "none"]
EncodingStrategy = Literal["ordinal", "one_hot", "drop_first", "label", "none"]
ScalingStrategy = Literal["standard", "minmax", "robust", "none"]
OutlierStrategy = Literal["zscore", "z_score", "iqr", "percentile", "winsorize", "winsorization", "none"]

ALLOWED_NUMERIC_MISSING = {"mean", "median", "arbitrary", "knn", "iterative", "end_tail", "none"}
ALLOWED_CATEGORICAL_MISSING = {"mode", "missing_category", "none"}
ALLOWED_ENCODING = {"ordinal", "one_hot", "drop_first", "label", "none"}
ALLOWED_SCALING = {"standard", "minmax", "robust", "none"}
ALLOWED_OUTLIER = {"zscore", "z_score", "iqr", "percentile", "winsorize", "winsorization", "none"}

class NumericalPipelineRecipe(BaseModel):
    imputer: str = "median"
    arbitrary_value: Optional[str] = None
    knn_neighbors: Optional[int] = None
    outlier_treatment: Optional[dict] = None
    scaler: str = "standard"

class CategoricalPipelineRecipe(BaseModel):
    imputer: str = "mode"
    nominal_encoder: str = "one_hot"
    ordinal_encoder: str = "ordinal"

class DatetimePipelineRecipe(BaseModel):
    parts: list[str] = Field(default_factory=lambda: ["year", "month", "day", "dayofweek", "is_weekend"])
    cyclical_sin_cos: bool = True

class TransformationRecipePayload(BaseModel):
    version: str = "1.0.0"
    leakage_safe: bool = True
    numerical_pipeline: NumericalPipelineRecipe = Field(default_factory=NumericalPipelineRecipe)
    categorical_pipeline: CategoricalPipelineRecipe = Field(default_factory=CategoricalPipelineRecipe)
    datetime_pipeline: DatetimePipelineRecipe = Field(default_factory=DatetimePipelineRecipe)

class TransformationRecipeResponse(BaseModel):
    project_id: UUID
    recipe: dict
    updated_columns_count: int
    message: str

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
