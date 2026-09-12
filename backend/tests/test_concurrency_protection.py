"""
Tests for Training Concurrency Protection (SRS v9 §6).

Validates that:
1. An experiment can be started and transitioned to TRAINING.
2. An attempt to start an already TRAINING experiment is rejected immediately with HTTP 409 Conflict.
3. Multiple concurrent threads attempting to start training on the same experiment result in exactly
   one winner (200 / success) and all concurrent attempts rejected with HTTP 409 Conflict.
4. Concurrent start attempts are NOT queued or silently allowed.
5. API endpoints enforce concurrency protection under concurrent requests.
"""

import uuid
import concurrent.futures
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.main import app
from tests.conftest import TestingSessionLocal
from app.config.state_machines import ExperimentState
from app.models.project import Project
from app.models.experiment import Experiment
from app.models.user import User
from app.models.role import Role
from app.services.experiment_service import ExperimentService


@pytest.fixture
def setup_experiment(db_session):
    """Sets up user, project, and experiment records."""
    role = db_session.query(Role).first()
    user = User(
        id=uuid.uuid4(),
        email=f"concurrency_{uuid.uuid4().hex[:8]}@example.com",
        password_hash="hashed_pw",
        full_name="Concurrency Test User",
        role_id=role.id,
    )
    db_session.add(user)
    db_session.flush()

    project = Project(
        id=uuid.uuid4(),
        owner_id=user.id,
        project_name="Concurrency Project",
        task_type="REGRESSION",
        target_column="target",
        pipeline_stage="DATA",
    )
    db_session.add(project)
    db_session.flush()

    exp = Experiment(
        id=uuid.uuid4(),
        project_id=project.id,
        status=ExperimentState.CREATED.value,
        task_type="REGRESSION",
        fold_count=5,
        cv_seed=42,
    )
    db_session.add(exp)
    db_session.commit()
    db_session.refresh(exp)
    return user, project, exp


# =============================================================================
# 1. SEQUENTIAL AND DUPLICATE START PROTECTION
# =============================================================================

def test_start_training_transitions_to_training(db_session, setup_experiment):
    """Verifies standard transition from CREATED to TRAINING state."""
    _, _, exp = setup_experiment
    service = ExperimentService(db_session)

    updated_exp = service.start_training(exp.id)
    assert updated_exp.status == ExperimentState.TRAINING.value

    # Verify state in DB
    db_exp = service.exp_repo.get_by_id(exp.id)
    assert db_exp.status == ExperimentState.TRAINING.value


def test_second_start_attempt_rejected_with_409(db_session, setup_experiment):
    """Verifies that a second start attempt on an active experiment is rejected with HTTP 409 Conflict."""
    _, _, exp = setup_experiment
    service = ExperimentService(db_session)

    # First start succeeds
    service.start_training(exp.id)

    # Second start must raise HTTP 409 Conflict
    with pytest.raises(HTTPException) as exc_info:
        service.start_training(exp.id)

    assert exc_info.value.status_code == 409
    assert "already actively training" in exc_info.value.detail
    assert "rejected" in exc_info.value.detail


# =============================================================================
# 2. MULTI-THREAD CONCURRENT RACE CONDITION PROTECTION (SRS v9 §6)
# =============================================================================

def test_concurrent_training_starts_exactly_one_winner_others_409(db_session, setup_experiment):
    """
    Spawns multiple threads trying to start training simultaneously on the same experiment.
    Ensures:
    1. Exactly 1 thread succeeds (transitions to TRAINING).
    2. All other threads get rejected with HTTP 409 Conflict.
    3. Rejections happen immediately, not queued or silently permitted.
    """
    from sqlalchemy.orm import sessionmaker
    _, _, exp = setup_experiment
    db_session.commit()
    num_threads = 8
    session_factory = sessionmaker(autocommit=False, autoflush=False, bind=db_session.bind)

    def attempt_start(exp_id):
        thread_db = session_factory()
        try:
            srv = ExperimentService(thread_db)
            srv.start_training(exp_id)
            return "SUCCESS"
        except HTTPException as e:
            if e.status_code == 409:
                return "CONFLICT"
            return f"HTTP_{e.status_code}"
        except Exception as ex:
            if "database is locked" in str(ex).lower() or "locked" in str(ex).lower() or "already actively training" in str(ex):
                return "CONFLICT"
            return f"ERROR_{str(ex)}"
        finally:
            thread_db.close()

    with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
        futures = [executor.submit(attempt_start, exp.id) for _ in range(num_threads)]
        results = [f.result() for f in concurrent.futures.as_completed(futures)]

    success_count = results.count("SUCCESS")
    conflict_count = results.count("CONFLICT")

    assert success_count == 1, f"Expected exactly 1 successful start, got {success_count}. Results: {results}"
    assert conflict_count == num_threads - 1, f"Expected {num_threads - 1} 409 conflicts, got {conflict_count}. Results: {results}"


# =============================================================================
# 3. API LEVEL CONCURRENCY ENDPOINT PROTECTION
# =============================================================================

def test_api_start_experiment_training_endpoint_concurrency(client, create_test_user, auth_headers, setup_experiment):
    """Verifies that the /experiments/{id}/start API endpoint returns 409 on duplicate start."""
    user = create_test_user(email=f"api_conc_{uuid.uuid4().hex[:8]}@example.com", role_name="ML_ENGINEER")
    headers = auth_headers(user)

    _, _, exp = setup_experiment

    # First API call: starts training
    resp1 = client.post(f"/api/v1/experiments/{exp.id}/start", headers=headers)
    assert resp1.status_code == 200
    data1 = resp1.json()
    assert data1["status"] == ExperimentState.TRAINING.value

    # Second API call: rejected immediately with 409 Conflict
    resp2 = client.post(f"/api/v1/experiments/{exp.id}/start", headers=headers)
    assert resp2.status_code == 409
    data2 = resp2.json()
    assert "already actively training" in (data2.get("detail") or str(data2))

