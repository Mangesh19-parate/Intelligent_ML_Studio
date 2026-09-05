from datetime import datetime
from uuid import UUID
from typing import Any
from pydantic import BaseModel, ConfigDict, Field

class GlobalExplainabilityResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, protected_namespaces=())

    id: UUID | None = None
    model_id: UUID
    shap_values: dict[str, float] = Field(
        description="Per-feature mean absolute SHAP value representing global feature importance"
    )
    background_sample_size: int = Field(
        description="Number of development partition samples used as background reference"
    )
    explainer_type: str = Field(
        description="Explainer architecture used: TREE, LINEAR, or KERNEL"
    )
    generated_at: datetime = Field(
        description="Timestamp when the explanation summary was computed and cached"
    )
    is_cached: bool = Field(
        default=False,
        description="Flag indicating whether this summary was returned from database cache"
    )

class LocalExplainabilityResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, protected_namespaces=())

    model_id: UUID
    base_value: float = Field(
        description="Explainer baseline / expected value (mean prediction over background sample)"
    )
    contributions: dict[str, float] = Field(
        description="Instance-level SHAP contribution values per feature"
    )
    prediction: float | None = Field(
        default=None,
        description="Model output for the provided input instance"
    )
    sum_contributions_plus_base: float = Field(
        description="Sum of all contributions plus base value (for additivity validation)"
    )
    explainer_type: str = Field(
        description="Explainer architecture used"
    )
