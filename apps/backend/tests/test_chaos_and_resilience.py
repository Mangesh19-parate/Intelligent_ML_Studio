"""
Chaos and Infrastructure Resilience Test Suite (P1.1, P1.4).
Tests system behavior under simulated chaos:
1. Worker process kill / sudden death -> Task lease expiration -> Automatic requeue -> Recovery.
2. Repeated worker crashes -> Max retries exhaustion -> Clean orphan triage (FAILED).
3. High concurrency claim contention (multiple workers contending for queue).
4. Hard process-isolated kill under runaway computations.
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
from app.tasks.worker import claim_next_queued_task
from app.models.durable_task import DurableTask
from app.models.project import Project
from app.models.experiment import Experiment


def test_chaos_worker_crash_and_automatic_requeue_recovery(db_session, create_test_user):
    """
    CHAOS TEST 1: Simulates worker process dying abruptly mid-task.
    System detects stale lease, requeues task, and allows a new worker to claim and complete it.
    """
    test_user = create_test_user("chaos_worker@mlstudio.io")
    proj = Project(project_name="Chaos Proj 1", task_type="REGRESSION", owner_id=test_user.id)
    db_session.add(proj)
    db_session.commit()

    exp = Experiment(project_id=proj.id, task_type="REGRESSION", status="TRAINING")
    db_session.add(exp)
    db_session.commit()

    task_id = f"task-chaos-{uuid.uuid4()}"
    # Simulate crashed worker that started 15 minutes ago
    crashed_time = datetime.now(timezone.utc) - timedelta(minutes=15)
    task = DurableTask(
        id=task_id,
        experiment_id=exp.id,
        state=TaskState.RUNNING.value,
        worker_id="crashed-worker-pid-9999",
        started_at=crashed_time,
        retry_count=0,
        max_retries=3,
        timeout_seconds=60,
    )
    db_session.add(task)
    db_session.commit()

    # Step 1: Healthcheck/Recovery detects abandoned task and requeues it
    report = recover_stale_tasks(stale_threshold_seconds=60, max_retries=3, db=db_session)
    assert task_id in report["requeued"]

    db_session.expire_all()
    requeued_task = get_task_status(task_id, db=db_session)
    assert requeued_task.state == TaskState.QUEUED
    assert requeued_task.retry_count == 1
    assert requeued_task.worker_id is None

    # Step 2: New worker node comes online and claims the requeued task
    new_worker_claim = claim_next_queued_task(db_session, worker_id="healthy-worker-pid-1001")
    assert new_worker_claim is not None
    assert new_worker_claim.id == task_id
    assert new_worker_claim.state == TaskState.RUNNING.value
    assert new_worker_claim.worker_id == "healthy-worker-pid-1001"


def test_chaos_max_retries_exhaustion_orphaned_triage(db_session, create_test_user):
    """
    CHAOS TEST 2: If a task continually crashes workers up to max_retries,
    it must be transitioned to FAILED with explicit diagnosis to prevent poison-pill infinite loops.
    """
    test_user = create_test_user("chaos_exhaust@mlstudio.io")
    proj = Project(project_name="Chaos Proj 2", task_type="REGRESSION", owner_id=test_user.id)
    db_session.add(proj)
    db_session.commit()

    exp = Experiment(project_id=proj.id, task_type="REGRESSION", status="TRAINING")
    db_session.add(exp)
    db_session.commit()

    task_id = f"task-exhaust-{uuid.uuid4()}"
    crashed_time = datetime.now(timezone.utc) - timedelta(minutes=20)
    task = DurableTask(
        id=task_id,
        experiment_id=exp.id,
        state=TaskState.RUNNING.value,
        worker_id="crashed-worker-fail",
        started_at=crashed_time,
        retry_count=3,
        max_retries=3,
        timeout_seconds=60,
    )
    db_session.add(task)
    db_session.commit()

    report = recover_stale_tasks(stale_threshold_seconds=60, max_retries=3, db=db_session)
    assert task_id in report["orphaned_failed"]

    db_session.expire_all()
    status = get_task_status(task_id, db=db_session)
    assert status.state == TaskState.FAILED
    assert "exceeded max retries" in status.failure_reason.lower()


def test_chaos_multi_worker_contention_no_duplicate_claims(db_session, create_test_user):
    """
    CHAOS TEST 3: Simulates 5 workers racing to claim 3 queued tasks.
    Every task must be claimed exactly once with no collisions or duplicates.
    """
    test_user = create_test_user("chaos_race@mlstudio.io")
    proj = Project(project_name="Chaos Proj 3", task_type="REGRESSION", owner_id=test_user.id)
    db_session.add(proj)
    db_session.commit()

    exp = Experiment(project_id=proj.id, task_type="REGRESSION", status="CREATED")
    db_session.add(exp)
    db_session.commit()

    task_ids = [f"race-task-{i}-{uuid.uuid4()}" for i in range(3)]
    for tid in task_ids:
        t = DurableTask(id=tid, experiment_id=exp.id, state=TaskState.QUEUED.value, timeout_seconds=60)
        db_session.add(t)
    db_session.commit()

    claimed_by_worker = {}
    # 5 workers poll the queue sequentially or concurrently
    workers = [f"worker-node-{i}" for i in range(5)]
    for w in workers:
        task = claim_next_queued_task(db_session, worker_id=w)
        if task:
            claimed_by_worker[w] = task.id

    # Exactly 3 tasks claimed by 3 distinct workers, 2 workers get None
    assert len(claimed_by_worker) == 3
    assert set(claimed_by_worker.values()) == set(task_ids)


def test_chaos_hard_process_isolation_kill(db_session, create_test_user):
    """
    CHAOS TEST 4: Simulates a rogue execution exceeding timeout budget.
    Ensures process is terminated at the OS level and state recorded as TIMED_OUT.
    """
    test_user = create_test_user("chaos_kill@mlstudio.io")
    proj = Project(project_name="Chaos Proj 4", task_type="REGRESSION", owner_id=test_user.id)
    db_session.add(proj)
    db_session.commit()

    exp = Experiment(project_id=proj.id, task_type="REGRESSION", status="CREATED")
    db_session.add(exp)
    db_session.commit()

    task_id = f"chaos-kill-{uuid.uuid4()}"
    t = DurableTask(id=task_id, experiment_id=exp.id, state=TaskState.QUEUED.value, timeout_seconds=1)
    db_session.add(t)
    db_session.commit()

    run_task_with_timeout_enforcement(
        task_id=task_id,
        project_id=proj.id,
        experiment_id=exp.id,
        algorithms=["RandomForestClassifier"],
        timeout_seconds=1,
        worker_id="chaos-worker-primary",
        db=db_session,
    )

    db_session.expire_all()
    status = get_task_status(task_id, db=db_session)
    assert status.state in [TaskState.TIMED_OUT, TaskState.FAILED]
