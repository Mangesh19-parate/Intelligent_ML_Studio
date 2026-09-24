"""
Standalone ML Studio Task Worker Process (P0.1, P0.2, P0.3, P1.1).
Polls for queued durable tasks from database with atomic locking (FOR UPDATE SKIP LOCKED),
executes them under OS-level process isolation with hard timeout termination,
and performs lease-based crash recovery, periodic heartbeats, and retry orchestration.
"""

import time
import logging
import signal
import sys
import uuid
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session
from app.core.database import SessionLocal
import app.models
from app.models.durable_task import DurableTask
from app.tasks.task_state import TaskState
from app.tasks.experiment_tasks import (
    run_task_with_timeout_enforcement,
    recover_stale_tasks,
    _model_to_record,
    DEFAULT_LEASE_DURATION_SECONDS,
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


def claim_next_queued_task(
    db: Session,
    worker_id: str,
    lease_duration_seconds: int = DEFAULT_LEASE_DURATION_SECONDS,
) -> DurableTask | None:
    """
    Atomically claims the next queued durable task.
    Uses PostgreSQL 'FOR UPDATE SKIP LOCKED' to prevent race conditions across multiple worker processes.
    Sets worker_id, started_at, heartbeat_at, and lease_expires_at.
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
            now = datetime.now(timezone.utc)
            task.state = TaskState.RUNNING.value
            task.worker_id = worker_id
            task.started_at = now
            task.heartbeat_at = now
            task.lease_expires_at = now + timedelta(seconds=lease_duration_seconds)

            # Atomically transition parent experiment from CONFIGURED/CREATED to TRAINING
            exp = db.query(Experiment).filter(Experiment.id == task.experiment_id).first()
            if exp and exp.status in ["CONFIGURED", "CREATED", "QUEUED"]:
                exp.status = "TRAINING"
                exp.started_at = now

            db.commit()
            db.refresh(task)
            return task
        return None
    except Exception as e:
        db.rollback()
        logger.error(f"Error during atomic task claim: {e}")
        return None


from app.models.experiment import Experiment


def main():
    worker_instance_id = f"worker-{uuid.uuid4().hex[:8]}"
    logger.info(f"ML Studio Durable Task Worker [{worker_instance_id}] started (Process Isolation & Lease Protocol enabled).")

    # Recover any stale or orphaned tasks on startup
    recovery_report = recover_stale_tasks()
    if recovery_report["requeued"]:
        logger.info(f"Requeued {len(recovery_report['requeued'])} abandoned tasks for retry: {recovery_report['requeued']}")
    if recovery_report["orphaned_failed"]:
        logger.info(f"Marked {len(recovery_report['orphaned_failed'])} exhausted tasks as FAILED: {recovery_report['orphaned_failed']}")

    while RUNNING:
        db = SessionLocal()
        try:
            task = claim_next_queued_task(db, worker_id=worker_instance_id)
            if task:
                task_id = task.id
                exp_id = task.experiment_id
                timeout_s = task.timeout_seconds
                logger.info(f"Claimed task {task_id} for experiment {exp_id} (timeout: {timeout_s}s)...")

                exp = db.query(Experiment).filter(Experiment.id == exp_id).first()
                project_id = str(exp.project_id) if exp else ""
                cfg = (exp.experiment_config or {}) if exp else {}
                algorithms = cfg.get("algorithms") or []
                folds = exp.fold_count or cfg.get("cv", {}).get("folds", 5) if exp else 5
                seed = exp.cv_seed if (exp and exp.cv_seed is not None) else cfg.get("cv", {}).get("seed", 42)
                selection_metric = exp.selection_metric if exp else None
                selection_direction = exp.selection_direction if exp else None
                deployment_threshold = cfg.get("deployment_threshold") if cfg else None
                db.close()

                # Execute with process isolation, heartbeats & hard timeout kill
                run_task_with_timeout_enforcement(
                    task_id=task_id,
                    project_id=project_id,
                    experiment_id=exp_id,
                    algorithms=algorithms,
                    folds=folds,
                    seed=seed,
                    selection_metric=selection_metric,
                    selection_direction=selection_direction,
                    deployment_threshold=deployment_threshold,
                    timeout_seconds=timeout_s,
                    worker_id=worker_instance_id,
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

    logger.info(f"ML Studio Durable Task Worker [{worker_instance_id}] stopped.")


if __name__ == "__main__":
    main()
