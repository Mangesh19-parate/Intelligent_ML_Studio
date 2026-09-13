"""
Durable Task State Machine and Persistence Helpers for ML Studio (P0.1).
Backs task records into PostgreSQL/SQLite via the DurableTask SQLAlchemy model.
"""

from enum import Enum
from typing import Any
from datetime import datetime, timezone
from dataclasses import dataclass, field
import uuid


class TaskState(str, Enum):
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    TIMED_OUT = "TIMED_OUT"
    CANCELLED = "CANCELLED"


@dataclass
class DurableTaskRecord:
    task_id: str
    experiment_id: str
    state: TaskState = TaskState.QUEUED
    idempotency_key: str | None = None
    retry_count: int = 0
    max_retries: int = 3
    timeout_seconds: int = 600
    worker_id: str | None = None
    queued_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    started_at: datetime | None = None
    finished_at: datetime | None = None
    failure_reason: str | None = None
    result_summary: dict[str, Any] | None = None

    def mark_running(self, worker_id: str = "worker-default") -> None:
        self.state = TaskState.RUNNING
        self.started_at = datetime.now(timezone.utc)
        self.worker_id = worker_id

    def mark_succeeded(self, summary: dict[str, Any] | None = None) -> None:
        self.state = TaskState.SUCCEEDED
        self.finished_at = datetime.now(timezone.utc)
        self.result_summary = summary

    def mark_failed(self, reason: str) -> None:
        self.state = TaskState.FAILED
        self.finished_at = datetime.now(timezone.utc)
        self.failure_reason = reason

    def mark_cancelled(self) -> None:
        self.state = TaskState.CANCELLED
        self.finished_at = datetime.now(timezone.utc)

    def mark_timed_out(self) -> None:
        self.state = TaskState.TIMED_OUT
        self.finished_at = datetime.now(timezone.utc)
        self.failure_reason = f"Execution exceeded maximum timeout of {self.timeout_seconds}s"
