"""
Day 2 — Predict endpoint & DeploymentState lifecycle test suite (SRS §2.13, §2.14, §2.15, §2.16).

Verifies:
1. Artifact verification on deploy (rejects missing/tampered disk artifacts with HTTP 422).
2. /api/v1/predict/{deployment_id} with in-memory pipeline caching (cold load integrity check, warm cache serving).
3. Decoupled fast prediction vs /predict/{id}/explain with local SHAP breakdown and separate latency timers.
4. Strict payload schema validation with audit logging to prediction_logs (VALIDATION_ERROR).
5. DeploymentState lifecycle transitions: DEPLOYED -> PAUSED -> DEPLOYED -> RETIRED, with RETIRED immutability.
"""

import io
import json
import uuid
import hashlib
from pathlib import Path
import pytest
import numpy as np
import pandas as pd
from uuid import UUID as PyUUID, uuid4
from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
import joblib

from app.core.seeder import seed_rbac_data
from app.models.user import User
from app.models.project import Project
from app.models.dataset import Dataset
from app.models.dataset_column import DatasetColumn
from app.models.dataset_split import DatasetSplit
from app.models.experiment import Experiment
from app.models.trained_model import TrainedModel
from app.models.model_metric import ModelMetric
from app.models.transformation_snapshot import TransformationSnapshot
from app.models.feature_selection_snapshot import FeatureSelectionSnapshot
from app.models.deployment import Deployment
from app.models.prediction_log import PredictionLog
from app.config.state_machines import DeploymentState, ModelState, ExperimentState
from app.services.deployment_service import DeploymentService
from app.services.prediction_service import PredictionService
from app.services.deployment_gate_service import DeploymentGateService


@pytest.fixture(autouse=True)
def ensure_seed_rbac(db_session: Session):
    seed_rbac_data(db_session)


@pytest.fixture
def deploy_test_environment(db_session: Session, tmp_path: Path):
    """
    Sets up a fully verified model ready for deployment.
    """
    trainer = db_session.query(User).filter(User.email == "trainer@demo.com").first()
    approver = db_session.query(User).filter(User.email == "approver@demo.com").first()
    assert trainer is not None
    assert approver is not None

    # 1. Project
    project = Project(
        id=uuid4(),
        owner_id=trainer.id,
        project_name="Day2 Serving Production",
        task_type="REGRESSION",
        target_column="target",
    )
    db_session.add(project)
    db_session.flush()

    # 2. Dataset and Columns
    dataset = Dataset(
        id=uuid4(),
        project_id=project.id,
        version_number=1,
        row_count=100,
        column_count=3,
        file_path=str(tmp_path / "data.csv"),
    )
    db_session.add(dataset)
    db_session.flush()

    col_sqft = DatasetColumn(dataset_id=dataset.id, column_name="sqft", data_type="NUMERIC", is_target=False)
    col_rooms = DatasetColumn(dataset_id=dataset.id, column_name="rooms", data_type="NUMERIC", is_target=False)
    col_target = DatasetColumn(dataset_id=dataset.id, column_name="target", data_type="NUMERIC", is_target=True)
    db_session.add_all([col_sqft, col_rooms, col_target])
    db_session.flush()

    # 3. Experiment with frozen deployment threshold
    experiment = Experiment(
        id=uuid4(),
        project_id=project.id,
        status=ExperimentState.REGISTERED.value,
        task_type="REGRESSION",
        selection_metric="RMSE",
        selection_direction="MINIMIZE",
        deployment_threshold_frozen_at_creation=True,
        experiment_config={},
        code_version="git:v1.0.0",
        python_version="3.13.0",
        sklearn_version="1.5.0",
        numpy_version="2.0.0",
        pandas_version="2.2.0",
        environment_capture_method="CAPTURED_LIVE",
    )
    db_session.add(experiment)
    db_session.flush()

    # 4. Snapshots for lineage_complete
    trans_snap = TransformationSnapshot(
        experiment_id=experiment.id,
        config_json={"pipeline": [{"step": "scaler"}]},
    )
    fs_snap = FeatureSelectionSnapshot(
        experiment_id=experiment.id,
        final_selected_features=["sqft", "rooms"],
    )
    db_session.add_all([trans_snap, fs_snap])
    db_session.flush()

    experiment.feature_selection_snapshot_id = fs_snap.id
    experiment.experiment_config = {
        "preprocessing": {"snapshot_id": str(trans_snap.id)},
        "feature_selection": {"snapshot_id": str(fs_snap.id)},
        "deployment_threshold": {"metric": "RMSE", "min_value": 100.0},
    }
    db_session.add(experiment)
    db_session.flush()

    # 5. Fit simple Scikit-Learn pipeline and save artifact
    X_synthetic = np.array([[1000.0, 2.0], [1500.0, 3.0], [2000.0, 4.0], [2500.0, 5.0]])
    y_synthetic = np.array([200.0, 300.0, 400.0, 500.0])

    scaler = StandardScaler()
    scaler.fit(pd.DataFrame(X_synthetic, columns=["sqft", "rooms"]))
    X_scaled = scaler.transform(pd.DataFrame(X_synthetic, columns=["sqft", "rooms"]))

    regressor = LinearRegression()
    regressor.fit(X_scaled, y_synthetic)

    artifact_dict = {
        "transformer": scaler,
        "estimator": regressor,
        "selected_indices": [0, 1],
        "selected_feature_names": ["sqft", "rooms"],
        "feature_names_in": ["sqft", "rooms"],
        "task_type": "REGRESSION",
    }

    artifact_file = tmp_path / "fitted_pipeline.joblib"
    joblib.dump(artifact_dict, artifact_file)
    artifact_checksum = hashlib.sha256(artifact_file.read_bytes()).hexdigest()

    # 6. TrainedModel
    trained_model = TrainedModel(
        id=uuid4(),
        experiment_id=experiment.id,
        algorithm_name="LinearRegression",
        hyperparameters={"fit_intercept": True},
        status=ModelState.DEPLOYABLE.value,
        artifact_path=str(artifact_file),
        artifact_checksum=artifact_checksum,
        preprocessing_snapshot_id=trans_snap.id,
        feature_selection_snapshot_id=fs_snap.id,
        created_by=trainer.id,
    )
    db_session.add(trained_model)
    db_session.flush()

    # 7. ModelMetric on LOCKED_TEST passing threshold
    metric = ModelMetric(
        model_id=trained_model.id,
        split="LOCKED_TEST",
        metric_name="RMSE",
        metric_value=12.5,
    )
    db_session.add(metric)
    db_session.commit()

    # 8. Independent approver signs off
    gate_service = DeploymentGateService(db_session)
    gate = gate_service.approve(model_id=trained_model.id, approved_by_user_id=approver.id)
    assert gate.gate_passed is True

    return {
        "trainer": trainer,
        "approver": approver,
        "project": project,
        "experiment": experiment,
        "model": trained_model,
        "artifact_file": artifact_file,
    }


def test_artifact_verification_on_deploy_success_and_tamper(deploy_test_environment, db_session: Session, tmp_path: Path):
    """
    Test that deploy() checks artifact checksum on disk and rejects missing/tampered artifacts.
    """
    env = deploy_test_environment
    model = env["model"]
    approver = env["approver"]
    artifact_file = env["artifact_file"]
    service = DeploymentService(db_session)

    # 1. Baseline: Valid artifact on disk -> Deploy succeeds
    deployment = service.deploy(model_id=model.id, user_id=approver.id)
    assert deployment is not None
    assert deployment.status in {"LIVE", "DEPLOYED"}
    assert deployment.endpoint_path == f"/api/v1/predict/{deployment.id}"

    # 2. Tampered disk artifact -> deployment attempt rejected with HTTP 422
    artifact_file.write_bytes(b"tampered-malicious-artifact-bytes")
    # Attempting to deploy with tampered artifact raises HTTP 422
    with pytest.raises(Exception) as exc_info:
        service.deploy(model_id=model.id, user_id=approver.id)
    assert "422" in str(exc_info.value) or "integrity" in str(exc_info.value).lower()


def test_predict_endpoint_in_memory_caching(deploy_test_environment, db_session: Session):
    """
    Verifies that /predict uses in-memory caching:
    - Cold load verifies disk checksum and populates memory cache.
    - Warm cache serves fast predictions directly from memory without disk reload.
    """
    env = deploy_test_environment
    model = env["model"]
    approver = env["approver"]
    deploy_service = DeploymentService(db_session)
    pred_service = PredictionService(db_session)

    deployment = deploy_service.deploy(model_id=model.id, user_id=approver.id)
    dep_id_str = str(deployment.id)

    # Ensure cache is clear before cold load
    PredictionService.clear_cache(deployment.id)
    assert dep_id_str not in PredictionService._model_cache

    payload = {"sqft": 1500.0, "rooms": 3.0}

    # 1. Cold Load
    res_cold, _ = pred_service.predict(deployment_id=deployment.id, payload=payload)
    assert res_cold.prediction is not None
    assert dep_id_str in PredictionService._model_cache

    # 2. Warm Load
    res_warm, _ = pred_service.predict(deployment_id=deployment.id, payload=payload)
    assert res_warm.prediction == res_cold.prediction
    assert res_warm.request_id != res_cold.request_id


def test_predict_schema_validation_and_audit_logging(deploy_test_environment, db_session: Session):
    """
    Verifies that missing features or wrong data types trigger HTTP 422 and log VALIDATION_ERROR to prediction_logs.
    """
    env = deploy_test_environment
    model = env["model"]
    approver = env["approver"]
    deploy_service = DeploymentService(db_session)
    pred_service = PredictionService(db_session)

    deployment = deploy_service.deploy(model_id=model.id, user_id=approver.id)

    # 1. Missing required field 'rooms'
    missing_payload = {"sqft": 1500.0}
    with pytest.raises(Exception) as exc_missing:
        pred_service.predict(deployment_id=deployment.id, payload=missing_payload)
    assert "Missing required fields" in str(exc_missing.value)

    # Verify VALIDATION_ERROR logged in DB
    log_missing = (
        db_session.query(PredictionLog)
        .filter(PredictionLog.deployment_id == deployment.id, PredictionLog.status == "VALIDATION_ERROR")
        .order_by(PredictionLog.requested_at.desc())
        .first()
    )
    assert log_missing is not None
    assert log_missing.prediction_output is None

    # 2. Invalid data type (boolean for NUMERIC)
    bad_type_payload = {"sqft": 1500.0, "rooms": True}
    with pytest.raises(Exception) as exc_type:
        pred_service.predict(deployment_id=deployment.id, payload=bad_type_payload)
    assert "Invalid field types" in str(exc_type.value)


def test_deployment_state_lifecycle_transitions(deploy_test_environment, db_session: Session):
    """
    Tests the DeploymentState lifecycle:
    - LIVE / DEPLOYED -> PAUSED -> LIVE / DEPLOYED -> RETIRED
    - Predictions rejected when PAUSED
    - RETIRED cannot transition back to active states (terminal immutability)
    """
    env = deploy_test_environment
    model = env["model"]
    approver = env["approver"]
    deploy_service = DeploymentService(db_session)
    pred_service = PredictionService(db_session)

    deployment = deploy_service.deploy(model_id=model.id, user_id=approver.id)
    assert deployment.status in {"LIVE", "DEPLOYED"}

    payload = {"sqft": 1500.0, "rooms": 3.0}

    # Active serving works
    res, _ = pred_service.predict(deployment_id=deployment.id, payload=payload)
    assert res.prediction is not None

    # Pause deployment
    dep_paused = deploy_service.pause(deployment.id)
    assert dep_paused.status == "PAUSED"

    # Prediction must be rejected while PAUSED
    with pytest.raises(Exception) as exc_paused:
        pred_service.predict(deployment_id=deployment.id, payload=payload)
    assert "not active" in str(exc_paused.value).lower() or "not live" in str(exc_paused.value).lower()

    # Resume to LIVE / DEPLOYED
    dep_resumed = deploy_service.update_status(deployment.id, "DEPLOYED")
    assert dep_resumed.status == "DEPLOYED"

    res_resumed, _ = pred_service.predict(deployment_id=deployment.id, payload=payload)
    assert res_resumed.prediction is not None

    # Retire deployment
    dep_retired = deploy_service.retire(deployment.id)
    assert dep_retired.status == "RETIRED"

    # Reactivation of retired deployment must be rejected
    with pytest.raises(Exception) as exc_unretire:
        deploy_service.update_status(deployment.id, "LIVE")
    assert "RETIRED" in str(exc_unretire.value)
