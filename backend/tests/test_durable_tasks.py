"""
Tests for Durable Asynchronous Task Orchestration and Lifecycle.
"""

import uuid
import pytest
from app.tasks.task_state import TaskState, DurableTaskRecord
from app.tasks.experiment_tasks import (
    submit_experiment_task,
    get_task_status,
    execute_durable_experiment_task,
    DURABLE_TASK_REGISTRY,
    IDEMPOTENCY_INDEX,
)


def test_durable_task_lifecycle():
    """Verifies state transitions from QUEUED -> RUNNING -> SUCCEEDED."""
    task_id = f"test-task-{uuid.uuid4()}"
    record = DurableTaskRecord(task_id=task_id, experiment_id=str(uuid.uuid4()))
    assert record.state == TaskState.QUEUED
    assert record.started_at is None

    record.mark_running(worker_id="worker-node-1")
    assert record.state == TaskState.RUNNING
    assert record.worker_id == "worker-node-1"
    assert record.started_at is not None

    record.mark_succeeded(summary={"accuracy": 0.95})
    assert record.state == TaskState.SUCCEEDED
    assert record.finished_at is not None
    assert record.result_summary == {"accuracy": 0.95}


def test_durable_task_failure_and_timeout():
    """Verifies failure reason capture and timeout handling."""
    task_id = f"test-task-{uuid.uuid4()}"
    record = DurableTaskRecord(task_id=task_id, experiment_id=str(uuid.uuid4()))
    record.mark_running()
    record.mark_failed("OutOfMemoryError during feature selection")
    assert record.state == TaskState.FAILED
    assert record.failure_reason == "OutOfMemoryError during feature selection"

    # Timeout
    task_timeout = DurableTaskRecord(task_id=f"timeout-{uuid.uuid4()}", experiment_id=str(uuid.uuid4()), timeout_seconds=300)
    task_timeout.mark_running()
    task_timeout.mark_timed_out()
    assert task_timeout.state == TaskState.TIMED_OUT
    assert "exceeded maximum timeout" in task_timeout.failure_reason


def test_idempotent_task_submission():
    """Verifies duplicate submissions with identical idempotency_key return the same task."""
    idempotency_key = f"key-{uuid.uuid4()}"
    exp_id = uuid.uuid4()
    proj_id = uuid.uuid4()

    record1 = submit_experiment_task(
        project_id=proj_id,
        experiment_id=exp_id,
        algorithms=["LinearRegression"],
        idempotency_key=idempotency_key,
    )

    record2 = submit_experiment_task(
        project_id=proj_id,
        experiment_id=exp_id,
        algorithms=["LinearRegression"],
        idempotency_key=idempotency_key,
    )

    assert record1.task_id == record2.task_id
    assert get_task_status(record1.task_id) is not None
