"""
Metrics Engine for Task Queue and Request Monitoring (P1.5).
Tracks task queue depth, task outcomes (SUCCEEDED, FAILED, TIMED_OUT), and latency percentiles.
"""

import time
from typing import Any
from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.models.durable_task import DurableTask
from app.models.experiment import Experiment

_LATENCY_SAMPLES: list[float] = []
_MAX_SAMPLES = 1000


def record_request_latency(duration_ms: float) -> None:
    global _LATENCY_SAMPLES
    _LATENCY_SAMPLES.append(duration_ms)
    if len(_LATENCY_SAMPLES) > _MAX_SAMPLES:
        _LATENCY_SAMPLES = _LATENCY_SAMPLES[-_MAX_SAMPLES:]


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
        queued_count = db.query(DurableTask).filter(DurableTask.state == "QUEUED").count()
        running_count = db.query(DurableTask).filter(DurableTask.state == "RUNNING").count()
        succeeded_count = db.query(DurableTask).filter(DurableTask.state == "SUCCEEDED").count()
        failed_count = db.query(DurableTask).filter(DurableTask.state == "FAILED").count()
        timed_out_count = db.query(DurableTask).filter(DurableTask.state == "TIMED_OUT").count()

        # Latency statistics
        if _LATENCY_SAMPLES:
            sorted_latencies = sorted(_LATENCY_SAMPLES)
            n = len(sorted_latencies)
            p50 = sorted_latencies[int(n * 0.50)]
            p95 = sorted_latencies[min(int(n * 0.95), n - 1)]
            p99 = sorted_latencies[min(int(n * 0.99), n - 1)]
            avg_latency = sum(sorted_latencies) / n
        else:
            p50, p95, p99, avg_latency = 0.0, 0.0, 0.0, 0.0

        return {
            "task_queue_depth": queued_count,
            "tasks_running": running_count,
            "tasks_succeeded": succeeded_count,
            "tasks_failed": failed_count,
            "tasks_timed_out": timed_out_count,
            "request_latency_p50_ms": round(p50, 2),
            "request_latency_p95_ms": round(p95, 2),
            "request_latency_p99_ms": round(p99, 2),
            "request_latency_avg_ms": round(avg_latency, 2),
            "total_requests_sampled": len(_LATENCY_SAMPLES),
        }
    finally:
        if close_db:
            db.close()
