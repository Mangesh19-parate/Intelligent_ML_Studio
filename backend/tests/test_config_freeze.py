"""
Unit Tests for Experiment Configuration Freeze (SRS v9 §2 / Day 2).

Verifies:
1. Transition ExperimentState.CREATED -> ExperimentState.CONFIGURED on freeze.
2. Assembly and immutability of experiment_config snapshot.
3. Strict rejection of any re-freeze attempt with HTTP 409 Conflict.
4. Smooth progression from CONFIGURED -> TRAINING -> EVALUATED.
"""

from uuid import uuid4
import pytest
from fastapi import HTTPException, status
from fastapi.testclient import TestClient

from app.models.project import Project
from app.models.dataset import Dataset
from app.models.dataset_split import DatasetSplit
from app.models.transformation_config import TransformationConfig
from app.models.experiment import Experiment
from app.config.state_machines import ExperimentState
from app.services.experiment_service import ExperimentService


@pytest.fixture
def freeze_test_setup(db_session, create_test_user):
    """Sets up a project with transformation configs and a CREATED experiment."""
    user = create_test_user("freeze_tester@studio.ml", "ADMIN")

    project = Project(
        id=uuid4(),
        owner_id=user.id,
        project_name="Config Freeze Test Project",
        task_type="REGRESSION",
        target_column="target_val",
        pipeline_stage="TRANSFORMED",
    )
    db_session.add(project)
    db_session.commit()

    # Add a transformation config
    tc = TransformationConfig(
        id=uuid4(),
        project_id=project.id,
        column_name="num_feat",
        missing_value_strategy="MEAN",
        scaling_strategy="STANDARD",
        encoding_strategy=None,
        outlier_strategy="NONE",
        is_active=True,
    )
    db_session.add(tc)

    # Add dataset and split
    dataset = Dataset(
        id=uuid4(),
        project_id=project.id,
        file_path="mock/path/data.csv",
        version_number=1,
        row_count=100,
        column_count=2,
    )
    db_session.add(dataset)
    db_session.commit()

    split = DatasetSplit(
        id=uuid4(),
        dataset_id=dataset.id,
        split_type="DEVELOPMENT",
        split_seed=42,
        row_indices=list(range(80)),
    )
    db_session.add(split)
    db_session.commit()

    return {
        "user": user,
        "project": project,
        "dataset": dataset,
        "split": split,
    }


def test_freeze_experiment_config_transitions_created_to_configured(db_session, freeze_test_setup):
    """
    Test that calling freeze_experiment_config on a CREATED experiment:
    1. Populates experiment_config
    2. Transitions status from CREATED to CONFIGURED
    """
    project = freeze_test_setup["project"]
    service = ExperimentService(db_session)

    # Create experiment shell in CREATED status
    exp = service.exp_repo.create_experiment(
        project_id=project.id,
        task_type="REGRESSION",
        fold_count=5,
        cv_seed=1234,
        selection_metric="rmse",
        selection_direction="MINIMIZE",
        status=ExperimentState.CREATED.value,
        deployment_threshold_frozen_at_creation=False,
    )
    assert exp.status == ExperimentState.CREATED.value
    assert exp.experiment_config is None

    # Freeze config
    frozen_exp = service.freeze_experiment_config(
        experiment_id=exp.id,
        config_override={
            "algorithms": ["LinearRegression", "Ridge"],
            "folds": 5,
            "seed": 1234,
            "selection_metric": "rmse",
            "deployment_threshold": {"metric": "rmse", "min_value": 0.5},
        },
    )

    assert frozen_exp.status == ExperimentState.CONFIGURED.value
    assert frozen_exp.experiment_config is not None
    assert frozen_exp.experiment_config["task_type"] == "REGRESSION"
    assert frozen_exp.experiment_config["target"] == "target_val"
    assert frozen_exp.experiment_config["algorithms"] == ["LinearRegression", "Ridge"]
    assert frozen_exp.experiment_config["cv"]["folds"] == 5
    assert frozen_exp.experiment_config["deployment_threshold"]["min_value"] == 0.5
    assert frozen_exp.deployment_threshold_frozen_at_creation is True


def test_refreeze_attempt_is_strictly_rejected(db_session, freeze_test_setup):
    """
    Test that calling freeze_experiment_config on an already CONFIGURED experiment
    raises HTTP 409 Conflict.
    """
    project = freeze_test_setup["project"]
    service = ExperimentService(db_session)

    exp = service.exp_repo.create_experiment(
        project_id=project.id,
        task_type="REGRESSION",
        status=ExperimentState.CREATED.value,
    )

    # First freeze -> succeeds
    service.freeze_experiment_config(exp.id)
    db_session.refresh(exp)
    assert exp.status == ExperimentState.CONFIGURED.value

    # Second freeze attempt -> rejected with 409
    with pytest.raises(HTTPException) as exc_info:
        service.freeze_experiment_config(exp.id)
    assert exc_info.value.status_code == status.HTTP_409_CONFLICT
    assert "already frozen" in exc_info.value.detail


@pytest.mark.parametrize(
    "subsequent_status",
    [
        ExperimentState.TRAINING.value,
        ExperimentState.EVALUATED.value,
        ExperimentState.TEST_CONSUMED.value,
        ExperimentState.REGISTERED.value,
    ],
)
def test_refreeze_rejected_for_all_subsequent_lifecycle_states(db_session, freeze_test_setup, subsequent_status):
    """
    Re-freeze attempts on experiments in TRAINING, EVALUATED, TEST_CONSUMED, REGISTERED
    are all strictly rejected with HTTP 409 Conflict.
    """
    project = freeze_test_setup["project"]
    service = ExperimentService(db_session)

    exp = service.exp_repo.create_experiment(
        project_id=project.id,
        task_type="REGRESSION",
        status=subsequent_status,
        experiment_config={"already": "frozen"},
    )

    with pytest.raises(HTTPException) as exc_info:
        service.freeze_experiment_config(exp.id)
    assert exc_info.value.status_code == status.HTTP_409_CONFLICT


def test_freeze_via_api_endpoint(client: TestClient, db_session, freeze_test_setup, auth_headers):
    """
    Test the HTTP POST /api/v1/experiments/{id}/freeze endpoint.
    """
    project = freeze_test_setup["project"]
    user = freeze_test_setup["user"]
    headers = auth_headers(user)
    service = ExperimentService(db_session)

    exp = service.exp_repo.create_experiment(
        project_id=project.id,
        task_type="REGRESSION",
        status=ExperimentState.CREATED.value,
    )

    # 1. Successful freeze
    resp = client.post(
        f"/api/v1/experiments/{exp.id}/freeze",
        json={
            "algorithms": ["LinearRegression"],
            "folds": 3,
            "seed": 999,
        },
        headers=headers,
    )
    assert resp.status_code == status.HTTP_200_OK
    data = resp.json()
    assert data["status"] == "CONFIGURED"
    assert data["fold_count"] == 3

    # 2. Duplicate freeze attempt -> 409 Conflict
    resp_dup = client.post(
        f"/api/v1/experiments/{exp.id}/freeze",
        json={"folds": 5},
        headers=headers,
    )
    assert resp_dup.status_code == status.HTTP_409_CONFLICT
    assert "already frozen" in resp_dup.json()["detail"]


def test_configured_experiment_can_start_training(db_session, freeze_test_setup):
    """
    Verify that an experiment frozen in CONFIGURED can start training (transitioning to TRAINING)
    and retains its frozen config.
    """
    project = freeze_test_setup["project"]
    service = ExperimentService(db_session)

    exp = service.exp_repo.create_experiment(
        project_id=project.id,
        task_type="REGRESSION",
        status=ExperimentState.CREATED.value,
    )

    service.freeze_experiment_config(exp.id, config_override={"algorithms": ["Ridge"]})
    db_session.refresh(exp)
    assert exp.status == ExperimentState.CONFIGURED.value
    original_config = dict(exp.experiment_config)

    # Start training
    exp_training = service.start_training(exp.id)
    assert exp_training.status == ExperimentState.TRAINING.value
    assert exp_training.experiment_config == original_config
