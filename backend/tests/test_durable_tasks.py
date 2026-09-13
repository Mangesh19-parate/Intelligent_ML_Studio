"""
Tests for Durable Asynchronous Task Orchestration and Lifecycle (P0.1, P0.2, P0.3).
Verifies DB persistence, idempotency, active timeout execution termination, and crash recovery.
"""

import time
import uuid
import pytest
from datetime import datetime, timezone, timedelta
from app.tasks.task_state import TaskState, DurableTaskRecord
from app.tasks.experiment_tasks import (
    submit_experiment_task,
    get_task_status,
    save_task_record,
    run_task_with_timeout_enforcement,
    recover_stale_tasks,
)
from app.models.durable_task import DurableTask
from app.core.database import SessionLocal


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


def test_idempotent_task_submission_and_db_persistence(db_session, create_test_user):
    """Verifies duplicate submissions with identical idempotency_key return the same task and persist in DB."""
    from app.models.project import Project
    from app.models.experiment import Experiment

    test_user = create_test_user("user_durable@mlstudio.io")

    # Create dummy project & experiment in DB
    proj = Project(
        project_name="Durable Project",
        task_type="REGRESSION",
        owner_id=test_user.id
    )
    db_session.add(proj)
    db_session.commit()

    exp = Experiment(
        project_id=proj.id,
        task_type="REGRESSION",
        status="CREATED"
    )
    db_session.add(exp)
    db_session.commit()

    idempotency_key = f"key-{uuid.uuid4()}"

    record1 = submit_experiment_task(
        project_id=proj.id,
        experiment_id=exp.id,
        algorithms=["LinearRegression"],
        idempotency_key=idempotency_key,
        run_async=False,
        db=db_session,
    )

    record2 = submit_experiment_task(
        project_id=proj.id,
        experiment_id=exp.id,
        algorithms=["LinearRegression"],
        idempotency_key=idempotency_key,
        run_async=False,
        db=db_session,
    )

    assert record1.task_id == record2.task_id
    status = get_task_status(record1.task_id, db=db_session)
    assert status is not None
    assert status.idempotency_key == idempotency_key

    # Check persistence directly via raw session query
    db_task = db_session.query(DurableTask).filter(DurableTask.id == record1.task_id).first()
    assert db_task is not None
    assert db_task.experiment_id == exp.id


def test_active_timeout_execution_enforcement(db_session, create_test_user):
    """
    P0.3 INVARIANT: Tests that an execution exceeding timeout_seconds is terminated,
    the task is marked TIMED_OUT in the database, and no subsequent writes occur.
    """
    from app.models.project import Project
    from app.models.experiment import Experiment
    from unittest.mock import patch

    test_user = create_test_user("user_timeout@mlstudio.io")

    proj = Project(
        project_name="Timeout Test Project",
        task_type="REGRESSION",
        owner_id=test_user.id
    )
    db_session.add(proj)
    db_session.commit()

    exp = Experiment(
        project_id=proj.id,
        task_type="REGRESSION",
        status="CREATED"
    )
    db_session.add(exp)
    db_session.commit()

    task_id = f"task-timeout-{uuid.uuid4()}"
    task_model = DurableTask(
        id=task_id,
        experiment_id=exp.id,
        state=TaskState.QUEUED.value,
        timeout_seconds=1,  # 1 second timeout
    )
    db_session.add(task_model)
    db_session.commit()

    # Simulate a long running training computation taking 3 seconds
    def slow_experiment(*args, **kwargs):
        time.sleep(3)
        return {"status": "ZOMBIE_WRITE"}

    with patch("app.services.experiment_service.ExperimentService.run_experiment", side_effect=slow_experiment):
        run_task_with_timeout_enforcement(
            task_id=task_id,
            project_id=proj.id,
            experiment_id=exp.id,
            algorithms=["LinearRegression"],
            timeout_seconds=1,
            worker_id="test-worker",
        )

    # Check that task status in DB is TIMED_OUT and failure_reason is recorded
    status = get_task_status(task_id)
    assert status is not None
    assert status.state == TaskState.TIMED_OUT
    assert "exceeded maximum timeout" in status.failure_reason
    assert status.result_summary is None  # Proves zero partial/zombie writes committed


def test_worker_crash_recovery_of_orphaned_tasks(db_session, create_test_user):
    """
    P0.1 INVARIANT: Tests that orphaned RUNNING tasks from a crashed worker are detected
    by recover_stale_tasks and transitioned to FAILED rather than lost.
    """
    from app.models.project import Project
    from app.models.experiment import Experiment

    test_user = create_test_user("user_crash@mlstudio.io")

    proj = Project(
        project_name="Crash Recovery Project",
        task_type="REGRESSION",
        owner_id=test_user.id
    )
    db_session.add(proj)
    db_session.commit()

    exp = Experiment(
        project_id=proj.id,
        task_type="REGRESSION",
        status="TRAINING"
    )
    db_session.add(exp)
    db_session.commit()

    # Simulate an orphaned task started 10 minutes ago
    orphaned_id = f"task-orphaned-{uuid.uuid4()}"
    past_time = datetime.now(timezone.utc) - timedelta(minutes=10)
    task_model = DurableTask(
        id=orphaned_id,
        experiment_id=exp.id,
        state=TaskState.RUNNING.value,
        worker_id="crashed-worker-node",
        timeout_seconds=60,
        started_at=past_time,
    )
    db_session.add(task_model)
    db_session.commit()

    recovered = recover_stale_tasks(stale_threshold_seconds=60, db=db_session)
    assert orphaned_id in recovered

    status = get_task_status(orphaned_id, db=db_session)
    assert status is not None
    assert status.state == TaskState.FAILED
    assert "crash recovery" in status.failure_reason.lower()
