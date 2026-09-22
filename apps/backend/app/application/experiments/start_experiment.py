"""
Application Use Case: Start / Enqueue Experiment.
Enqueues a durable background task or starts asynchronous training execution.
"""

from uuid import UUID
from typing import Any
from sqlalchemy.orm import Session
from app.repositories.experiment_repository import ExperimentRepository
from app.tasks.experiment_tasks import enqueue_experiment_task
from app.domain.experiment.state import ExperimentState
from app.domain.experiment.policies import validate_transition


def start_experiment_use_case(
    db: Session,
    experiment_id: UUID | str,
    algorithms: list[str] | None = None,
    folds: int | None = None,
    seed: int | None = None,
    selection_metric: str | None = None,
    selection_direction: str | None = None,
    deployment_threshold: float | None = None,
    timeout_seconds: int = 1800,
) -> dict[str, Any]:
    """
    Submits experiment for durable execution:
    1. Verifies current experiment state allows start/queue.
    2. Enqueues atomic durable_tasks record.
    3. Updates experiment state to QUEUED.
    """
    exp_repo = ExperimentRepository(db)
    exp = exp_repo.get_by_id(experiment_id)
    if not exp:
        raise ValueError(f"Experiment '{experiment_id}' not found.")

    curr_status = exp.status or "CREATED"
    if curr_status in ("COMPLETED", "RUNNING"):
        raise ValueError(f"Cannot start experiment in '{curr_status}' state.")

    # Enqueue task in DB
    task_id = enqueue_experiment_task(
        db=db,
        experiment_id=exp.id,
        timeout_seconds=timeout_seconds,
    )

    exp_repo.update_status(exp.id, "QUEUED")

    return {
        "experiment_id": str(exp.id),
        "task_id": str(task_id),
        "status": "QUEUED",
    }
