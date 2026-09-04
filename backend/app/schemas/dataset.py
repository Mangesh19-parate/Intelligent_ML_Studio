from uuid import UUID
from datetime import datetime
from decimal import Decimal
from typing import Literal, Any
from pydantic import BaseModel, ConfigDict, Field

DataTypeEnum = Literal["NUMERIC", "CATEGORICAL", "DATETIME", "MIXED"]

class DatasetColumnResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    dataset_id: UUID
    column_name: str
    data_type: DataTypeEnum
    unique_count: int
    missing_percentage: Decimal
    is_target: bool

class DatasetResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    project_id: UUID
    file_path: str
    version_number: int
    row_count: int
    column_count: int
    stage: str
    content_hash: str | None = None
    uploaded_by: UUID | None = None
    created_at: datetime

class DatasetDetailResponse(DatasetResponse):
    model_config = ConfigDict(from_attributes=True)
    columns: list[DatasetColumnResponse] = []

class DatasetSplitCreate(BaseModel):
    locked_test_pct: int = Field(default=20, ge=1, le=99, description="Percentage of data allocated to the locked test partition")
    seed: int | None = Field(default=None, description="Random seed for reproducibility. If None, a secure seed is generated.")

class DatasetSplitSummaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    dataset_id: UUID
    development_rows: int
    locked_test_rows: int
    locked_test_pct: int
    split_seed: int
    is_stratified: bool
    created_at: datetime

class DatasetDevelopmentPreviewResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    dataset_id: UUID
    total_development_rows: int
    preview_rows: list[dict[str, Any]]
    columns: list[str]
