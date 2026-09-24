"""
Application Use Case: Verify Model Training Reproducibility (SRS §2.14).
Reruns model training under identical split, seed, and hyperparameter configuration
and verifies metric invariance within acceptable numerical tolerances.
"""

from typing import Any
from uuid import UUID
from sqlalchemy.orm import Session
from app.services.experiment_service import ExperimentService


def verify_reproducibility_use_case(
    db: Session,
    experiment_id: UUID | str,
    model_id: UUID | str | None = None,
) -> dict[str, Any]:
    """
    Executes audit verification of experiment reproducibility.
    """
    service = ExperimentService(db)
    return service.verify_reproducibility(
        experiment_id=experiment_id,
        model_id=model_id,
    )
