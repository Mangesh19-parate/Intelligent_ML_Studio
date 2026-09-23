"""
Application Use Case: Start / Enqueue Experiment.
Enqueues a durable background task or starts asynchronous training execution.
"""

from uuid import UUID
from typing import Any
from sqlalchemy.orm import Session
from app.repositories.experiment_repository import ExperimentRepository
from app.tasks.experiment_tasks import submit_experiment_task
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

    # Submit task in DB
    cfg = exp.experiment_config or {}
    record = submit_experiment_task(
        project_id=str(exp.project_id),
        experiment_id=str(exp.id),
        algorithms=algorithms or cfg.get("algorithms", []),
        folds=folds or exp.fold_count or 5,
        seed=seed or exp.cv_seed or 42,
        selection_metric=selection_metric or exp.selection_metric,
        selection_direction=selection_direction or exp.selection_direction,
        deployment_threshold=deployment_threshold or cfg.get("deployment_threshold"),
        timeout_seconds=timeout_seconds,
        db=db,
    )

    exp_repo.update_status(exp.id, ExperimentState.TRAINING.value)

    return {
        "experiment_id": str(exp.id),
        "task_id": str(record.task_id),
        "task_state": "QUEUED",
        "status": ExperimentState.TRAINING.value,
    }
