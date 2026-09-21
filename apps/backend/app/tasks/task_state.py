"""
Durable Task State Machine and Persistence Helpers for ML Studio (P0.1, P1.1).
Backs task records into PostgreSQL/SQLite via the DurableTask SQLAlchemy model.
"""

from enum import Enum
from typing import Any
from datetime import datetime, timezone, timedelta
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
    lease_expires_at: datetime | None = None
    heartbeat_at: datetime | None = None
    failure_reason: str | None = None
    result_summary: dict[str, Any] | None = None

    def mark_running(self, worker_id: str = "worker-default", lease_duration_seconds: int = 30) -> None:
        now = datetime.now(timezone.utc)
        self.state = TaskState.RUNNING
        self.started_at = now
        self.heartbeat_at = now
        self.lease_expires_at = now + timedelta(seconds=lease_duration_seconds)
        self.worker_id = worker_id

    def renew_lease(self, extend_seconds: int = 30) -> None:
        now = datetime.now(timezone.utc)
        self.heartbeat_at = now
        self.lease_expires_at = now + timedelta(seconds=extend_seconds)

    def mark_succeeded(self, summary: dict[str, Any] | None = None) -> None:
        now = datetime.now(timezone.utc)
        self.state = TaskState.SUCCEEDED
        self.finished_at = now
        self.lease_expires_at = None
        self.result_summary = summary

    def mark_failed(self, reason: str) -> None:
        now = datetime.now(timezone.utc)
        self.state = TaskState.FAILED
        self.finished_at = now
        self.lease_expires_at = None
        self.failure_reason = reason

    def mark_cancelled(self) -> None:
        now = datetime.now(timezone.utc)
        self.state = TaskState.CANCELLED
        self.finished_at = now
        self.lease_expires_at = None

    def mark_timed_out(self) -> None:
        now = datetime.now(timezone.utc)
        self.state = TaskState.TIMED_OUT
        self.finished_at = now
        self.lease_expires_at = None
        self.failure_reason = f"Execution exceeded maximum timeout of {self.timeout_seconds}s"
