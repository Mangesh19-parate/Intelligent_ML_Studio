"""
Application Use Case: Evaluate Locked Test Partition (SRS §2.8, §2.12).
Evaluates the winning trained model on the strictly held-out locked test set.
Enforces single-use consumption and lineage recording.
"""

from typing import Any
from uuid import UUID
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.services.experiment_service import ExperimentService


def evaluate_locked_test_use_case(
    db: Session,
    experiment_id: UUID | str,
    model_id: UUID | str | None = None,
) -> dict[str, Any]:
    """
    Executes one-time locked test partition evaluation for an experiment's winning model.
    """
    service = ExperimentService(db)
    return service.evaluate_locked_test(
        experiment_id=experiment_id,
        model_id=model_id,
    )
