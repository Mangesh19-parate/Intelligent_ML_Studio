from uuid import UUID
from datetime import datetime
from typing import Literal
from pydantic import BaseModel, ConfigDict

RecommendationConfidence = Literal["HIGH", "MEDIUM", "LOW"]

class RecommendationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    project_id: UUID
    finding: str
    evidence: str
    recommended_action: str
    risk_note: str
    confidence: str
    status: str
    created_at: datetime
