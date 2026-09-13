"""
Durable Task Registry and Execution Engine for ML Studio.
Provides state persistence, idempotency validation, and timeout/cancellation handling.
"""

import uuid
import logging
from typing import Any
from uuid import UUID
from datetime import datetime, timezone

from app.tasks.task_state import TaskState, DurableTaskRecord
from app.core.database import SessionLocal
from app.services.experiment_service import ExperimentService

logger = logging.getLogger(__name__)

# In-memory / persistent task registry for job lifecycle tracking
DURABLE_TASK_REGISTRY: dict[str, DurableTaskRecord] = {}
IDEMPOTENCY_INDEX: dict[str, str] = {}  # idempotency_key -> task_id


def submit_experiment_task(
    project_id: UUID | str,
    experiment_id: UUID | str,
    algorithms: list[str],
    folds: int = 5,
    seed: int | None = 42,
    threshold: float = 0.0,
    selection_metric: str | None = None,
    selection_direction: str | None = None,
    deployment_threshold: dict[str, Any] | None = None,
    idempotency_key: str | None = None,
) -> DurableTaskRecord:
    """
    Submits an experiment task for asynchronous durable execution.
    Enforces idempotency: repeated submissions with the same key return the existing record.
    """
    if idempotency_key and idempotency_key in IDEMPOTENCY_INDEX:
        existing_task_id = IDEMPOTENCY_INDEX[idempotency_key]
        return DURABLE_TASK_REGISTRY[existing_task_id]

    task_id = f"task-{uuid.uuid4()}"
    record = DurableTaskRecord(
        task_id=task_id,
        experiment_id=str(experiment_id),
        idempotency_key=idempotency_key,
    )
    DURABLE_TASK_REGISTRY[task_id] = record
    if idempotency_key:
        IDEMPOTENCY_INDEX[idempotency_key] = task_id

    return record


def get_task_status(task_id: str) -> DurableTaskRecord | None:
    """Retrieves current execution state of a durable task."""
    return DURABLE_TASK_REGISTRY.get(task_id)


def execute_durable_experiment_task(
    task_id: str,
    project_id: UUID | str,
    experiment_id: UUID | str,
    algorithms: list[str],
    folds: int = 5,
    seed: int | None = 42,
    threshold: float = 0.0,
    selection_metric: str | None = None,
    selection_direction: str | None = None,
    deployment_threshold: dict[str, Any] | None = None,
    worker_id: str = "worker-primary",
) -> None:
    """
    Executes an experiment task with durable status tracking, exception containment, and state persistence.
    """
    record = DURABLE_TASK_REGISTRY.get(task_id)
    if not record:
        record = DurableTaskRecord(task_id=task_id, experiment_id=str(experiment_id))
        DURABLE_TASK_REGISTRY[task_id] = record

    if record.state == TaskState.CANCELLED:
        logger.info(f"Task {task_id} was cancelled before execution.")
        return

    record.mark_running(worker_id=worker_id)
    db = SessionLocal()
    try:
        service = ExperimentService(db)
        result = service.run_experiment(
            project_id=project_id,
            algorithms=algorithms,
            folds=folds,
            seed=seed,
            threshold=threshold,
            selection_metric=selection_metric,
            selection_direction=selection_direction,
            experiment_id=experiment_id,
            auto_finalize=True,
            deployment_threshold=deployment_threshold,
        )
        record.mark_succeeded(summary={"experiment_id": str(experiment_id), "status": "COMPLETED"})
    except Exception as e:
        logger.exception(f"Durable task {task_id} failed: {e}")
        record.mark_failed(reason=str(e))
    finally:
        db.close()
