"""
Application Use Case: Get Experiment Model Leaderboard (SRS §2.8).
Returns ranked trained models for an experiment sorted by primary metric and optimization direction.
"""

from typing import Any
from uuid import UUID
from sqlalchemy.orm import Session
from app.services.experiment_service import ExperimentService


def get_leaderboard_use_case(
    db: Session,
    experiment_id: UUID | str,
) -> list[dict[str, Any]]:
    """
    Retrieves the authoritative leaderboard of evaluated models for an experiment.
    """
    service = ExperimentService(db)
    return service.get_leaderboard(experiment_id=experiment_id)
