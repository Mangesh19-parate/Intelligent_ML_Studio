"""
Day 7 — Experiment Health Report Test Suite (SRS v9 §13).

Verifies:
1. Experiment Health Report endpoint (GET /api/v1/experiments/{id}/health).
2. Six immutable structural guarantees (static architectural proofs).
3. Dynamic per-experiment signals (fit diagnosis, evidence strength, checksum, locked test status, gate conditions).
4. Accurate risk flagging ('0 risks flagged' on healthy experiment vs 'N risks flagged' with severity and remediation on impaired experiments).
5. Critical risk flagging on disk artifact checksum mismatch/tampering.
"""

import hashlib
from datetime import datetime, timezone
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
from app.models.feature_selection_snapshot import FeatureSelectionSnapshot
from app.models.transformation_snapshot import TransformationSnapshot
from app.models.deployment_gate import DeploymentGate
from app.config.state_machines import ModelState, ExperimentState


@pytest.fixture(autouse=True)
def ensure_seed_rbac(db_session: Session):
    seed_rbac_data(db_session)


@pytest.fixture
def auth_headers(db_session: Session):
    trainer = db_session.query(User).filter(User.email == "trainer@demo.com").first()
    token = create_access_token(str(trainer.id))
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def healthy_experiment_setup(db_session: Session, tmp_path: Path):
    trainer = db_session.query(User).filter(User.email == "trainer@demo.com").first()
    approver = db_session.query(User).filter(User.email == "approver@demo.com").first()

    # 1. Project
    project = Project(
        id=uuid4(),
        owner_id=trainer.id,
        project_name="Healthy Experiment Demo",
        task_type="REGRESSION",
        target_column="target",
    )
    db_session.add(project)
    db_session.flush()

    # 2. Dataset
    data_file = tmp_path / "data.csv"
    data_file.write_text("f1,f2,target\n1,2,3\n")
    dataset = Dataset(
        id=uuid4(),
        project_id=project.id,
        version_number=1,
        row_count=100,
        column_count=3,
        file_path=str(data_file),
    )
    db_session.add(dataset)
    db_session.flush()

    # 3. Experiment
    experiment = Experiment(
        id=uuid4(),
        project_id=project.id,
        status=ExperimentState.REGISTERED.value,
        task_type="REGRESSION",
        selection_metric="RMSE",
        selection_direction="MINIMIZE",
        locked_test_consumed=True,
        locked_test_consumed_at=datetime.now(timezone.utc),
        experiment_config={"feature_selection": {"evidence_strength": "STRONG"}},
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
    fs_snap = FeatureSelectionSnapshot(
        experiment_id=experiment.id,
        final_selected_features=["f1", "f2"],
    )
    trans_snap = TransformationSnapshot(experiment_id=experiment.id, config_json={})
    db_session.add_all([fs_snap, trans_snap])
    db_session.flush()
    experiment.feature_selection_snapshot_id = fs_snap.id
    experiment.transformation_snapshot_id = trans_snap.id

    # 5. Model binary on disk
    model_obj = LinearRegression()
    artifact_path = tmp_path / "healthy_model.joblib"
    joblib.dump(model_obj, artifact_path)
    checksum = hashlib.sha256(artifact_path.read_bytes()).hexdigest()

    trained_model = TrainedModel(
        id=uuid4(),
        experiment_id=experiment.id,
        algorithm_name="LinearRegression",
        hyperparameters={"fit_intercept": True},
        status=ModelState.DEPLOYABLE.value,
        artifact_path=str(artifact_path),
        artifact_checksum=checksum,
        quick_cv_score=10.5,
        model_selection_score=10.6,
        fit_diagnosis="GOOD_FIT",
        preprocessing_snapshot_id=trans_snap.id,
        feature_selection_snapshot_id=fs_snap.id,
        created_by=trainer.id,
    )
    db_session.add(trained_model)
    db_session.flush()

    experiment.selected_model_id = trained_model.id

    # Metrics
    metric_dev = ModelMetric(
        id=uuid4(),
        model_id=trained_model.id,
        split="CV_MEAN",
        metric_name="RMSE",
        metric_value=10.5,
    )
    metric_test = ModelMetric(
        id=uuid4(),
        model_id=trained_model.id,
        split="LOCKED_TEST",
        metric_name="RMSE",
        metric_value=10.6,
    )
    db_session.add_all([metric_dev, metric_test])

    # 6. Deployment Gate (Passed)
    gate = DeploymentGate(
        id=uuid4(),
        model_id=trained_model.id,
        gate_passed=True,
        evaluated_at=datetime.now(timezone.utc),
        approved_by=approver.id,
        locked_test_evaluated=True,
        schema_locked=True,
        artifact_verified=True,
        lineage_complete=True,
        performance_threshold_passed="PASS",
        user_approved=True,
    )
    db_session.add(gate)
    db_session.commit()

    return experiment


def test_experiment_health_report_healthy(client: TestClient, healthy_experiment_setup: Experiment, auth_headers: dict):
    """
    Verifies that a fully validated healthy experiment reports 0 risks flagged
    and returns all 6 immutable structural guarantees.
    """
    exp_id = healthy_experiment_setup.id
    resp = client.get(f"/api/v1/experiments/{exp_id}/health", headers=auth_headers)
    assert resp.status_code == status.HTTP_200_OK

    data = resp.json()
    assert data["experiment_id"] == str(exp_id)
    assert data["overall_health"] == "HEALTHY"
    assert data["risks_flagged_count"] == 0
    assert "0 risks flagged" in data["risks_summary"]

    # Verify 6 structural guarantees
    guarantees = data["structural_guarantees"]
    assert len(guarantees) == 6
    guarantee_ids = [g["id"] for g in guarantees]
    assert "GUARANTEE_1_OUTER_SPLIT" in guarantee_ids
    assert "GUARANTEE_2_PREPROCESSING_LEAKAGE" in guarantee_ids
    assert "GUARANTEE_3_FEATURE_SELECTION" in guarantee_ids
    assert "GUARANTEE_4_LOCKED_TEST" in guarantee_ids
    assert "GUARANTEE_5_LINEAGE_REPRODUCIBILITY" in guarantee_ids
    assert "GUARANTEE_6_FOUR_EYES_GATE" in guarantee_ids
    assert all(g["is_guaranteed"] is True for g in guarantees)

    # Verify signals
    signals = data["signals"]
    assert signals["fit_diagnosis"] == "GOOD_FIT"
    assert signals["evidence_strength"] == "STRONG"
    assert signals["artifact_checksum_status"] == "VERIFIED"
    assert signals["locked_test_status"] == "CONSUMED"
    assert signals["gate_status"] == "PASSED"
    assert signals["gate_conditions_passed"] == 6


def test_experiment_health_report_flagged_risks(client: TestClient, db_session: Session, tmp_path: Path, auth_headers: dict):
    """
    Verifies risk detection on an impaired experiment:
    - Overfitting model (POTENTIAL_OVERFIT)
    - Unconsumed locked test split
    - Weak feature evidence (INSUFFICIENT_EVIDENCE)
    """
    trainer = db_session.query(User).filter(User.email == "trainer@demo.com").first()

    project = Project(
        id=uuid4(),
        owner_id=trainer.id,
        project_name="Impaired Experiment Demo",
        task_type="REGRESSION",
        target_column="target",
    )
    db_session.add(project)
    db_session.flush()

    experiment = Experiment(
        id=uuid4(),
        project_id=project.id,
        status=ExperimentState.EVALUATED.value,
        task_type="REGRESSION",
        selection_metric="RMSE",
        selection_direction="MINIMIZE",
        locked_test_consumed=False,  # Risk 1: Unconsumed locked test
        experiment_config={"feature_selection": {"evidence_strength": "INSUFFICIENT_EVIDENCE"}},
        code_version="git:v1.0.0",
        python_version="3.13.0",
        sklearn_version="1.5.0",
        numpy_version="2.0.0",
        pandas_version="2.2.0",
        environment_capture_method="CAPTURED_LIVE",
    )
    db_session.add(experiment)
    db_session.flush()

    # Snapshot with insufficient evidence
    fs_snap = FeatureSelectionSnapshot(
        experiment_id=experiment.id,
        final_selected_features=["f1"],
    )
    db_session.add(fs_snap)
    db_session.flush()
    experiment.feature_selection_snapshot_id = fs_snap.id

    # Model with potential overfit
    artifact_path = tmp_path / "overfit_model.joblib"
    joblib.dump(LinearRegression(), artifact_path)
    checksum = hashlib.sha256(artifact_path.read_bytes()).hexdigest()

    trained_model = TrainedModel(
        id=uuid4(),
        experiment_id=experiment.id,
        algorithm_name="RandomForestRegressor",
        status=ModelState.TRAINED.value,
        artifact_path=str(artifact_path),
        artifact_checksum=checksum,
        quick_cv_score=5.0,
        model_selection_score=25.0,
        fit_diagnosis="POTENTIAL_OVERFIT",  # Risk 3: Overfitting
        created_by=trainer.id,
    )
    db_session.add(trained_model)
    db_session.flush()
    experiment.selected_model_id = trained_model.id
    db_session.commit()

    resp = client.get(f"/api/v1/experiments/{experiment.id}/health", headers=auth_headers)
    assert resp.status_code == status.HTTP_200_OK

    data = resp.json()
    assert data["risks_flagged_count"] >= 3
    assert data["overall_health"] == "WARNING"

    risk_types = [r["risk_type"] for r in data["risks"]]
    assert "OVERFITTING_RISK" in risk_types
    assert "LOCKED_TEST_UNCONSUMED" in risk_types
    assert "WEAK_FEATURE_EVIDENCE" in risk_types

    # Verify each risk contains finding, description, severity, and remediation
    for risk in data["risks"]:
        assert len(risk["finding"]) > 0
        assert len(risk["description"]) > 0
        assert len(risk["remediation"]) > 0
        assert risk["severity"] in ["LOW", "MEDIUM", "HIGH", "CRITICAL"]


def test_experiment_health_report_artifact_tamper_critical(client: TestClient, db_session: Session, tmp_path: Path, auth_headers: dict):
    """
    Verifies that modifying the disk artifact file after training triggers a CRITICAL checksum mismatch risk.
    """
    trainer = db_session.query(User).filter(User.email == "trainer@demo.com").first()

    project = Project(
        id=uuid4(),
        owner_id=trainer.id,
        project_name="Tamper Experiment Demo",
        task_type="REGRESSION",
        target_column="target",
    )
    db_session.add(project)
    db_session.flush()

    experiment = Experiment(
        id=uuid4(),
        project_id=project.id,
        status=ExperimentState.REGISTERED.value,
        task_type="REGRESSION",
        selection_metric="RMSE",
        selection_direction="MINIMIZE",
        locked_test_consumed=True,
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

    # Create model artifact on disk with recorded checksum
    artifact_path = tmp_path / "tampered_model.joblib"
    joblib.dump(LinearRegression(), artifact_path)
    recorded_checksum = hashlib.sha256(artifact_path.read_bytes()).hexdigest()

    trained_model = TrainedModel(
        id=uuid4(),
        experiment_id=experiment.id,
        algorithm_name="LinearRegression",
        status=ModelState.DEPLOYABLE.value,
        artifact_path=str(artifact_path),
        artifact_checksum=recorded_checksum,
        fit_diagnosis="GOOD_FIT",
        created_by=trainer.id,
    )
    db_session.add(trained_model)
    db_session.flush()
    experiment.selected_model_id = trained_model.id
    db_session.commit()

    # Tamper with disk binary
    artifact_path.write_bytes(b"TAMPERED_MALICIOUS_BYTES_999")

    resp = client.get(f"/api/v1/experiments/{experiment.id}/health", headers=auth_headers)
    assert resp.status_code == status.HTTP_200_OK

    data = resp.json()
    assert data["overall_health"] == "CRITICAL"
    assert data["signals"]["artifact_checksum_status"] == "MISMATCH"

    tamper_risk = next(r for r in data["risks"] if r["risk_type"] == "ARTIFACT_TAMPER_RISK")
    assert tamper_risk["severity"] == "CRITICAL"
    assert "SHA-256 on disk does not match" in tamper_risk["finding"]
