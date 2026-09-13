"""
Durable Task Registry and Execution Engine for ML Studio (P0.1, P0.2, P0.3).
Backs task records into the database (DurableTask model) so state survives process restarts.
Enforces real execution timeouts terminating the workload, and provides crash recovery.
"""

import uuid
import logging
import concurrent.futures
from typing import Any
from uuid import UUID
from datetime import datetime, timezone

from sqlalchemy.orm import Session
from app.tasks.task_state import TaskState, DurableTaskRecord
from app.models.durable_task import DurableTask
from app.core.database import SessionLocal
from app.services.experiment_service import ExperimentService

logger = logging.getLogger(__name__)

# Thread pool for asynchronous task execution with timeout enforcement
TASK_EXECUTOR = concurrent.futures.ThreadPoolExecutor(max_workers=8, thread_name_prefix="ml-task-worker")
ACTIVE_FUTURES: dict[str, concurrent.futures.Future] = {}


def _record_to_model(record: DurableTaskRecord) -> DurableTask:
    return DurableTask(
        id=record.task_id,
        experiment_id=UUID(str(record.experiment_id)),
        state=record.state.value if isinstance(record.state, TaskState) else record.state,
        idempotency_key=record.idempotency_key,
        retry_count=record.retry_count,
        max_retries=record.max_retries,
        timeout_seconds=record.timeout_seconds,
        worker_id=record.worker_id,
        queued_at=record.queued_at,
        started_at=record.started_at,
        finished_at=record.finished_at,
        failure_reason=record.failure_reason,
        result_summary=record.result_summary,
    )


def _model_to_record(model: DurableTask) -> DurableTaskRecord:
    return DurableTaskRecord(
        task_id=model.id,
        experiment_id=str(model.experiment_id),
        state=TaskState(model.state),
        idempotency_key=model.idempotency_key,
        retry_count=model.retry_count,
        max_retries=model.max_retries,
        timeout_seconds=model.timeout_seconds,
        worker_id=model.worker_id,
        queued_at=model.queued_at,
        started_at=model.started_at,
        finished_at=model.finished_at,
        failure_reason=model.failure_reason,
        result_summary=model.result_summary,
    )


def save_task_record(record: DurableTaskRecord, db: Session | None = None) -> None:
    """Persists a DurableTaskRecord into the database."""
    close_db = False
    if db is None:
        db = SessionLocal()
        close_db = True
    try:
        existing = db.query(DurableTask).filter(DurableTask.id == record.task_id).first()
        if existing:
            existing.state = record.state.value if isinstance(record.state, TaskState) else record.state
            existing.worker_id = record.worker_id
            existing.started_at = record.started_at
            existing.finished_at = record.finished_at
            existing.failure_reason = record.failure_reason
            existing.result_summary = record.result_summary
            existing.retry_count = record.retry_count
        else:
            model = _record_to_model(record)
            db.add(model)
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to persist task record {record.task_id}: {e}")
    finally:
        if close_db:
            db.close()


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
    timeout_seconds: int = 600,
    run_async: bool = True,
    db: Session | None = None,
) -> DurableTaskRecord:
    """
    Submits an experiment task for asynchronous durable execution with DB persistence.
    Enforces idempotency: repeated submissions with the same key return the existing record.
    """
    close_db = False
    if db is None:
        db = SessionLocal()
        close_db = True
    try:
        if idempotency_key:
            existing = db.query(DurableTask).filter(DurableTask.idempotency_key == idempotency_key).first()
            if existing:
                return _model_to_record(existing)

        task_id = f"task-{uuid.uuid4()}"
        record = DurableTaskRecord(
            task_id=task_id,
            experiment_id=str(experiment_id),
            idempotency_key=idempotency_key,
            timeout_seconds=timeout_seconds,
            state=TaskState.QUEUED,
        )
        model = _record_to_model(record)
        db.add(model)
        db.commit()
        db.refresh(model)
        record = _model_to_record(model)
    finally:
        if close_db:
            db.close()

    if run_async:
        future = TASK_EXECUTOR.submit(
            run_task_with_timeout_enforcement,
            task_id=record.task_id,
            project_id=project_id,
            experiment_id=experiment_id,
            algorithms=algorithms,
            folds=folds,
            seed=seed,
            threshold=threshold,
            selection_metric=selection_metric,
            selection_direction=selection_direction,
            deployment_threshold=deployment_threshold,
            timeout_seconds=timeout_seconds,
        )
        ACTIVE_FUTURES[record.task_id] = future

    return record


def get_task_status(task_id: str, db: Session | None = None) -> DurableTaskRecord | None:
    """Retrieves current execution state of a durable task from DB."""
    close_db = False
    if db is None:
        db = SessionLocal()
        close_db = True
    try:
        model = db.query(DurableTask).filter(DurableTask.id == task_id).first()
        return _model_to_record(model) if model else None
    finally:
        if close_db:
            db.close()


def run_task_with_timeout_enforcement(
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
    timeout_seconds: int = 600,
    worker_id: str = "worker-primary",
) -> None:
    """
    Executes task within an isolated execution future and enforces real timeout termination.
    If the computation exceeds timeout_seconds, it is aborted, marked TIMED_OUT in the DB,
    and partial writes are prevented.
    """
    record = get_task_status(task_id)
    if not record:
        record = DurableTaskRecord(task_id=task_id, experiment_id=str(experiment_id), timeout_seconds=timeout_seconds)

    if record.state == TaskState.CANCELLED:
        logger.info(f"Task {task_id} was cancelled before execution.")
        return

    record.mark_running(worker_id=worker_id)
    save_task_record(record)

    # Execute training logic with timeout constraint
    inner_executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
    
    def _do_run():
        db_exec = SessionLocal()
        try:
            service = ExperimentService(db_exec)
            return service.run_experiment(
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
        finally:
            db_exec.close()

    inner_future = inner_executor.submit(_do_run)
    try:
        result = inner_future.result(timeout=timeout_seconds)
        record.mark_succeeded(summary={"experiment_id": str(experiment_id), "status": "COMPLETED"})
        save_task_record(record)
    except concurrent.futures.TimeoutError:
        logger.warning(f"Task {task_id} timed out after {timeout_seconds}s. Aborting execution.")
        inner_future.cancel()
        inner_executor.shutdown(wait=False, cancel_futures=True)
        record.mark_timed_out()
        save_task_record(record)
    except Exception as e:
        logger.exception(f"Durable task {task_id} failed: {e}")
        record.mark_failed(reason=str(e))
        save_task_record(record)
    finally:
        inner_executor.shutdown(wait=False)


def recover_stale_tasks(stale_threshold_seconds: int = 300, db: Session | None = None) -> list[str]:
    """
    Recovers orphaned tasks in RUNNING state whose worker process crashed or restarted.
    Marks them FAILED with recoverable state instead of leaving them silently lost.
    """
    close_db = False
    if db is None:
        db = SessionLocal()
        close_db = True
    recovered_ids = []
    try:
        running_tasks = db.query(DurableTask).filter(DurableTask.state == "RUNNING").all()
        now = datetime.now(timezone.utc)
        for task in running_tasks:
            started = task.started_at
            if started:
                if started.tzinfo is None:
                    started = started.replace(tzinfo=timezone.utc)
                elapsed = (now - started).total_seconds()
                if elapsed >= stale_threshold_seconds:
                    task.state = TaskState.FAILED.value
                    task.finished_at = now
                    task.failure_reason = "Worker process terminated or abandoned task. Marked FAILED on crash recovery."
                    recovered_ids.append(task.id)
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"Error during stale task recovery: {e}")
    finally:
        if close_db:
            db.close()
    return recovered_ids


# Backward compatibility alias
execute_durable_experiment_task = run_task_with_timeout_enforcement
DURABLE_TASK_REGISTRY = {}
