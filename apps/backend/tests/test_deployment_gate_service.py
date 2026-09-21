"""
Unit and integration tests for DeploymentGateService (SRS v9 §2 / Day 1).

CRITICAL ARCHITECTURAL BOUNDARY:
This test suite verifies the six substantive business eligibility conditions:
1. locked_test_evaluated (strictly accepts split='LOCKED_TEST', never TEST_REUSED_DIAGNOSTIC)
2. schema_locked (resolves valid non-empty feature schema)
3. artifact_verified (active disk checksum matches trained_models.artifact_checksum)
4. lineage_complete (config, transformation snapshot, feature selection snapshot, and environment capture metadata)
5. performance_threshold_passed (tri-state PASS/FAIL/UNVERIFIABLE against frozen deployment threshold)
6. user_approved & Four-Eyes Principle (approved_by != trained_models.created_by enforced server-side)

Tests self-approval rejection using seeded demo accounts:
- trainer@demo.com (model creator)
- approver@demo.com (independent approver with DEPLOY permission)
"""

import hashlib
from pathlib import Path
import pytest
from fastapi import HTTPException, status
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.seeder import seed_rbac_data
from app.core.security import create_access_token
from app.models.user import User
from app.models.project import Project
from app.models.dataset import Dataset
from app.models.dataset_column import DatasetColumn
from app.models.experiment import Experiment
from app.models.trained_model import TrainedModel
from app.models.model_metric import ModelMetric
from app.models.transformation_snapshot import TransformationSnapshot
from app.models.feature_selection_snapshot import FeatureSelectionSnapshot
from app.services.deployment_gate_service import DeploymentGateService
from app.config.state_machines import ModelState, ExperimentState


@pytest.fixture(autouse=True)
def ensure_seed_rbac(db_session: Session):
    seed_rbac_data(db_session)


@pytest.fixture
def gate_test_environment(db_session: Session, tmp_path: Path):
    """
    Sets up a fully lineage-complete and artifact-verified trained model
    created by trainer@demo.com with frozen deployment threshold.
    """
    trainer = db_session.query(User).filter(User.email == "trainer@demo.com").first()
    approver = db_session.query(User).filter(User.email == "approver@demo.com").first()
    assert trainer is not None
    assert approver is not None

    # 1. Project owned by trainer
    project = Project(
        owner_id=trainer.id,
        project_name="Deployment Gate Verification Project",
        task_type="REGRESSION",
        target_column="target",
    )
    db_session.add(project)
    db_session.flush()

    # 2. Dataset and Columns (for schema_locked)
    dataset = Dataset(
        project_id=project.id,
        version_number=1,
        row_count=100,
        column_count=2,
        file_path=str(tmp_path / "data.csv"),
    )
    db_session.add(dataset)
    db_session.flush()

    col_feat = DatasetColumn(
        dataset_id=dataset.id,
        column_name="feature_1",
        data_type="NUMERIC",
        is_target=False,
    )
    col_tgt = DatasetColumn(
        dataset_id=dataset.id,
        column_name="target",
        data_type="NUMERIC",
        is_target=True,
    )
    db_session.add_all([col_feat, col_tgt])
    db_session.flush()

    # 3. Experiment with frozen threshold
    experiment = Experiment(
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
        config_json={"pipeline": [{"step": "impute"}]},
    )
    fs_snap = FeatureSelectionSnapshot(
        experiment_id=experiment.id,
        final_selected_features=["feature_1"],
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

    # 5. Artifact file and checksum
    artifact_file = tmp_path / "model_artifact.pkl"
    artifact_content = b"sample-valid-serialized-model-artifact"
    artifact_file.write_bytes(artifact_content)
    artifact_checksum = hashlib.sha256(artifact_content).hexdigest()

    # 6. Trained model created by trainer
    trained_model = TrainedModel(
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

    # 7. ModelMetric: split='LOCKED_TEST' with passing RMSE
    metric = ModelMetric(
        model_id=trained_model.id,
        split="LOCKED_TEST",
        metric_name="RMSE",
        metric_value=25.0,  # 25.0 <= 50.0 -> PASS
    )
    db_session.add(metric)
    db_session.commit()

    return {
        "trainer": trainer,
        "approver": approver,
        "project": project,
        "experiment": experiment,
        "model": trained_model,
        "metric": metric,
        "artifact_file": artifact_file,
    }


def test_condition_1_locked_test_evaluated_strictness(gate_test_environment, db_session: Session):
    """
    SRS v9 §2.13:
    locked_test_evaluated ONLY accepts split='LOCKED_TEST', never TEST_REUSED_DIAGNOSTIC.
    """
    model = gate_test_environment["model"]
    metric = gate_test_environment["metric"]
    service = DeploymentGateService(db_session)

    # 1. Baseline: split == 'LOCKED_TEST' -> locked_test_evaluated is True
    gate = service.check_gate(model.id)
    assert gate.locked_test_evaluated is True

    # 2. Change split to 'TEST_REUSED_DIAGNOSTIC' -> must be ignored / evaluated as False
    metric.split = "TEST_REUSED_DIAGNOSTIC"
    db_session.add(metric)
    db_session.commit()

    gate_reused = service.check_gate(model.id)
    assert gate_reused.locked_test_evaluated is False
    assert gate_reused.gate_passed is False

    # 3. Delete all metric rows -> evaluated as False
    db_session.delete(metric)
    db_session.commit()

    gate_empty = service.check_gate(model.id)
    assert gate_empty.locked_test_evaluated is False


def test_condition_2_schema_locked(gate_test_environment, db_session: Session):
    """
    schema_locked verifies that the expected input feature schema is resolved and non-empty.
    """
    model = gate_test_environment["model"]
    service = DeploymentGateService(db_session)

    # Baseline: non-empty schema -> True
    gate = service.check_gate(model.id)
    assert gate.schema_locked is True

    # If feature selection snapshot has no features -> schema is empty -> False
    fs_snaps = db_session.query(FeatureSelectionSnapshot).all()
    for fs in fs_snaps:
        fs.final_selected_features = []
        db_session.add(fs)
    db_session.commit()

    gate_noschema = service.check_gate(model.id)
    assert gate_noschema.schema_locked is False
    assert gate_noschema.gate_passed is False


def test_condition_3_artifact_verified_disk_checksum(gate_test_environment, db_session: Session):
    """
    artifact_verified verifies that artifact exists on disk and active SHA-256 matches model checksum.
    """
    model = gate_test_environment["model"]
    artifact_file = gate_test_environment["artifact_file"]
    service = DeploymentGateService(db_session)

    # Baseline: matches disk checksum -> True
    gate = service.check_gate(model.id)
    assert gate.artifact_verified is True

    # Tamper with artifact file on disk -> checksum mismatch -> False
    artifact_file.write_bytes(b"tampered-corrupted-artifact-data")
    gate_tampered = service.check_gate(model.id)
    assert gate_tampered.artifact_verified is False
    assert gate_tampered.gate_passed is False

    # Delete artifact file -> False
    artifact_file.unlink()
    gate_deleted = service.check_gate(model.id)
    assert gate_deleted.artifact_verified is False


def test_condition_4_lineage_complete(gate_test_environment, db_session: Session):
    """
    lineage_complete requires config, snapshots, and runtime environment metadata.
    """
    model = gate_test_environment["model"]
    experiment = gate_test_environment["experiment"]
    service = DeploymentGateService(db_session)

    # Baseline: complete -> True
    gate = service.check_gate(model.id)
    assert gate.lineage_complete is True

    # Missing python_version -> False
    experiment.python_version = None
    db_session.add(experiment)
    db_session.commit()

    gate_missing_env = service.check_gate(model.id)
    assert gate_missing_env.lineage_complete is False
    assert gate_missing_env.gate_passed is False


def test_condition_5_performance_threshold_tri_state(gate_test_environment, db_session: Session):
    """
    performance_threshold_passed yields tri-state: 'PASS', 'FAIL', 'UNVERIFIABLE'.
    """
    model = gate_test_environment["model"]
    experiment = gate_test_environment["experiment"]
    metric = gate_test_environment["metric"]
    service = DeploymentGateService(db_session)

    # 1. Baseline: RMSE=25.0 <= 50.0 (MINIMIZE) -> PASS
    gate_pass = service.check_gate(model.id)
    assert gate_pass.performance_threshold_passed == "PASS"

    # 2. Failing metric value: RMSE=75.0 > 50.0 -> FAIL
    metric.metric_value = 75.0
    db_session.add(metric)
    db_session.commit()

    gate_fail = service.check_gate(model.id)
    assert gate_fail.performance_threshold_passed == "FAIL"
    assert gate_fail.gate_passed is False

    # 3. Unfrozen threshold flag -> UNVERIFIABLE
    experiment.deployment_threshold_frozen_at_creation = False
    db_session.add(experiment)
    db_session.commit()

    gate_unverifiable = service.check_gate(model.id)
    assert gate_unverifiable.performance_threshold_passed == "UNVERIFIABLE"
    assert gate_unverifiable.gate_passed is False


def test_condition_6_self_approval_rejection_service_level(gate_test_environment, db_session: Session):
    """
    Enforces approved_by != trained_models.created_by server-side (Four-Eyes Principle).
    - trainer@demo.com (creator) attempting to approve their own model raises HTTP 403 Forbidden.
    - approver@demo.com (independent user) approving succeeds and passes gate.
    """
    model = gate_test_environment["model"]
    trainer = gate_test_environment["trainer"]
    approver = gate_test_environment["approver"]
    service = DeploymentGateService(db_session)

    assert model.created_by == trainer.id

    # 1. trainer@demo.com attempts self-approval -> raises HTTP 403 Forbidden
    with pytest.raises(HTTPException) as exc_info:
        service.approve(model_id=model.id, approved_by_user_id=trainer.id)
    assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
    assert "Self-approval is forbidden" in exc_info.value.detail

    # 2. trainer@demo.com direct check_gate with user_approved=True -> raises HTTP 403 Forbidden
    with pytest.raises(HTTPException) as exc_info2:
        service.check_gate(model_id=model.id, user_approved=True, approved_by_user_id=trainer.id)
    assert exc_info2.value.status_code == status.HTTP_403_FORBIDDEN
    assert "Self-approval is forbidden" in exc_info2.value.detail

    # 3. approver@demo.com approves -> succeeds, all 6 conditions satisfied -> gate_passed is True
    gate = service.approve(model_id=model.id, approved_by_user_id=approver.id)
    assert gate.user_approved is True
    assert gate.approved_by == approver.id
    assert gate.locked_test_evaluated is True
    assert gate.schema_locked is True
    assert gate.artifact_verified is True
    assert gate.lineage_complete is True
    assert gate.performance_threshold_passed == "PASS"
    assert gate.gate_passed is True


def test_self_approval_rejection_via_api_endpoints(gate_test_environment, client: TestClient, db_session: Session):
    """
    Integration test for self-approval rejection and approval via POST /api/v1/models/{id}/deployment-gate/approve.
    - trainer@demo.com gets 403 Forbidden (firstly due to lack of DEPLOY or self-approval).
    - If trainer is granted DEPLOY override, trainer STILL gets 403 Forbidden due to self-approval rejection!
    - approver@demo.com with DEPLOY permission gets 200 OK.
    """
    model = gate_test_environment["model"]
    trainer = gate_test_environment["trainer"]
    approver = gate_test_environment["approver"]

    trainer_token = create_access_token(subject=str(trainer.id))
    approver_token = create_access_token(subject=str(approver.id))

    # 1. Trainer attempts approval (without DEPLOY permission override) -> 403 Forbidden
    res_trainer_no_deploy = client.post(
        f"/api/v1/models/{model.id}/deployment-gate/approve",
        headers={"Authorization": f"Bearer {trainer_token}"},
    )
    assert res_trainer_no_deploy.status_code == status.HTTP_403_FORBIDDEN

    # 2. Grant trainer DEPLOY override to test server-side self-approval check specifically
    from app.models.user_permission_override import UserPermissionOverride
    trainer_override = UserPermissionOverride(
        user_id=trainer.id,
        permission_key="DEPLOY",
        is_granted=True,
    )
    db_session.add(trainer_override)
    db_session.commit()

    # Trainer calls approve now with DEPLOY permission -> MUST BE REJECTED with 403 Self-approval forbidden
    res_trainer_self_approve = client.post(
        f"/api/v1/models/{model.id}/deployment-gate/approve",
        headers={"Authorization": f"Bearer {trainer_token}"},
    )
    assert res_trainer_self_approve.status_code == status.HTTP_403_FORBIDDEN
    assert "Self-approval is forbidden" in res_trainer_self_approve.json()["detail"]

    # 3. Independent approver calls approve -> 200 OK
    res_approver = client.post(
        f"/api/v1/models/{model.id}/deployment-gate/approve",
        headers={"Authorization": f"Bearer {approver_token}"},
    )
    assert res_approver.status_code == status.HTTP_200_OK
    gate_data = res_approver.json()["gate"]
    assert gate_data["user_approved"] is True
    assert gate_data["approved_by"] == str(approver.id)
    assert gate_data["gate_passed"] is True
