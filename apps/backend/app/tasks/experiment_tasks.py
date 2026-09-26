"""
Durable Task Registry and Execution Engine for ML Studio (P0.1, P0.2, P0.3, P1.1).
Backs task records into the database (DurableTask model) so state survives process restarts.
Enforces real execution timeouts with process-level isolation and hard OS termination,
plus lease-based crash recovery, periodic heartbeats, and retry orchestration.
"""

import uuid
import time
import logging
import threading
import multiprocessing
import concurrent.futures
from typing import Any
from uuid import UUID
from datetime import datetime, timezone, timedelta

from sqlalchemy.orm import Session
from app.tasks.task_state import TaskState, DurableTaskRecord
from app.models.durable_task import DurableTask
from app.core.database import SessionLocal
from app.services.experiment_service import ExperimentService

logger = logging.getLogger(__name__)

DEFAULT_LEASE_DURATION_SECONDS = 30
DEFAULT_HEARTBEAT_INTERVAL_SECONDS = 10


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
        lease_expires_at=record.lease_expires_at,
        heartbeat_at=record.heartbeat_at,
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
        lease_expires_at=model.lease_expires_at,
        heartbeat_at=model.heartbeat_at,
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
            existing.lease_expires_at = record.lease_expires_at
            existing.heartbeat_at = record.heartbeat_at
            existing.failure_reason = record.failure_reason
            existing.result_summary = record.result_summary
            existing.retry_count = record.retry_count
            existing.max_retries = record.max_retries
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


def renew_task_lease(
    task_id: str,
    worker_id: str,
    extend_seconds: int = DEFAULT_LEASE_DURATION_SECONDS,
    db: Session | None = None,
) -> bool:
    """
    Extends the worker lease and updates the heartbeat timestamp for an active running task.
    Returns True if lease was successfully extended, False otherwise.
    """
    close_db = False
    if db is None:
        db = SessionLocal()
        close_db = True
    try:
        task = (
            db.query(DurableTask)
            .filter(
                DurableTask.id == task_id,
                DurableTask.worker_id == worker_id,
                DurableTask.state == TaskState.RUNNING.value,
            )
            .first()
        )
        if task:
            now = datetime.now(timezone.utc)
            task.heartbeat_at = now
            task.lease_expires_at = now + timedelta(seconds=extend_seconds)
            db.commit()
            return True
        return False
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to renew lease for task {task_id} by worker {worker_id}: {e}")
        return False
    finally:
        if close_db:
            db.close()


class HeartbeatRunner:
    """
    Background worker thread that sends periodic lease heartbeats for a running task.
    """
    def __init__(
        self,
        task_id: str,
        worker_id: str,
        interval_seconds: int = DEFAULT_HEARTBEAT_INTERVAL_SECONDS,
        lease_duration_seconds: int = DEFAULT_LEASE_DURATION_SECONDS,
    ):
        self.task_id = task_id
        self.worker_id = worker_id
        self.interval_seconds = interval_seconds
        self.lease_duration_seconds = lease_duration_seconds
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._run,
            name=f"heartbeat-{self.task_id}",
            daemon=True,
        )
        self._thread.start()

    def _run(self) -> None:
        while not self._stop_event.is_set():
            time.sleep(self.interval_seconds)
            if self._stop_event.is_set():
                break
            success = renew_task_lease(
                task_id=self.task_id,
                worker_id=self.worker_id,
                extend_seconds=self.lease_duration_seconds,
            )
            if not success:
                logger.debug(f"Heartbeat skipped or task {self.task_id} no longer running.")

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2)


def submit_experiment_task(
    project_id: UUID | str,
    experiment_id: UUID | str,
    algorithms: list[str] | None = None,
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
    commit_on_submit: bool = True,
) -> DurableTaskRecord:
    """
    Submits an experiment task into the durable database queue.
    The task is persisted with state QUEUED and claimed exclusively by the standalone worker daemon.
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
        if commit_on_submit:
            db.commit()
            db.refresh(model)
        else:
            db.flush()
        return _model_to_record(model)
    finally:
        if close_db:
            db.close()


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


def _child_experiment_worker(
    pipe_conn: Any,
    project_id: str | None,
    experiment_id: str | None,
    algorithms: list[str],
    folds: int,
    seed: int | None,
    threshold: float,
    selection_metric: str | None,
    selection_direction: str | None,
    deployment_threshold: dict[str, Any] | None,
) -> None:
    """Target execution function run inside an isolated OS child process."""
    db_exec = None
    try:
        db_exec = SessionLocal()
        service = ExperimentService(db_exec)
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
        if pipe_conn:
            pipe_conn.send({"status": "SUCCESS", "result": {"experiment_id": str(experiment_id), "status": "COMPLETED"}})
    except Exception as e:
        logger.exception(f"Child process execution failed: {e}")
        if pipe_conn:
            try:
                pipe_conn.send({"status": "ERROR", "error": str(e), "type": type(e).__name__})
            except Exception:
                pass
    finally:
        if db_exec:
            try:
                db_exec.close()
            except Exception:
                pass
        if pipe_conn:
            try:
                pipe_conn.close()
            except Exception:
                pass


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
    db: Session | None = None,
) -> None:
    """
    Executes task within an isolated child OS process, maintains periodic lease heartbeats,
    and enforces hard timeout termination.
    If the computation exceeds timeout_seconds, the child process is terminated (SIGTERM)
    and killed (SIGKILL) at the process boundary, marked TIMED_OUT in the DB, and partial writes are prevented.
    """
    record = get_task_status(task_id, db=db)
    if not record:
        record = DurableTaskRecord(task_id=task_id, experiment_id=str(experiment_id), timeout_seconds=timeout_seconds)

    if record.state == TaskState.CANCELLED:
        logger.info(f"Task {task_id} was cancelled before execution.")
        return

    record.mark_running(worker_id=worker_id, lease_duration_seconds=DEFAULT_LEASE_DURATION_SECONDS)
    save_task_record(record, db=db)

    # Start periodic background heartbeat runner to keep worker lease fresh
    heartbeat = HeartbeatRunner(
        task_id=task_id,
        worker_id=worker_id,
        interval_seconds=DEFAULT_HEARTBEAT_INTERVAL_SECONDS,
        lease_duration_seconds=DEFAULT_LEASE_DURATION_SECONDS,
    )
    heartbeat.start()

    # Process-isolated execution
    parent_conn, child_conn = multiprocessing.Pipe()
    process = multiprocessing.Process(
        target=_child_experiment_worker,
        args=(
            child_conn,
            str(project_id) if project_id else None,
            str(experiment_id) if experiment_id else None,
            algorithms,
            folds,
            seed,
            threshold,
            selection_metric,
            selection_direction,
            deployment_threshold,
        ),
        name=f"ml-child-{task_id}",
    )
    
    try:
        process.start()
        child_conn.close()

        process.join(timeout=timeout_seconds)

        if process.is_alive():
            logger.warning(
                f"Task {task_id} (PID {process.pid}) exceeded timeout of {timeout_seconds}s. "
                f"Hard terminating child process at process boundary."
            )
            process.terminate()
            process.join(timeout=2)
            if process.is_alive():
                logger.warning(f"Task {task_id} (PID {process.pid}) did not terminate on SIGTERM. Sending SIGKILL.")
                process.kill()
                process.join()

            record.mark_timed_out()
            record.failure_reason = (
                f"Execution terminated at process boundary: computation exceeded maximum timeout of {timeout_seconds}s."
            )
            save_task_record(record, db=db)
        else:
            # Process completed within timeout
            payload = None
            if parent_conn.poll():
                try:
                    payload = parent_conn.recv()
                except EOFError:
                    pass

            if payload and payload.get("status") == "SUCCESS":
                record.mark_succeeded(summary=payload.get("result", {"experiment_id": str(experiment_id), "status": "COMPLETED"}))
            elif payload and payload.get("status") == "ERROR":
                record.mark_failed(reason=payload.get("error", "Execution failed in child process"))
            elif process.exitcode != 0:
                record.mark_failed(reason=f"Worker process terminated unexpectedly with exit code {process.exitcode}")
            else:
                record.mark_succeeded(summary={"experiment_id": str(experiment_id), "status": "COMPLETED"})

            save_task_record(record, db=db)
    finally:
        heartbeat.stop()
        parent_conn.close()


def recover_stale_tasks(
    stale_threshold_seconds: int = DEFAULT_LEASE_DURATION_SECONDS,
    max_retries: int = 3,
    db: Session | None = None,
) -> dict[str, list[str]]:
    """
    Scans for orphaned/stale RUNNING tasks from crashed workers based on lease expiration.
    - If lease_expires_at < now (or elapsed >= stale_threshold_seconds) and retry_count < max_retries:
        Requeues the task (RUNNING -> QUEUED) for automatic recovery.
    - If retry_count >= max_retries:
        Marks the task FAILED (orphan cleanup).
    Returns a dict with 'requeued' and 'orphaned_failed' task ID lists.
    """
    close_db = False
    if db is None:
        db = SessionLocal()
        close_db = True
    result: dict[str, list[str]] = {"requeued": [], "orphaned_failed": []}
    try:
        running_tasks = db.query(DurableTask).filter(DurableTask.state == TaskState.RUNNING.value).all()
        now = datetime.now(timezone.utc)
        for task in running_tasks:
            is_stale = False
            if task.lease_expires_at:
                lease_exp = task.lease_expires_at
                if lease_exp.tzinfo is None:
                    lease_exp = lease_exp.replace(tzinfo=timezone.utc)
                if now > lease_exp:
                    is_stale = True
            elif task.started_at:
                started = task.started_at
                if started.tzinfo is None:
                    started = started.replace(tzinfo=timezone.utc)
                elapsed = (now - started).total_seconds()
                if elapsed >= stale_threshold_seconds:
                    is_stale = True

            if is_stale:
                current_retries = task.retry_count or 0
                task_max = task.max_retries or max_retries
                if current_retries < task_max:
                    task.retry_count = current_retries + 1
                    task.state = TaskState.QUEUED.value
                    task.started_at = None
                    task.worker_id = None
                    task.lease_expires_at = None
                    task.heartbeat_at = None
                    task.failure_reason = f"Requeued after worker lease expiration (retry {task.retry_count}/{task_max})"
                    result["requeued"].append(task.id)
                else:
                    task.state = TaskState.FAILED.value
                    task.finished_at = now
                    task.lease_expires_at = None
                    task.failure_reason = f"Worker process abandoned task or lease expired. Exceeded max retries ({task_max}). Marked FAILED on orphan cleanup."
                    result["orphaned_failed"].append(task.id)
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"Error during stale task recovery: {e}")
    finally:
        if close_db:
            db.close()
    return result


# Backward compatibility alias
execute_durable_experiment_task = run_task_with_timeout_enforcement
DURABLE_TASK_REGISTRY = {}
