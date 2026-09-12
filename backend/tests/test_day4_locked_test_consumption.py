"""
Unit & Integration Tests for Day 4 — Locked Test Consumption.

Per SRS v9 §5, SRS §2.5, and SRS §2.12:
1. One-time Locked Test evaluation:
   - Lifecycle: ExperimentState.EVALUATED -> ExperimentState.TEST_CONSUMED -> ExperimentState.REGISTERED.
   - Permanent flag: experiment.locked_test_consumed = True with locked_test_consumed_at timestamp.
2. Second standard finalization attempt is strictly rejected (HTTP 400).
3. Subsequent/diagnostic evaluations stored as model_metrics.split = 'TEST_REUSED_DIAGNOSTIC'.
4. TEST_REUSED_DIAGNOSTIC is excluded from leaderboard and deployment gate queries at the query level.
"""

import uuid
from uuid import uuid4
from datetime import datetime, timezone
import numpy as np
import pandas as pd
import pytest
from fastapi import HTTPException, status

from app.models.project import Project
from app.models.user import User
from app.models.role import Role
from app.models.dataset import Dataset
from app.models.dataset_column import DatasetColumn
from app.models.dataset_split import DatasetSplit
from app.models.transformation_config import TransformationConfig
from app.models.experiment import Experiment
from app.models.trained_model import TrainedModel
from app.models.model_metric import ModelMetric
from app.models.feature_selection_snapshot import FeatureSelectionSnapshot
from app.config.state_machines import ExperimentState, ModelState
from app.services.experiment_service import ExperimentService
from app.services.deployment_gate_service import DeploymentGateService
from app.repositories.experiment_repository import ExperimentRepository


def get_auth_token(client, email="day4_mle@studio.com"):
    """Helper to signup/login and obtain JWT bearer token."""
    reg_resp = client.post("/api/v1/auth/signup", json={
        "email": email,
        "password": "Password123!",
        "full_name": "Day4 MLE",
    })
    assert reg_resp.status_code in [200, 201]
    resp = client.post("/api/v1/auth/login", json={
        "email": email,
        "password": "Password123!",
    })
    assert resp.status_code == 200
    return resp.json()["access_token"]


@pytest.fixture
def day4_experiment_env(db_session, create_test_user, tmp_path):
    """Sets up a complete classification environment for testing Locked Test lifecycle."""
    user = create_test_user("d4_user@studio.ml", "ADMIN")

    project = Project(
        id=uuid4(),
        owner_id=user.id,
        project_name="Day 4 Locked Test Project",
        task_type="CLASSIFICATION",
        target_column="label",
        pipeline_stage="TRANSFORMED",
    )
    db_session.add(project)
    db_session.commit()

    np.random.seed(42)
    n_samples = 60
    f1 = np.random.normal(0, 1, n_samples)
    f2 = np.random.normal(0, 1, n_samples)
    labels = (f1 + f2 > 0).astype(int)

    df = pd.DataFrame({
        "feat1": f1,
        "feat2": f2,
        "label": labels,
        "row_uid": [f"d4_{i}" for i in range(n_samples)],
    })

    csv_path = tmp_path / "d4_data.csv"
    df.to_csv(csv_path, index=False)

    dataset = Dataset(
        id=uuid4(),
        project_id=project.id,
        file_path=str(csv_path),
        row_count=n_samples,
        column_count=3,
        content_hash="d4contenthash123456",
        version_number=1,
        stage="SPLIT",
    )
    db_session.add(dataset)
    db_session.commit()

    c1 = DatasetColumn(id=uuid4(), dataset_id=dataset.id, column_name="feat1", data_type="NUMERIC")
    c2 = DatasetColumn(id=uuid4(), dataset_id=dataset.id, column_name="feat2", data_type="NUMERIC")
    c3 = DatasetColumn(id=uuid4(), dataset_id=dataset.id, column_name="label", data_type="CATEGORICAL", is_target=True)
    db_session.add_all([c1, c2, c3])

    tc1 = TransformationConfig(
        id=uuid4(),
        project_id=project.id,
        column_name="feat1",
        missing_value_strategy="MEAN",
        scaling_strategy="STANDARD",
        outlier_strategy="NONE",
        is_active=True,
    )
    tc2 = TransformationConfig(
        id=uuid4(),
        project_id=project.id,
        column_name="feat2",
        missing_value_strategy="MEAN",
        scaling_strategy="STANDARD",
        outlier_strategy="NONE",
        is_active=True,
    )
    db_session.add_all([tc1, tc2])

    dev_split = DatasetSplit(
        id=uuid4(),
        dataset_id=dataset.id,
        split_type="DEVELOPMENT",
        split_seed=42,
        row_indices=[f"d4_{i}" for i in range(45)],
    )
    test_split = DatasetSplit(
        id=uuid4(),
        dataset_id=dataset.id,
        split_type="LOCKED_TEST",
        split_seed=42,
        row_indices=[f"d4_{i}" for i in range(45, n_samples)],
    )
    db_session.add(dev_split)
    db_session.add(test_split)
    db_session.commit()

    return project, dataset, user


# =============================================================================
# 1. State Lifecycle: EVALUATED -> TEST_CONSUMED -> REGISTERED
# =============================================================================

def test_locked_test_state_lifecycle(db_session, day4_experiment_env):
    """
    Verify one-time Locked Test evaluation lifecycle:
    1. Training with auto_finalize=False sets state to EVALUATED.
    2. Calling finalize_experiment evaluates Locked Test once, sets locked_test_consumed=True,
       and transitions to TEST_CONSUMED and REGISTERED.
    """
    project, dataset, user = day4_experiment_env
    service = ExperimentService(db_session)

    exp = service.exp_repo.create_experiment(
        project_id=project.id,
        task_type="CLASSIFICATION",
        status=ExperimentState.CREATED.value,
    )

    frozen_exp = service.freeze_experiment_config(
        exp.id,
        config_override={
            "algorithms": ["LogisticRegression"],
            "folds": 3,
            "seed": 42,
            "selection_metric": "macro_f1",
            "selection_direction": "MAXIMIZE",
        },
    )

    # 1. Run experiment without auto-finalization
    res = service.run_experiment(
        project_id=project.id,
        experiment_id=frozen_exp.id,
        auto_finalize=False,
    )

    db_session.refresh(exp)
    assert exp.status == ExperimentState.EVALUATED.value
    assert exp.locked_test_consumed is False
    assert exp.locked_test_consumed_at is None

    # 2. Finalize experiment -> consumes Locked Test
    fin_res = service.finalize_experiment(exp.id)

    db_session.refresh(exp)
    assert exp.status == ExperimentState.REGISTERED.value
    assert exp.locked_test_consumed is True
    assert exp.locked_test_consumed_at is not None

    # Verify winning model state and LOCKED_TEST metrics
    winning_model = db_session.query(TrainedModel).filter_by(id=exp.selected_model_id).first()
    assert winning_model is not None
    assert winning_model.status == ModelState.DEPLOYABLE.value

    locked_metrics = db_session.query(ModelMetric).filter_by(
        model_id=winning_model.id,
        split="LOCKED_TEST"
    ).all()
    assert len(locked_metrics) > 0


# =============================================================================
# 2. Second Standard Finalization Attempt is Strictly Rejected
# =============================================================================

def test_second_finalize_attempt_strictly_rejected(db_session, day4_experiment_env):
    """Verify calling finalize_experiment on an already-consumed experiment raises HTTP 400."""
    project, dataset, user = day4_experiment_env
    service = ExperimentService(db_session)

    exp = service.exp_repo.create_experiment(
        project_id=project.id,
        task_type="CLASSIFICATION",
        status=ExperimentState.CREATED.value,
    )

    frozen_exp = service.freeze_experiment_config(
        exp.id,
        config_override={
            "algorithms": ["LogisticRegression"],
            "folds": 3,
            "seed": 42,
            "selection_metric": "macro_f1",
            "selection_direction": "MAXIMIZE",
        },
    )

    # Initial run and finalization
    service.run_experiment(
        project_id=project.id,
        experiment_id=frozen_exp.id,
        auto_finalize=True,
    )

    db_session.refresh(exp)
    assert exp.locked_test_consumed is True

    # Second finalization attempt MUST raise HTTPException 400
    with pytest.raises(HTTPException) as exc_info:
        service.finalize_experiment(exp.id)

    assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
    assert "already been consumed" in str(exc_info.value.detail).lower()


# =============================================================================
# 3. Diagnostic Rerun Writes TEST_REUSED_DIAGNOSTIC Split
# =============================================================================

def test_diagnostic_rerun_stores_test_reused_diagnostic_split(db_session, day4_experiment_env):
    """
    Verify rerun_locked_test_diagnostic stores metrics strictly with
    split='TEST_REUSED_DIAGNOSTIC' without altering authoritative evidence.
    """
    project, dataset, user = day4_experiment_env
    service = ExperimentService(db_session)

    exp = service.exp_repo.create_experiment(
        project_id=project.id,
        task_type="CLASSIFICATION",
        status=ExperimentState.CREATED.value,
    )

    frozen_exp = service.freeze_experiment_config(
        exp.id,
        config_override={
            "algorithms": ["LogisticRegression"],
            "folds": 3,
            "seed": 42,
            "selection_metric": "macro_f1",
            "selection_direction": "MAXIMIZE",
        },
    )

    service.run_experiment(
        project_id=project.id,
        experiment_id=frozen_exp.id,
        auto_finalize=True,
    )

    initial_winner_id = exp.selected_model_id
    initial_status = exp.status

    # Initial locked metrics count
    initial_locked_count = db_session.query(ModelMetric).filter_by(
        model_id=initial_winner_id,
        split="LOCKED_TEST"
    ).count()
    assert initial_locked_count > 0

    # Call diagnostic rerun
    diag_res = service.rerun_locked_test_diagnostic(exp.id)
    assert diag_res["split"] == "TEST_REUSED_DIAGNOSTIC"
    assert diag_res["selected_model_id"] == initial_winner_id

    # Verify TEST_REUSED_DIAGNOSTIC rows exist in DB
    diag_metrics = db_session.query(ModelMetric).filter_by(
        model_id=initial_winner_id,
        split="TEST_REUSED_DIAGNOSTIC"
    ).all()
    assert len(diag_metrics) > 0

    # Verify LOCKED_TEST rows were not overwritten or deleted
    after_locked_count = db_session.query(ModelMetric).filter_by(
        model_id=initial_winner_id,
        split="LOCKED_TEST"
    ).count()
    assert after_locked_count == initial_locked_count

    # Verify experiment winner and status remain untouched
    db_session.refresh(exp)
    assert exp.selected_model_id == initial_winner_id
    assert exp.status == initial_status


# =============================================================================
# 4. Query-Level Exclusion from Leaderboard & Repository
# =============================================================================

def test_query_level_exclusion_from_leaderboard_and_repository(client, db_session):
    """
    Verify that TEST_REUSED_DIAGNOSTIC metric rows are excluded at the query level
    from repository queries and leaderboard API responses.
    """
    token = get_auth_token(client, email="lb_diag_test@studio.com")
    headers = {"Authorization": f"Bearer {token}"}

    proj_resp = client.post("/api/v1/projects", headers=headers, json={
        "project_name": "Diag Exclusion Project",
        "task_type": "CLASSIFICATION"
    })
    assert proj_resp.status_code == 201
    proj_id = proj_resp.json()["id"]

    repo = ExperimentRepository(db_session)
    exp = repo.create_experiment(
        project_id=uuid.UUID(proj_id),
        task_type="CLASSIFICATION",
        selection_metric="macro_f1",
        selection_direction="MAXIMIZE",
        status=ExperimentState.REGISTERED.value
    )

    model = repo.add_trained_model(
        experiment_id=exp.id,
        algorithm_name="LogisticRegression",
        hyperparameters={},
        quick_cv_score=0.75,
        model_selection_score=75.0,
        status=ModelState.DEPLOYABLE.value,
    )
    exp.selected_model_id = model.id
    db_session.commit()

    # Add CV_MEAN, LOCKED_TEST, and a synthetic high-scoring TEST_REUSED_DIAGNOSTIC
    m_cv = ModelMetric(model_id=model.id, metric_name="macro_f1", split="CV_MEAN", metric_value=0.75)
    m_lt = ModelMetric(model_id=model.id, metric_name="macro_f1", split="LOCKED_TEST", metric_value=0.73)
    m_diag = ModelMetric(model_id=model.id, metric_name="macro_f1", split="TEST_REUSED_DIAGNOSTIC", metric_value=0.99)
    db_session.add_all([m_cv, m_lt, m_diag])
    db_session.commit()

    # 1. Repository Query-level check with exclude_diagnostic=True
    non_diag_metrics = repo.get_model_metrics(model.id, exclude_diagnostic=True)
    splits = [m.split for m in non_diag_metrics]
    assert "CV_MEAN" in splits
    assert "LOCKED_TEST" in splits
    assert "TEST_REUSED_DIAGNOSTIC" not in splits

    # 2. API Leaderboard query check
    resp = client.get(f"/api/v1/projects/{proj_id}/leaderboard", headers=headers)
    assert resp.status_code == status.HTTP_200_OK
    data = resp.json()

    assert len(data["models"]) == 1
    returned_metrics = data["models"][0]["metrics"]
    returned_splits = [m["split"] for m in returned_metrics]
    assert "TEST_REUSED_DIAGNOSTIC" not in returned_splits
    assert "CV_MEAN" in returned_splits
    assert "LOCKED_TEST" in returned_splits


# =============================================================================
# 5. Query-Level Exclusion from Deployment Gate
# =============================================================================

def test_query_level_exclusion_from_deployment_gate(db_session, create_test_user, tmp_path):
    """
    Verify deployment gate locked_test_evaluated check strictly queries
    split == 'LOCKED_TEST' and is NOT satisfied by split == 'TEST_REUSED_DIAGNOSTIC'.
    """
    user = create_test_user("gate_diag_user@studio.ml", "ADMIN")

    project = Project(
        id=uuid4(),
        owner_id=user.id,
        project_name="Gate Diag Project",
        task_type="CLASSIFICATION",
        target_column="target",
        pipeline_stage="SPLIT",
    )
    db_session.add(project)
    db_session.flush()

    repo = ExperimentRepository(db_session)
    exp = repo.create_experiment(
        project_id=project.id,
        task_type="CLASSIFICATION",
        status=ExperimentState.REGISTERED.value
    )

    # Create dummy artifact file for disk check
    artifact_dir = tmp_path / "models"
    artifact_dir.mkdir(parents=True, exist_ok=True)
    artifact_file = artifact_dir / "model.joblib"
    artifact_file.write_bytes(b"dummy_artifact_bytes")

    import hashlib
    hasher = hashlib.sha256()
    hasher.update(b"dummy_artifact_bytes")
    checksum = hasher.hexdigest()

    fs_snap = FeatureSelectionSnapshot(
        id=uuid4(),
        experiment_id=exp.id,
        final_selected_features=["f1"],
        final_selection_method="test"
    )
    db_session.add(fs_snap)
    db_session.flush()

    model = repo.add_trained_model(
        experiment_id=exp.id,
        algorithm_name="LogisticRegression",
        hyperparameters={},
        status=ModelState.DEPLOYABLE.value,
    )
    model.artifact_path = str(artifact_file)
    model.artifact_checksum = checksum
    model.feature_selection_snapshot_id = fs_snap.id
    exp.selected_model_id = model.id
    db_session.commit()

    # Add ONLY a TEST_REUSED_DIAGNOSTIC metric (NO LOCKED_TEST metric)
    m_diag = ModelMetric(
        model_id=model.id,
        metric_name="macro_f1",
        split="TEST_REUSED_DIAGNOSTIC",
        metric_value=0.95
    )
    db_session.add(m_diag)
    db_session.commit()

    gate_service = DeploymentGateService(db_session)
    gate = gate_service.check_gate(model.id)

    # Condition locked_test_evaluated MUST be False because no split='LOCKED_TEST' exists
    assert gate.locked_test_evaluated is False
    assert gate.gate_passed is False
