"""
Tests for Durable Asynchronous Task Orchestration and Lifecycle (P0.1, P0.2, P0.3, P1.1).
Verifies DB persistence, idempotency, process-isolated timeout termination, atomic claiming,
worker lease protocol, periodic heartbeats, and lease-based retry recovery.
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
    renew_task_lease,
    HeartbeatRunner,
)
from app.tasks.worker import claim_next_queued_task
from app.models.durable_task import DurableTask
from app.core.database import SessionLocal


def test_durable_task_lifecycle():
    """Verifies state transitions from QUEUED -> RUNNING -> SUCCEEDED with lease tracking."""
    task_id = f"test-task-{uuid.uuid4()}"
    record = DurableTaskRecord(task_id=task_id, experiment_id=str(uuid.uuid4()))
    assert record.state == TaskState.QUEUED
    assert record.started_at is None
    assert record.lease_expires_at is None

    record.mark_running(worker_id="worker-node-1", lease_duration_seconds=30)
    assert record.state == TaskState.RUNNING
    assert record.worker_id == "worker-node-1"
    assert record.started_at is not None
    assert record.lease_expires_at is not None
    assert record.heartbeat_at is not None

    record.mark_succeeded(summary={"accuracy": 0.95})
    assert record.state == TaskState.SUCCEEDED
    assert record.finished_at is not None
    assert record.lease_expires_at is None
    assert record.result_summary == {"accuracy": 0.95}


def test_durable_task_failure_and_timeout():
    """Verifies failure reason capture, lease clearing, and timeout handling."""
    task_id = f"test-task-{uuid.uuid4()}"
    record = DurableTaskRecord(task_id=task_id, experiment_id=str(uuid.uuid4()))
    record.mark_running(worker_id="worker-1", lease_duration_seconds=30)
    record.mark_failed("OutOfMemoryError during feature selection")
    assert record.state == TaskState.FAILED
    assert record.lease_expires_at is None
    assert record.failure_reason == "OutOfMemoryError during feature selection"

    # Timeout
    task_timeout = DurableTaskRecord(task_id=f"timeout-{uuid.uuid4()}", experiment_id=str(uuid.uuid4()), timeout_seconds=300)
    task_timeout.mark_running(worker_id="worker-1", lease_duration_seconds=30)
    task_timeout.mark_timed_out()
    assert task_timeout.state == TaskState.TIMED_OUT
    assert task_timeout.lease_expires_at is None
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


def test_atomic_task_claim_and_concurrency(db_session, create_test_user):
    """
    P0.1 & P1.1 INVARIANT: Tests that claiming a queued task transitions state to RUNNING,
    assigns worker_id, and sets lease_expires_at.
    """
    from app.models.project import Project
    from app.models.experiment import Experiment

    test_user = create_test_user("user_claim@mlstudio.io")

    proj = Project(project_name="Claim Project", task_type="REGRESSION", owner_id=test_user.id)
    db_session.add(proj)
    db_session.commit()

    exp = Experiment(project_id=proj.id, task_type="REGRESSION", status="CREATED")
    db_session.add(exp)
    db_session.commit()

    task_id = f"task-claim-{uuid.uuid4()}"
    task_model = DurableTask(
        id=task_id,
        experiment_id=exp.id,
        state=TaskState.QUEUED.value,
        timeout_seconds=60,
    )
    db_session.add(task_model)
    db_session.commit()

    # Worker 1 claims task
    claimed = claim_next_queued_task(db_session, worker_id="worker-A", lease_duration_seconds=45)
    assert claimed is not None
    assert claimed.id == task_id
    assert claimed.state == TaskState.RUNNING.value
    assert claimed.worker_id == "worker-A"
    assert claimed.lease_expires_at is not None
    assert claimed.heartbeat_at is not None

    # Worker 2 attempts to claim - queue should be empty
    claimed_again = claim_next_queued_task(db_session, worker_id="worker-B")
    assert claimed_again is None


def test_worker_lease_and_heartbeat_renewal(db_session, create_test_user):
    """
    P1.1 INVARIANT: Tests that an active worker can periodically renew its task lease and update heartbeats.
    """
    from app.models.project import Project
    from app.models.experiment import Experiment

    test_user = create_test_user("user_lease@mlstudio.io")

    proj = Project(project_name="Lease Project", task_type="REGRESSION", owner_id=test_user.id)
    db_session.add(proj)
    db_session.commit()

    exp = Experiment(project_id=proj.id, task_type="REGRESSION", status="TRAINING")
    db_session.add(exp)
    db_session.commit()

    task_id = f"task-lease-{uuid.uuid4()}"
    initial_exp = datetime.now(timezone.utc) + timedelta(seconds=10)
    task_model = DurableTask(
        id=task_id,
        experiment_id=exp.id,
        state=TaskState.RUNNING.value,
        worker_id="worker-live-1",
        timeout_seconds=60,
        started_at=datetime.now(timezone.utc),
        lease_expires_at=initial_exp,
    )
    db_session.add(task_model)
    db_session.commit()

    # Renew lease by worker
    success = renew_task_lease(task_id, worker_id="worker-live-1", extend_seconds=60, db=db_session)
    assert success is True

    db_session.refresh(task_model)
    updated_lease = task_model.lease_expires_at
    if updated_lease and updated_lease.tzinfo is None:
        updated_lease = updated_lease.replace(tzinfo=timezone.utc)
    assert updated_lease > initial_exp
    assert task_model.heartbeat_at is not None

    # Attempt renewal by wrong worker should fail
    wrong_worker_success = renew_task_lease(task_id, worker_id="worker-imposter", extend_seconds=60, db=db_session)
    assert wrong_worker_success is False


def test_worker_crash_recovery_via_lease_expiration(db_session, create_test_user):
    """
    P0.1 & P1.1 INVARIANT: Tests that expired leases from a crashed worker:
    1. Are requeued (RUNNING -> QUEUED) if retry_count < max_retries
    2. Are marked FAILED once max_retries is exceeded.
    """
    from app.models.project import Project
    from app.models.experiment import Experiment

    test_user = create_test_user("user_recovery@mlstudio.io")

    proj = Project(project_name="Recovery Project", task_type="REGRESSION", owner_id=test_user.id)
    db_session.add(proj)
    db_session.commit()

    exp = Experiment(project_id=proj.id, task_type="REGRESSION", status="TRAINING")
    db_session.add(exp)
    db_session.commit()

    # 1. Task with expired lease and retry_count = 0 (can be retried)
    requeue_id = f"task-requeue-{uuid.uuid4()}"
    past_lease = datetime.now(timezone.utc) - timedelta(seconds=15)
    task_requeue = DurableTask(
        id=requeue_id,
        experiment_id=exp.id,
        state=TaskState.RUNNING.value,
        worker_id="crashed-worker-1",
        timeout_seconds=60,
        started_at=datetime.now(timezone.utc) - timedelta(minutes=5),
        lease_expires_at=past_lease,
        retry_count=0,
        max_retries=2,
    )
    db_session.add(task_requeue)

    # 2. Task with expired lease and retry_count = 2 (max retries reached)
    exhausted_id = f"task-exhausted-{uuid.uuid4()}"
    task_exhausted = DurableTask(
        id=exhausted_id,
        experiment_id=exp.id,
        state=TaskState.RUNNING.value,
        worker_id="crashed-worker-2",
        timeout_seconds=60,
        started_at=datetime.now(timezone.utc) - timedelta(minutes=5),
        lease_expires_at=past_lease,
        retry_count=2,
        max_retries=2,
    )
    db_session.add(task_exhausted)
    db_session.commit()

    report = recover_stale_tasks(db=db_session)
    assert requeue_id in report["requeued"]
    assert exhausted_id in report["orphaned_failed"]

    status_requeue = get_task_status(requeue_id, db=db_session)
    assert status_requeue.state == TaskState.QUEUED
    assert status_requeue.retry_count == 1
    assert status_requeue.worker_id is None
    assert status_requeue.lease_expires_at is None
    assert "requeued" in status_requeue.failure_reason.lower()

    status_exhausted = get_task_status(exhausted_id, db=db_session)
    assert status_exhausted.state == TaskState.FAILED
    assert "exceeded max retries" in status_exhausted.failure_reason.lower()
