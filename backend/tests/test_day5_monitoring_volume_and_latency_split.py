"""
Day 5 — Operational Monitoring Telemetry Test Suite (SRS §2.14, §2.15).

Verifies:
1. Hourly bucketed request volume tracking with status breakdowns (SUCCESS, VALIDATION_ERROR, SERVER_ERROR).
2. Segregated latency calculation:
   - Base prediction percentiles (avg, p50, p95) without SHAP distortion.
   - Decoupled explained prediction latency metrics with subcomponent breakdown (base_avg_ms vs explanation_avg_ms).
3. Explicit error rate calculation isolating validation errors from internal server errors.
4. GET /api/v1/deployments/{id}/monitoring unified dashboard endpoint with lookback filtering.
"""

import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
import pytest
from uuid import uuid4
from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from sklearn.linear_model import LinearRegression
import joblib

from app.core.seeder import seed_rbac_data
from app.core.security import create_access_token
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
from app.services.monitoring_service import MonitoringService


@pytest.fixture(autouse=True)
def ensure_seed_rbac(db_session: Session):
    seed_rbac_data(db_session)


@pytest.fixture
def monitoring_test_deployment(db_session: Session, tmp_path: Path):
    """
    Sets up a deployed model ready for monitoring logs ingestion and telemetry testing.
    """
    trainer = db_session.query(User).filter(User.email == "trainer@demo.com").first()
    approver = db_session.query(User).filter(User.email == "approver@demo.com").first()

    # 1. Project
    project = Project(
        id=uuid4(),
        owner_id=trainer.id,
        project_name="Monitoring Telemetry Demo",
        task_type="REGRESSION",
        target_column="target",
    )
    db_session.add(project)
    db_session.flush()

    # 2. Dataset
    data_file = tmp_path / "dummy.csv"
    data_file.write_text("f1,f2,target\n1,2,3\n")
    dataset = Dataset(
        id=uuid4(),
        project_id=project.id,
        version_number=1,
        row_count=10,
        column_count=3,
        file_path=str(data_file),
    )
    db_session.add(dataset)
    db_session.flush()

    col1 = DatasetColumn(dataset_id=dataset.id, column_name="f1", data_type="NUMERIC", is_target=False)
    col2 = DatasetColumn(dataset_id=dataset.id, column_name="f2", data_type="NUMERIC", is_target=False)
    colt = DatasetColumn(dataset_id=dataset.id, column_name="target", data_type="NUMERIC", is_target=True)
    db_session.add_all([col1, col2, colt])

    dev_split = DatasetSplit(dataset_id=dataset.id, split_type="DEVELOPMENT", split_seed=42, row_indices=[0])
    locked_split = DatasetSplit(dataset_id=dataset.id, split_type="LOCKED_TEST", split_seed=42, row_indices=[0])
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

    fs_snap = FeatureSelectionSnapshot(experiment_id=experiment.id, final_selected_features=["f1", "f2"])
    trans_snap = TransformationSnapshot(experiment_id=experiment.id, config_json={})
    db_session.add_all([fs_snap, trans_snap])
    db_session.flush()
    experiment.feature_selection_snapshot_id = fs_snap.id
    experiment.transformation_snapshot_id = trans_snap.id

    # 4. Model Artifact
    model = LinearRegression()
    artifact_path = tmp_path / "model.joblib"
    joblib.dump(model, artifact_path)

    trained_model = TrainedModel(
        id=uuid4(),
        experiment_id=experiment.id,
        algorithm_name="LinearRegression",
        hyperparameters={"fit_intercept": True},
        status=ModelState.DEPLOYABLE.value,
        artifact_path=str(artifact_path),
        artifact_checksum="checksum",
        preprocessing_snapshot_id=trans_snap.id,
        feature_selection_snapshot_id=fs_snap.id,
        created_by=trainer.id,
    )
    db_session.add(trained_model)
    db_session.flush()

    # 5. Deployment
    deployment = Deployment(
        id=uuid4(),
        model_id=trained_model.id,
        deployed_by=approver.id,
        status="DEPLOYED",
        endpoint_path=f"/api/v1/predict/{trained_model.id}",
        deployed_at=datetime.now(timezone.utc),
    )
    db_session.add(deployment)
    db_session.commit()
    db_session.refresh(deployment)

    return deployment


def test_volume_over_time_bucketing(db_session: Session, monitoring_test_deployment: Deployment):
    """
    Verifies that volume_over_time aggregates requests into hourly buckets and correctly
    computes counts for SUCCESS, VALIDATION_ERROR, and SERVER_ERROR.
    """
    dep_id = monitoring_test_deployment.id
    now = datetime.now(timezone.utc)
    t_hour_0 = now.replace(minute=10, second=0, microsecond=0)
    t_hour_1 = (now - timedelta(hours=1)).replace(minute=20, second=0, microsecond=0)

    # Insert logs for t_hour_0 (2 success, 1 validation error)
    logs_h0 = [
        PredictionLog(
            id=uuid4(),
            deployment_id=dep_id,
            request_id=uuid4(),
            schema_hash="hash_h0_1",
            payload_mode="HASHED",
            status="SUCCESS",
            latency_ms=12,
            requested_at=t_hour_0,
        ),
        PredictionLog(
            id=uuid4(),
            deployment_id=dep_id,
            request_id=uuid4(),
            schema_hash="hash_h0_2",
            payload_mode="HASHED",
            status="SUCCESS",
            latency_ms=14,
            requested_at=t_hour_0 + timedelta(minutes=5),
        ),
        PredictionLog(
            id=uuid4(),
            deployment_id=dep_id,
            request_id=uuid4(),
            schema_hash="hash_h0_3",
            payload_mode="HASHED",
            status="VALIDATION_ERROR",
            latency_ms=2,
            requested_at=t_hour_0 + timedelta(minutes=10),
        ),
    ]

    # Insert logs for t_hour_1 (1 success, 1 server error)
    logs_h1 = [
        PredictionLog(
            id=uuid4(),
            deployment_id=dep_id,
            request_id=uuid4(),
            schema_hash="hash_h1_1",
            payload_mode="HASHED",
            status="SUCCESS",
            latency_ms=18,
            requested_at=t_hour_1,
        ),
        PredictionLog(
            id=uuid4(),
            deployment_id=dep_id,
            request_id=uuid4(),
            schema_hash="hash_h1_2",
            payload_mode="HASHED",
            status="SERVER_ERROR",
            latency_ms=50,
            requested_at=t_hour_1 + timedelta(minutes=15),
        ),
    ]

    db_session.add_all(logs_h0 + logs_h1)
    db_session.commit()

    service = MonitoringService(db_session)
    volume = service.volume_over_time(dep_id, lookback_hours=24)

    assert len(volume) == 2
    # Verify chronological ordering
    h1_bucket = volume[0]
    h0_bucket = volume[1]

    assert h1_bucket["total_requests"] == 2
    assert h1_bucket["success_count"] == 1
    assert h1_bucket["server_error_count"] == 1
    assert h1_bucket["validation_error_count"] == 0

    assert h0_bucket["total_requests"] == 3
    assert h0_bucket["success_count"] == 2
    assert h0_bucket["validation_error_count"] == 1
    assert h0_bucket["server_error_count"] == 0


def test_latency_summary_segregated_metrics(db_session: Session, monitoring_test_deployment: Deployment):
    """
    Verifies that base prediction latency and explained prediction latency are calculated
    completely separately, preventing heavy SHAP computations from skewing fast prediction telemetry.
    """
    dep_id = monitoring_test_deployment.id
    now = datetime.now(timezone.utc)

    # 4 Base predictions (fast): latencies = [10, 20, 30, 40] -> avg = 25, p50 = 25, p95 = 38.5
    base_logs = [
        PredictionLog(
            id=uuid4(),
            deployment_id=dep_id,
            request_id=uuid4(),
            schema_hash=f"hash_base_{i}",
            payload_mode="HASHED",
            status="SUCCESS",
            latency_ms=lat,
            explanation_requested=False,
            explanation_latency_ms=None,
            requested_at=now - timedelta(minutes=i * 2),
        )
        for i, lat in enumerate([10, 20, 30, 40])
    ]

    # 2 Explained predictions (slower due to SHAP):
    # Log 1: base = 15, shap = 100 -> total = 115
    # Log 2: base = 25, shap = 200 -> total = 225
    # Total avg = (115 + 225)/2 = 170.0, base_avg = 20.0, explanation_avg = 150.0
    explained_logs = [
        PredictionLog(
            id=uuid4(),
            deployment_id=dep_id,
            request_id=uuid4(),
            schema_hash="hash_exp_1",
            payload_mode="HASHED",
            status="SUCCESS",
            latency_ms=15,
            explanation_requested=True,
            explanation_latency_ms=100,
            requested_at=now - timedelta(minutes=10),
        ),
        PredictionLog(
            id=uuid4(),
            deployment_id=dep_id,
            request_id=uuid4(),
            schema_hash="hash_exp_2",
            payload_mode="HASHED",
            status="SUCCESS",
            latency_ms=25,
            explanation_requested=True,
            explanation_latency_ms=200,
            requested_at=now - timedelta(minutes=12),
        ),
    ]

    db_session.add_all(base_logs + explained_logs)
    db_session.commit()

    service = MonitoringService(db_session)
    latency = service.latency_summary(dep_id, lookback_hours=24)

    assert latency["total_measured_requests"] == 6

    # Verify base predictions metrics
    base = latency["base_predictions"]
    assert base["count"] == 4
    assert base["avg_ms"] == 25.0
    assert base["min_ms"] == 10.0
    assert base["max_ms"] == 40.0
    assert base["p50_ms"] == 25.0

    # Verify explained predictions metrics
    explained = latency["explained_predictions"]
    assert explained["count"] == 2
    assert explained["avg_ms"] == 170.0
    assert explained["min_ms"] == 115.0
    assert explained["max_ms"] == 225.0
    assert explained["base_avg_ms"] == 20.0
    assert explained["explanation_avg_ms"] == 150.0


def test_error_rate_breakdown(db_session: Session, monitoring_test_deployment: Deployment):
    """
    Verifies that error rates accurately separate client validation errors from internal server crashes.
    """
    dep_id = monitoring_test_deployment.id
    now = datetime.now(timezone.utc)

    # 10 requests: 7 SUCCESS, 2 VALIDATION_ERROR, 1 SERVER_ERROR
    logs = [
        PredictionLog(
            id=uuid4(),
            deployment_id=dep_id,
            request_id=uuid4(),
            schema_hash=f"hash_err_success_{i}",
            payload_mode="HASHED",
            status="SUCCESS",
            latency_ms=10,
            requested_at=now - timedelta(minutes=i),
        )
        for i in range(7)
    ] + [
        PredictionLog(
            id=uuid4(),
            deployment_id=dep_id,
            request_id=uuid4(),
            schema_hash="hash_err_val_1",
            payload_mode="HASHED",
            status="VALIDATION_ERROR",
            latency_ms=2,
            requested_at=now - timedelta(minutes=8),
        ),
        PredictionLog(
            id=uuid4(),
            deployment_id=dep_id,
            request_id=uuid4(),
            schema_hash="hash_err_val_2",
            payload_mode="HASHED",
            status="VALIDATION_ERROR",
            latency_ms=3,
            requested_at=now - timedelta(minutes=9),
        ),
        PredictionLog(
            id=uuid4(),
            deployment_id=dep_id,
            request_id=uuid4(),
            schema_hash="hash_err_srv_1",
            payload_mode="HASHED",
            status="SERVER_ERROR",
            latency_ms=100,
            requested_at=now - timedelta(minutes=10),
        ),
    ]

    db_session.add_all(logs)
    db_session.commit()

    service = MonitoringService(db_session)
    rates = service.error_rate(dep_id, lookback_hours=24)

    assert rates["total_requests"] == 10
    assert rates["success_count"] == 7
    assert rates["validation_error_count"] == 2
    assert rates["server_error_count"] == 1
    assert pytest.approx(rates["error_rate"], 0.001) == 0.3
    assert pytest.approx(rates["validation_error_rate"], 0.001) == 0.2
    assert pytest.approx(rates["server_error_rate"], 0.001) == 0.1


def test_monitoring_dashboard_endpoint(client: TestClient, db_session: Session, monitoring_test_deployment: Deployment):
    """
    Verifies that the GET /api/v1/deployments/{id}/monitoring route returns the complete
    monitoring dashboard with lookback window filtering.
    """
    dep_id = monitoring_test_deployment.id
    now = datetime.now(timezone.utc)

    # 1 recent log (within 1 hour)
    recent_log = PredictionLog(
        id=uuid4(),
        deployment_id=dep_id,
        request_id=uuid4(),
        schema_hash="hash_dash_recent",
        payload_mode="HASHED",
        status="SUCCESS",
        latency_ms=15,
        requested_at=now - timedelta(minutes=30),
    )
    # 1 old log (48 hours ago - should be excluded from lookback_hours=24)
    old_log = PredictionLog(
        id=uuid4(),
        deployment_id=dep_id,
        request_id=uuid4(),
        schema_hash="hash_dash_old",
        payload_mode="HASHED",
        status="SUCCESS",
        latency_ms=90,
        requested_at=now - timedelta(hours=48),
    )

    db_session.add_all([recent_log, old_log])
    db_session.commit()

    # Query monitoring endpoint with default lookback_hours=24
    user = db_session.query(User).filter(User.email == "trainer@demo.com").first()
    token = create_access_token(str(user.id))
    response = client.get(
        f"/api/v1/deployments/{dep_id}/monitoring?lookback_hours=24",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    assert data["deployment_id"] == str(dep_id)
    assert data["status"] == "DEPLOYED"
    assert "volume_over_time" in data
    assert "latency_summary" in data
    assert "error_rate" in data
    assert "recent_logs" in data

    # Lookback 24 should only measure 1 request in summary metrics
    assert data["latency_summary"]["total_measured_requests"] == 1
    assert data["error_rate"]["total_requests"] == 1

    # But recent_logs lists the audit logs regardless of lookback window (up to limit)
    assert len(data["recent_logs"]) == 2
