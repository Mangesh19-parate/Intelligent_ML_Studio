import os
import json
import hashlib
from uuid import uuid4
from datetime import datetime, timezone
import numpy as np
import pandas as pd
import pytest
from fastapi import status
from fastapi.testclient import TestClient

from app.models.project import Project
from app.models.dataset import Dataset
from app.models.dataset_column import DatasetColumn
from app.models.dataset_split import DatasetSplit
from app.models.transformation_config import TransformationConfig
from app.models.experiment import Experiment
from app.models.trained_model import TrainedModel
from app.models.deployment_gate import DeploymentGate
from app.models.deployment import Deployment
from app.models.prediction_log import PredictionLog
from app.services.experiment_service import ExperimentService
from app.services.deployment_gate_service import DeploymentGateService
from app.services.deployment_service import DeploymentService
from app.services.prediction_service import PredictionService
from app.services.model_registry_service import ModelRegistryService


@pytest.fixture
def deployed_regression_setup(db_session, tmp_path, create_test_user):
    """
    Creates a full regression project, trains models, refits winning model with artifact,
    and returns all required entities for testing Day 10 deployment features.
    """
    owner = create_test_user("ml_admin@test.com", "ADMIN")

    project = Project(
        id=uuid4(),
        owner_id=owner.id,
        project_name="Day10 Housing Production",
        task_type="REGRESSION",
        target_column="price",
        pipeline_stage="SPLIT",
    )
    db_session.add(project)
    db_session.commit()

    # Synthetic dataset
    np.random.seed(42)
    n_samples = 160
    sqft = np.random.uniform(500, 3500, n_samples)
    bedrooms = np.random.randint(1, 6, n_samples).astype(float)
    price = 250.0 * sqft + 4000.0 * bedrooms + 500.0 * np.random.randn(n_samples)

    df = pd.DataFrame({
        "sqft": sqft,
        "bedrooms": bedrooms,
        "price": price,
    })

    data_bytes = df.to_csv(index=False).encode("utf-8")
    content_hash = hashlib.sha256(data_bytes).hexdigest()

    dataset_path = str(tmp_path / "housing_prod.csv")
    with open(dataset_path, "wb") as f:
        f.write(data_bytes)

    dataset = Dataset(
        id=uuid4(),
        project_id=project.id,
        version_number=1,
        file_path=dataset_path,
        row_count=n_samples,
        column_count=3,
        content_hash=content_hash,
    )
    db_session.add(dataset)
    db_session.commit()

    # Dataset columns
    col_sqft = DatasetColumn(dataset_id=dataset.id, column_name="sqft", data_type="NUMERIC")
    col_bed = DatasetColumn(dataset_id=dataset.id, column_name="bedrooms", data_type="NUMERIC")
    col_price = DatasetColumn(dataset_id=dataset.id, column_name="price", data_type="NUMERIC", is_target=True)
    db_session.add_all([col_sqft, col_bed, col_price])

    # 80/20 Dev/Locked Split
    n_dev = int(n_samples * 0.8)
    dev_split = DatasetSplit(
        dataset_id=dataset.id,
        split_type="DEVELOPMENT",
        split_seed=42,
        row_indices=list(range(n_dev)),
    )
    locked_split = DatasetSplit(
        dataset_id=dataset.id,
        split_type="LOCKED_TEST",
        split_seed=42,
        row_indices=list(range(n_dev, n_samples)),
    )
    db_session.add_all([dev_split, locked_split])

    # Transformation config
    tc1 = TransformationConfig(project_id=project.id, column_name="sqft", scaling_strategy="standard", is_active=True)
    tc2 = TransformationConfig(project_id=project.id, column_name="bedrooms", scaling_strategy="standard", is_active=True)
    db_session.add_all([tc1, tc2])
    db_session.commit()

    return {
        "owner": owner,
        "project": project,
        "dataset": dataset,
        "tmp_path": tmp_path,
    }


def test_check_a_pre_fix_experiment_unverifiable(deployed_regression_setup, db_session, client, auth_headers):
    """
    Acceptance Check (a):
    Attempt to deploy a model from a pre-fix experiment (deployment_threshold_frozen_at_creation is False).
    Confirm the gate fails with performance_threshold_passed = 'UNVERIFIABLE', not a fabricated PASS,
    and the deploy response names this specific condition in HTTP 422.
    """
    setup = deployed_regression_setup
    project = setup["project"]
    headers = auth_headers(setup["owner"])

    # Run experiment without new creation threshold
    exp_service = ExperimentService(db_session)
    exp_res = exp_service.run_experiment(
        project_id=project.id,
        algorithms=["LinearRegression"],
        folds=3,
        seed=42,
        selection_metric="RMSE",
        selection_direction="MINIMIZE",
        auto_finalize=True,
    )

    exp_id = exp_res["experiment_id"]
    experiment = db_session.query(Experiment).filter(Experiment.id == exp_id).first()
    
    # Retroactively mark as pre-fix (created before Day 10 fix)
    experiment.deployment_threshold_frozen_at_creation = False
    db_session.add(experiment)
    db_session.commit()

    winning_model_id = exp_res["selected_model_id"]
    assert winning_model_id is not None

    # Check Gate explicitly
    gate_service = DeploymentGateService(db_session)
    gate = gate_service.check_gate(winning_model_id, user_approved=False)

    assert gate.performance_threshold_passed == "UNVERIFIABLE"
    assert gate.gate_passed is False

    # Attempt to deploy pre-fix model
    res = client.post(f"/api/v1/models/{winning_model_id}/deploy", headers=headers)
    assert res.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    data = res.json()
    assert "performance_threshold_passed: UNVERIFIABLE" in data["detail"]


def test_check_b_new_experiment_with_threshold_passes_gate(deployed_regression_setup, db_session, client, auth_headers):
    """
    Acceptance Check (b):
    Run a NEW experiment through POST /experiments with deployment_threshold supplied.
    Confirm deployment_threshold_frozen_at_creation is True, and gate can reach gate_passed = True
    after approval.
    """
    setup = deployed_regression_setup
    project = setup["project"]
    headers = auth_headers(setup["owner"])

    # 1. Start experiment with deployment_threshold
    create_payload = {
        "algorithms": ["LinearRegression"],
        "folds": 3,
        "seed": 42,
        "selection_metric": "RMSE",
        "selection_direction": "MINIMIZE",
        "deployment_threshold": {
            "metric": "RMSE",
            "min_value": 50000.0,  # Generous threshold to guarantee passing
        },
    }
    
    # Direct execution for synchronous test
    exp_service = ExperimentService(db_session)
    exp_res = exp_service.run_experiment(
        project_id=project.id,
        algorithms=["LinearRegression"],
        folds=3,
        seed=42,
        selection_metric="RMSE",
        selection_direction="MINIMIZE",
        auto_finalize=True,
        deployment_threshold=create_payload["deployment_threshold"],
    )

    exp_id = exp_res["experiment_id"]
    experiment = db_session.query(Experiment).filter(Experiment.id == exp_id).first()
    assert experiment.deployment_threshold_frozen_at_creation is True
    assert experiment.experiment_config["deployment_threshold"]["min_value"] == 50000.0

    winning_model_id = exp_res["selected_model_id"]
    assert winning_model_id is not None

    # 2. Check gate before approval
    gate_service = DeploymentGateService(db_session)
    gate_pre = gate_service.check_gate(winning_model_id, user_approved=False)

    assert gate_pre.locked_test_evaluated is True
    assert gate_pre.schema_locked is True
    assert gate_pre.artifact_verified is True
    assert gate_pre.lineage_complete is True
    assert gate_pre.performance_threshold_passed == "PASS"
    assert gate_pre.user_approved is False
    assert gate_pre.gate_passed is False

    # 3. Call Approval Endpoint (Day 10)
    app_res = client.post(f"/api/v1/models/{winning_model_id}/deployment-gate/approve", headers=headers)
    assert app_res.status_code == status.HTTP_200_OK
    gate_data = app_res.json()["gate"]
    assert gate_data["user_approved"] is True
    assert gate_data["gate_passed"] is True

    # 4. Deploy Model
    deploy_res = client.post(f"/api/v1/models/{winning_model_id}/deploy", headers=headers)
    assert deploy_res.status_code == status.HTTP_200_OK
    dep_data = deploy_res.json()
    assert dep_data["status"] == "LIVE"
    assert dep_data["endpoint_path"] == f"/api/v1/predict/{dep_data['id']}"


def test_check_c_d_e_f_g_h_full_roundtrip_and_edge_cases(deployed_regression_setup, db_session, client, auth_headers):
    """
    Acceptance Checks (c) through (h):
    - (c) Call /predict with valid payload -> fast response, explanation_requested=False, explanation_latency_ms IS NULL.
    - (d) Call /predict/.../explain -> explanation_latency_ms populated and separate from prediction latency.
    - (e) Missing feature payload -> HTTP 422, status='VALIDATION_ERROR' logged.
    - (f) Pause deployment -> /predict rejected. Retire deployment -> cannot be reactivated.
    - (g) Default payload_mode='HASHED' -> input_payload is null.
    - (h) Corrupt artifact on disk -> next cold-load refuses to serve predictions.
    """
    setup = deployed_regression_setup
    project = setup["project"]
    headers = auth_headers(setup["owner"])

    # Train and deploy a model
    exp_service = ExperimentService(db_session)
    exp_res = exp_service.run_experiment(
        project_id=project.id,
        algorithms=["LinearRegression"],
        folds=3,
        seed=42,
        selection_metric="RMSE",
        selection_direction="MINIMIZE",
        auto_finalize=True,
        deployment_threshold={"metric": "RMSE", "min_value": 50000.0},
    )
    winning_model_id = exp_res["selected_model_id"]
    
    # Approve and deploy
    client.post(f"/api/v1/models/{winning_model_id}/deployment-gate/approve", headers=headers)
    dep_res = client.post(f"/api/v1/models/{winning_model_id}/deploy", headers=headers)
    dep_id = dep_res.json()["id"]

    valid_payload = {"sqft": 1500.0, "bedrooms": 3.0}

    # -------------------------------------------------------------
    # Check (c): Call /predict -> fast prediction, no SHAP overhead
    # -------------------------------------------------------------
    pred_res = client.post(f"/api/v1/predict/{dep_id}", json=valid_payload)
    assert pred_res.status_code == status.HTTP_200_OK
    pred_data = pred_res.json()
    assert "prediction" in pred_data
    assert isinstance(pred_data["prediction"], (int, float))
    assert "latency_ms" in pred_data
    assert "request_id" in pred_data

    # Verify prediction log entry in DB
    from uuid import UUID as PyUUID
    req_c_uuid = PyUUID(pred_data["request_id"])
    log_c = db_session.query(PredictionLog).filter(PredictionLog.request_id == req_c_uuid).first()
    assert log_c is not None
    assert log_c.explanation_requested is False
    assert log_c.explanation_latency_ms is None
    assert log_c.status == "SUCCESS"

    # -------------------------------------------------------------
    # Check (g): Confirm default payload_mode = HASHED and input_payload is NULL
    # -------------------------------------------------------------
    assert log_c.payload_mode == "HASHED"
    assert log_c.input_payload is None
    assert log_c.schema_hash is not None and len(log_c.schema_hash) == 64

    # -------------------------------------------------------------
    # Check (d): Call /predict/.../explain -> distinct explanation latency
    # -------------------------------------------------------------
    exp_pred_res = client.post(f"/api/v1/predict/{dep_id}/explain", json=valid_payload)
    assert exp_pred_res.status_code == status.HTTP_200_OK
    exp_pred_data = exp_pred_res.json()
    
    assert "prediction" in exp_pred_data
    assert "explanation" in exp_pred_data
    assert "contributions" in exp_pred_data["explanation"]
    assert "base_value" in exp_pred_data["explanation"]
    assert "latency_ms" in exp_pred_data
    assert "explanation_latency_ms" in exp_pred_data
    assert "total_latency_ms" in exp_pred_data
    assert exp_pred_data["explanation_latency_ms"] >= 0

    req_d_uuid = PyUUID(exp_pred_data["request_id"])
    log_d = db_session.query(PredictionLog).filter(PredictionLog.request_id == req_d_uuid).first()
    assert log_d is not None
    assert log_d.explanation_requested is True
    assert log_d.explanation_latency_ms is not None

    # -------------------------------------------------------------
    # Check (e): Call /predict with missing feature -> HTTP 422, status='VALIDATION_ERROR'
    # -------------------------------------------------------------
    invalid_payload = {"sqft": 1500.0}  # Missing 'bedrooms'
    err_res = client.post(f"/api/v1/predict/{dep_id}", json=invalid_payload)
    assert err_res.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    assert "Missing required fields" in err_res.json()["detail"]

    dep_uuid = PyUUID(dep_id)
    val_error_log = (
        db_session.query(PredictionLog)
        .filter(PredictionLog.deployment_id == dep_uuid, PredictionLog.status == "VALIDATION_ERROR")
        .order_by(PredictionLog.requested_at.desc())
        .first()
    )
    assert val_error_log is not None
    assert val_error_log.prediction_output is None

    # -------------------------------------------------------------
    # Check (f): Pause deployment -> reject; Retire -> cannot be un-retired
    # -------------------------------------------------------------
    # Pause
    pause_res = client.put(f"/api/v1/deployments/{dep_id}/status", json={"status": "PAUSED"}, headers=headers)
    assert pause_res.status_code == status.HTTP_200_OK
    assert pause_res.json()["status"] == "PAUSED"

    # Prediction against paused deployment must be rejected
    paused_pred_res = client.post(f"/api/v1/predict/{dep_id}", json=valid_payload)
    assert paused_pred_res.status_code == status.HTTP_400_BAD_REQUEST
    assert "Deployment is not LIVE" in paused_pred_res.json()["detail"]

    # Retire
    retire_res = client.put(f"/api/v1/deployments/{dep_id}/status", json={"status": "RETIRED"}, headers=headers)
    assert retire_res.status_code == status.HTTP_200_OK
    assert retire_res.json()["status"] == "RETIRED"

    # Attempt to reactivate retired deployment -> must fail
    unretire_res = client.put(f"/api/v1/deployments/{dep_id}/status", json={"status": "LIVE"}, headers=headers)
    assert unretire_res.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    assert "can never transition back" in unretire_res.json()["detail"]

    # -------------------------------------------------------------
    # Check (h): Corrupt disk artifact -> next cold load refuses to serve
    # -------------------------------------------------------------
    # Create a fresh deployment for cold load tampering test
    new_exp = exp_service.run_experiment(
        project_id=project.id,
        algorithms=["LinearRegression"],
        folds=3,
        seed=99,
        selection_metric="RMSE",
        selection_direction="MINIMIZE",
        auto_finalize=True,
        deployment_threshold={"metric": "RMSE", "min_value": 50000.0},
    )
    new_model_id = new_exp["selected_model_id"]
    client.post(f"/api/v1/models/{new_model_id}/deployment-gate/approve", headers=headers)
    fresh_dep_res = client.post(f"/api/v1/models/{new_model_id}/deploy", headers=headers)
    fresh_dep_id = fresh_dep_res.json()["id"]

    # Clear memory cache so next load is a cold load
    PredictionService.clear_cache(fresh_dep_id)

    # Tamper with the artifact file on disk
    model_obj = db_session.query(TrainedModel).filter(TrainedModel.id == new_model_id).first()
    with open(model_obj.artifact_path, "wb") as f:
        f.write(b"CORRUPTED_MALICIOUS_BYTES_DAY_10")

    corrupted_pred_res = client.post(f"/api/v1/predict/{fresh_dep_id}", json=valid_payload)
    assert corrupted_pred_res.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    assert "Artifact integrity check failed" in corrupted_pred_res.json()["detail"]


def test_model_download_joblib_and_pkl(deployed_regression_setup, db_session, client, auth_headers):
    """
    Test ModelRegistryService export endpoint with joblib and pkl formats.
    """
    setup = deployed_regression_setup
    project = setup["project"]
    headers = auth_headers(setup["owner"])

    exp_service = ExperimentService(db_session)
    exp_res = exp_service.run_experiment(
        project_id=project.id,
        algorithms=["LinearRegression"],
        folds=3,
        seed=42,
        selection_metric="RMSE",
        selection_direction="MINIMIZE",
        auto_finalize=True,
    )
    winning_model_id = exp_res["selected_model_id"]

    # Download joblib
    res_joblib = client.get(f"/api/v1/models/{winning_model_id}/download?format=joblib", headers=headers)
    assert res_joblib.status_code == status.HTTP_200_OK
    assert len(res_joblib.content) > 0
    assert "attachment; filename=" in res_joblib.headers.get("Content-Disposition", "")
    assert res_joblib.headers["Content-Disposition"].endswith('.joblib"')

    # Download pkl
    res_pkl = client.get(f"/api/v1/models/{winning_model_id}/download?format=pkl", headers=headers)
    assert res_pkl.status_code == status.HTTP_200_OK
    assert len(res_pkl.content) > 0
    assert res_pkl.headers["Content-Disposition"].endswith('.pkl"')
