"""
Metrics Engine for Task Queue and Request Monitoring (P1.5).
Tracks task queue depth and task outcomes (SUCCEEDED, FAILED, TIMED_OUT).
"""

from typing import Any
from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.models.durable_task import DurableTask
from app.tasks.task_state import TaskState


def get_system_metrics(db: Session | None = None) -> dict[str, Any]:
    """
    Computes real-time system metrics including task queue depth and task outcome counts.
    """
    close_db = False
    if db is None:
        db = SessionLocal()
        close_db = True
    try:
        # Task queue depth and counts
        queued_count = db.query(DurableTask).filter(DurableTask.state == TaskState.QUEUED.value).count()
        running_count = db.query(DurableTask).filter(DurableTask.state == TaskState.RUNNING.value).count()
        succeeded_count = db.query(DurableTask).filter(DurableTask.state == TaskState.SUCCEEDED.value).count()
        failed_count = db.query(DurableTask).filter(DurableTask.state == TaskState.FAILED.value).count()
        timed_out_count = db.query(DurableTask).filter(DurableTask.state == TaskState.TIMED_OUT.value).count()

        return {
            "task_queue_depth": queued_count,
            "tasks_running": running_count,
            "tasks_succeeded": succeeded_count,
            "tasks_failed": failed_count,
            "tasks_timed_out": timed_out_count,
        }
    finally:
        if close_db:
            db.close()

