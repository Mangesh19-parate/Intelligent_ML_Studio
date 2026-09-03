from uuid import UUID
from datetime import datetime
from decimal import Decimal
from typing import Literal
from pydantic import BaseModel, ConfigDict

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
    uploaded_by: UUID | None = None
    created_at: datetime

class DatasetDetailResponse(DatasetResponse):
    model_config = ConfigDict(from_attributes=True)
    columns: list[DatasetColumnResponse] = []
