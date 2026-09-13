"""
Standalone ML Studio Task Worker Process (P0.1).
Polls for queued durable tasks from database / redis and executes them with crash recovery and isolation.
"""

import time
import logging
import signal
import sys
from datetime import datetime, timezone
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


def main():
    logger.info("ML Studio Durable Task Worker started.")
    worker_id = f"worker-daemon"

    # Recover any stale tasks from previous crashes
    recovered = recover_stale_tasks()
    if recovered:
        logger.info(f"Recovered {len(recovered)} orphaned tasks on startup: {recovered}")

    while RUNNING:
        db = SessionLocal()
        try:
            # Query for next queued task
            task = (
                db.query(DurableTask)
                .filter(DurableTask.state == TaskState.QUEUED.value)
                .order_by(DurableTask.queued_at.asc())
                .first()
            )
            if task:
                task_id = task.id
                exp_id = task.experiment_id
                timeout_s = task.timeout_seconds
                logger.info(f"Claiming task {task_id} for experiment {exp_id}...")
                task.state = TaskState.RUNNING.value
                task.worker_id = worker_id
                task.started_at = datetime.now(timezone.utc)
                db.commit()
                db.close()

                # Execute with isolation & timeout
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
            logger.error(f"Worker iteration exception: {e}")
            try:
                db.close()
            except Exception:
                pass
            time.sleep(2)

    logger.info("ML Studio Durable Task Worker stopped.")


if __name__ == "__main__":
    main()
