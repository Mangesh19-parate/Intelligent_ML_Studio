"""
Scheduled Data Retention and Log Cleanup Routine (Tier 3 Compliance).
Enforces retention policies on inference prediction logs, temporary task records, and scratch files.
"""

import sys
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Add backend directory to path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from app.core.database import SessionLocal
from app.models.prediction_log import PredictionLog
from app.models.durable_task import DurableTask

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("DataRetention")

from sqlalchemy.orm import Session

def purge_expired_records(retention_days: int = 90, db: Session | None = None):
    """
    Purges prediction audit logs and finished durable tasks older than retention_days.
    """
    cutoff_date = datetime.now(timezone.utc) - timedelta(days=retention_days)
    logger.info(f"Purging audit records older than {cutoff_date.isoformat()} ({retention_days} days retention)...")

    should_close = False
    if db is None:
        db = SessionLocal()
        should_close = True

    try:
        # 1. Purge aged prediction logs
        deleted_logs = (
            db.query(PredictionLog)
            .filter(PredictionLog.requested_at < cutoff_date)
            .delete(synchronize_session=False)
        )

        # 2. Purge aged completed/failed durable task records
        deleted_tasks = (
            db.query(DurableTask)
            .filter(
                DurableTask.state.in_(["COMPLETED", "FAILED", "TERMINATED"]),
                DurableTask.finished_at < cutoff_date
            )
            .delete(synchronize_session=False)
        )

        db.commit()
        logger.info(f"Retention cleanup complete: {deleted_logs} prediction logs and {deleted_tasks} task records purged.")
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to execute data retention purge: {e}")
        raise
    finally:
        if should_close:
            db.close()

if __name__ == "__main__":
    days = int(sys.argv[1]) if len(sys.argv) > 1 else 90
    purge_expired_records(retention_days=days)
