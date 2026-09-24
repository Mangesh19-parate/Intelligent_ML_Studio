"""
Application Use Case: Run Experiment Execution (SRS §2.8-§2.12).
Orchestrates leak-free k-fold cross validation, multi-metric evaluation,
primary metric leaderboard sorting, and winning model artifact packaging.
"""

from typing import Any
from uuid import UUID
from sqlalchemy.orm import Session
from app.services.experiment_service import ExperimentService


def run_experiment_use_case(
    db: Session,
    project_id: UUID | str | None = None,
    algorithms: list[str] | None = None,
    folds: int = 5,
    seed: int | None = 42,
    threshold: float = 0.0,
    selection_metric: str | None = None,
    selection_direction: str | None = None,
    experiment_id: UUID | str | None = None,
    auto_finalize: bool = True,
    deployment_threshold: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Executes an end-to-end leak-free cross-validation experiment run.
    """
    service = ExperimentService(db)
    return service.run_experiment(
        project_id=project_id,
        algorithms=algorithms,
        folds=folds,
        seed=seed,
        threshold=threshold,
        selection_metric=selection_metric,
        selection_direction=selection_direction,
        experiment_id=experiment_id,
        auto_finalize=auto_finalize,
        deployment_threshold=deployment_threshold,
    )
