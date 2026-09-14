"""
Standalone ML Studio Task Worker Process (P0.1, P0.2, P0.3).
Polls for queued durable tasks from database with atomic locking (FOR UPDATE SKIP LOCKED),
executes them under OS-level process isolation with hard timeout termination,
and performs lease-based crash recovery and retry orchestration.
"""

import time
import logging
import signal
import sys
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.models.durable_task import DurableTask
from app.tasks.task_state import TaskState
from app.tasks.experiment_tasks import (
    run_task_with_timeout_enforcement,
    recover_stale_tasks,
    _model_to_record
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [worker] %(message)s"
)
logger = logging.getLogger("task_worker")

RUNNING = True


def handle_shutdown(signum, frame):
    global RUNNING
    logger.info("Received termination signal. Shutting down worker gracefully...")
    RUNNING = False


signal.signal(signal.SIGINT, handle_shutdown)
signal.signal(signal.SIGTERM, handle_shutdown)


def claim_next_queued_task(db: Session, worker_id: str) -> DurableTask | None:
    """
    Atomically claims the next queued durable task.
    Uses PostgreSQL 'FOR UPDATE SKIP LOCKED' to prevent race conditions across multiple worker processes.
    Gracefully falls back to standard select for SQLite test environments.
    """
    try:
        query = (
            db.query(DurableTask)
            .filter(DurableTask.state == TaskState.QUEUED.value)
            .order_by(DurableTask.queued_at.asc())
        )
        if db.bind and db.bind.dialect.name == "postgresql":
            query = query.with_for_update(skip_locked=True)
        
        task = query.first()
        if task:
            task.state = TaskState.RUNNING.value
            task.worker_id = worker_id
            task.started_at = datetime.now(timezone.utc)
            db.commit()
            db.refresh(task)
            return task
        return None
    except Exception as e:
        db.rollback()
        logger.error(f"Error during atomic task claim: {e}")
        return None


def main():
    logger.info("ML Studio Durable Task Worker started (Process Isolation & Atomic Claiming enabled).")
    worker_id = f"worker-daemon"

    # Recover any stale or orphaned tasks on startup
    recovery_report = recover_stale_tasks()
    if recovery_report["requeued"]:
        logger.info(f"Requeued {len(recovery_report['requeued'])} abandoned tasks for retry: {recovery_report['requeued']}")
    if recovery_report["orphaned_failed"]:
        logger.info(f"Marked {len(recovery_report['orphaned_failed'])} exhausted tasks as FAILED: {recovery_report['orphaned_failed']}")

    while RUNNING:
        db = SessionLocal()
        try:
            task = claim_next_queued_task(db, worker_id=worker_id)
            if task:
                task_id = task.id
                exp_id = task.experiment_id
                timeout_s = task.timeout_seconds
                logger.info(f"Claimed task {task_id} for experiment {exp_id} (timeout: {timeout_s}s)...")
                db.close()

                # Execute with process isolation & hard timeout kill
                run_task_with_timeout_enforcement(
                    task_id=task_id,
                    project_id="",  # service retrieves from experiment
                    experiment_id=exp_id,
                    algorithms=[],
                    timeout_seconds=timeout_s,
                    worker_id=worker_id,
                )
            else:
                db.close()
                time.sleep(2)
        except Exception as e:
            logger.error(f"Worker loop exception: {e}")
            try:
                db.close()
            except Exception:
                pass
            time.sleep(2)

    logger.info("ML Studio Durable Task Worker stopped.")


if __name__ == "__main__":
    main()
