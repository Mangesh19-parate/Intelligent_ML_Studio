"""
Day 4 — Explain + Prediction Logging test suite (SRS §2.14, §2.15).

Verifies:
1. Decoupled local SHAP explain endpoint (/api/v1/predict/{deployment_id}/explain):
   - Returns prediction, explanation breakdown (base_value, contributions, explainer_type).
   - Segregates prediction latency vs explanation latency distinctly.
2. Fast prediction endpoint (/api/v1/predict/{deployment_id}):
   - Executes lightweight prediction without SHAP overhead.
   - prediction_logs record has explanation_requested=False, explanation_latency_ms=None.
3. Privacy & Payload Modes (HASHED default vs FULL/OFF):
   - HASHED: input_payload is NULL, schema_hash is populated.
   - FULL: input_payload is persisted in JSON format.
4. Observability for validation errors:
   - Missing fields / wrong data types log status='VALIDATION_ERROR' in prediction_logs.
"""

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
from app.config.state_machines import ModelState, ExperimentState
from app.services.deployment_service import DeploymentService
from app.services.prediction_service import PredictionService
from app.services.deployment_gate_service import DeploymentGateService


@pytest.fixture(autouse=True)
def ensure_seed_rbac(db_session: Session):
    seed_rbac_data(db_session)


@pytest.fixture
def explain_test_environment(db_session: Session, tmp_path: Path):
    """
    Sets up a deployed model with training background data for SHAP explanations.
    """
    trainer = db_session.query(User).filter(User.email == "trainer@demo.com").first()
    approver = db_session.query(User).filter(User.email == "approver@demo.com").first()

    # 1. Project
    project = Project(
        id=uuid4(),
        owner_id=trainer.id,
        project_name="Explainability Demo Project",
        task_type="REGRESSION",
        target_column="target",
    )
    db_session.add(project)
    db_session.flush()

    # 2. Dataset and Splits
    df = pd.DataFrame({
        "feature_a": [10.0, 20.0, 30.0, 40.0, 50.0] * 10,
        "feature_b": [1.0, 2.0, 3.0, 4.0, 5.0] * 10,
        "target": [100.0, 200.0, 300.0, 400.0, 500.0] * 10,
    })
    data_file = tmp_path / "explain_data.csv"
    df.to_csv(data_file, index=False)

    dataset = Dataset(
        id=uuid4(),
        project_id=project.id,
        version_number=1,
        row_count=len(df),
        column_count=3,
        file_path=str(data_file),
    )
    db_session.add(dataset)
    db_session.flush()

    col_a = DatasetColumn(dataset_id=dataset.id, column_name="feature_a", data_type="NUMERIC", is_target=False)
    col_b = DatasetColumn(dataset_id=dataset.id, column_name="feature_b", data_type="NUMERIC", is_target=False)
    col_t = DatasetColumn(dataset_id=dataset.id, column_name="target", data_type="NUMERIC", is_target=True)
    db_session.add_all([col_a, col_b, col_t])

    dev_indices = list(range(40))
    locked_indices = list(range(40, 50))
    dev_split = DatasetSplit(dataset_id=dataset.id, split_type="DEVELOPMENT", split_seed=42, row_indices=dev_indices)
    locked_split = DatasetSplit(dataset_id=dataset.id, split_type="LOCKED_TEST", split_seed=42, row_indices=locked_indices)
    db_session.add_all([dev_split, locked_split])
    db_session.flush()

    # 3. Experiment
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

    # 4. Snapshots
    trans_snap = TransformationSnapshot(
        experiment_id=experiment.id,
        config_json={"pipeline": [{"step": "scaler"}]},
    )
    fs_snap = FeatureSelectionSnapshot(
        experiment_id=experiment.id,
        final_selected_features=["feature_a", "feature_b"],
    )
    db_session.add_all([trans_snap, fs_snap])
    db_session.flush()

    experiment.feature_selection_snapshot_id = fs_snap.id
    experiment.experiment_config = {
        "preprocessing": {"snapshot_id": str(trans_snap.id)},
        "feature_selection": {"snapshot_id": str(fs_snap.id)},
        "deployment_threshold": {"metric": "RMSE", "min_value": 50.0},
    }
    db_session.add(experiment)
    db_session.flush()

    # 5. Fit Scikit-Learn pipeline
    scaler = StandardScaler()
    X_dev = df.iloc[dev_indices][["feature_a", "feature_b"]]
    y_dev = df.iloc[dev_indices]["target"]
    scaler.fit(X_dev)
    X_dev_trans = scaler.transform(X_dev)

    regressor = LinearRegression()
    regressor.fit(X_dev_trans, y_dev)

    artifact_dict = {
        "transformer": scaler,
        "estimator": regressor,
        "selected_indices": [0, 1],
        "selected_feature_names": ["feature_a", "feature_b"],
        "feature_names_in": ["feature_a", "feature_b"],
        "task_type": "REGRESSION",
    }
    artifact_file = tmp_path / "explain_model.joblib"
    joblib.dump(artifact_dict, artifact_file)
    artifact_checksum = hashlib.sha256(artifact_file.read_bytes()).hexdigest()

    # 6. Model
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

    metric = ModelMetric(
        model_id=trained_model.id,
        split="LOCKED_TEST",
        metric_name="RMSE",
        metric_value=5.0,
    )
    db_session.add(metric)
    db_session.commit()

    # 7. Approve & Deploy
    gate_service = DeploymentGateService(db_session)
    gate_service.approve(model_id=trained_model.id, approved_by_user_id=approver.id)

    deploy_service = DeploymentService(db_session)
    deployment = deploy_service.deploy(model_id=trained_model.id, user_id=approver.id)

    return {
        "trainer": trainer,
        "approver": approver,
        "deployment": deployment,
        "model": trained_model,
    }


def test_decoupled_fast_predict_vs_explain(explain_test_environment, client: TestClient, db_session: Session):
    """
    Verifies that /predict (fast path) and /predict/.../explain (local SHAP) operate with segregated latencies.
    """
    deployment = explain_test_environment["deployment"]
    valid_payload = {"feature_a": 25.0, "feature_b": 2.5}

    # 1. Fast Path: POST /api/v1/predict/{deployment_id}
    res_fast = client.post(f"/api/v1/predict/{deployment_id_to_str(deployment.id)}", json=valid_payload)
    assert res_fast.status_code == status.HTTP_200_OK
    data_fast = res_fast.json()
    assert "prediction" in data_fast
    assert "latency_ms" in data_fast
    assert "explanation" not in data_fast

    req_fast_id = PyUUID(data_fast["request_id"])
    log_fast = db_session.query(PredictionLog).filter(PredictionLog.request_id == req_fast_id).first()
    assert log_fast is not None
    assert log_fast.explanation_requested is False
    assert log_fast.explanation_latency_ms is None

    # 2. Explain Path: POST /api/v1/predict/{deployment_id}/explain
    res_explain = client.post(f"/api/v1/predict/{deployment_id_to_str(deployment.id)}/explain", json=valid_payload)
    assert res_explain.status_code == status.HTTP_200_OK
    data_explain = res_explain.json()

    assert "prediction" in data_explain
    assert "explanation" in data_explain
    assert "contributions" in data_explain["explanation"]
    assert "base_value" in data_explain["explanation"]
    assert "explainer_type" in data_explain["explanation"]
    assert "latency_ms" in data_explain
    assert "explanation_latency_ms" in data_explain
    assert "total_latency_ms" in data_explain

    assert data_explain["explanation_latency_ms"] >= 0
    assert data_explain["total_latency_ms"] == data_explain["latency_ms"] + data_explain["explanation_latency_ms"]

    req_explain_id = PyUUID(data_explain["request_id"])
    log_explain = db_session.query(PredictionLog).filter(PredictionLog.request_id == req_explain_id).first()
    assert log_explain is not None
    assert log_explain.explanation_requested is True
    assert log_explain.explanation_latency_ms is not None


def test_payload_privacy_modes_hashed_and_full(explain_test_environment, db_session: Session):
    """
    Verifies that HASHED payload_mode leaves input_payload null, and FULL populates input_payload.
    """
    deployment = explain_test_environment["deployment"]
    pred_service = PredictionService(db_session)
    payload = {"feature_a": 35.0, "feature_b": 3.5}

    # 1. HASHED Mode (Default per SRS §2.15)
    res_hashed, _ = pred_service.predict(deployment_id=deployment.id, payload=payload, payload_mode="HASHED")
    log_hashed = db_session.query(PredictionLog).filter(PredictionLog.request_id == res_hashed.request_id).first()
    assert log_hashed.payload_mode == "HASHED"
    assert log_hashed.input_payload is None
    assert log_hashed.schema_hash is not None and len(log_hashed.schema_hash) == 64

    # 2. FULL Mode (Explicit opt-in)
    res_full, _ = pred_service.predict(deployment_id=deployment.id, payload=payload, payload_mode="FULL")
    log_full = db_session.query(PredictionLog).filter(PredictionLog.request_id == res_full.request_id).first()
    assert log_full.payload_mode == "FULL"
    assert log_full.input_payload == payload


def test_validation_error_audit_logging(explain_test_environment, client: TestClient, db_session: Session):
    """
    Verifies that schema validation failures return HTTP 422 and are audit-logged as VALIDATION_ERROR.
    """
    deployment = explain_test_environment["deployment"]
    bad_payload = {"feature_a": 10.0}  # Missing 'feature_b'

    res = client.post(f"/api/v1/predict/{deployment_id_to_str(deployment.id)}", json=bad_payload)
    assert res.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    val_log = (
        db_session.query(PredictionLog)
        .filter(PredictionLog.deployment_id == deployment.id, PredictionLog.status == "VALIDATION_ERROR")
        .order_by(PredictionLog.requested_at.desc())
        .first()
    )
    assert val_log is not None
    assert val_log.prediction_output is None
    assert val_log.latency_ms >= 1


def deployment_id_to_str(d_id):
    return str(d_id)
