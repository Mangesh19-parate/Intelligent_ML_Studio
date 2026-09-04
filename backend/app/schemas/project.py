from uuid import UUID
from datetime import datetime
from decimal import Decimal
from typing import Literal
from pydantic import BaseModel, Field, ConfigDict

TaskType = Literal["REGRESSION", "CLASSIFICATION", "UNDETERMINED"]

class ProjectCreate(BaseModel):
    project_name: str = Field(..., min_length=1, max_length=200)
    target_column: str | None = Field(default=None, max_length=150)

class ProjectUpdate(BaseModel):
    project_name: str | None = Field(default=None, min_length=1, max_length=200)
    task_type: TaskType | None = None
    target_column: str | None = Field(default=None, max_length=150)
    pipeline_stage: str | None = None

class TaskTypeUpdate(BaseModel):
    task_type: Literal["REGRESSION", "CLASSIFICATION"]

class ProjectResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    owner_id: UUID
    project_name: str
    task_type: str
    task_type_confidence: str | None = None
    target_column: str | None = None
    pipeline_stage: str
    data_quality_index: Decimal | None = None
    created_at: datetime
    updated_at: datetime
