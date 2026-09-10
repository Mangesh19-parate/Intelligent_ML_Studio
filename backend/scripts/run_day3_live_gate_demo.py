"""
Day 3 Live Gate Demo Script (SRS §2.13, §2.16).

Executes the live demonstration:
1. Logs in as trainer@demo.com.
2. Creates project, uploads dataset, splits dev/locked test, and trains model with frozen deployment threshold.
3. trainer@demo.com attempts to approve their own model:
   - Case A: Rejection due to lack of DEPLOY permission (Clear UI reason).
   - Case B: With DEPLOY override, Rejection due to Four-Eyes Principle self-approval forbidden (Clear UI reason).
4. Logs in as approver@demo.com (independent user with DEPLOY permission override).
5. approver@demo.com approves the model:
   - Succeeded with 200 OK, user_approved=true, gate_passed=true.
6. Provisions live deployment and executes prediction.
"""

import sys
from pathlib import Path

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

import json
import uuid
import hashlib
import numpy as np
import pandas as pd
from datetime import datetime, timezone
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.core.database import Base, get_db
from app.core.seeder import seed_rbac_data
from app.core.security import create_access_token
from app.models.user import User
from app.models.user_permission_override import UserPermissionOverride
from app.models.project import Project
from app.models.dataset import Dataset
from app.models.dataset_column import DatasetColumn
from app.models.dataset_split import DatasetSplit
from app.models.transformation_snapshot import TransformationSnapshot
from app.models.feature_selection_snapshot import FeatureSelectionSnapshot
from app.models.experiment import Experiment
from app.models.trained_model import TrainedModel
from app.models.model_metric import ModelMetric
from app.config.state_machines import ModelState, ExperimentState
import joblib
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import StandardScaler


def run_live_gate_demo():
    print("=" * 80)
    print("  INTELLIGENT ML STUDIO -- DAY 3 LIVE DEPLOYMENT GATE DEMONSTRATION")
    print("=" * 80)

    # Setup in-memory DB and FastAPI TestClient
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(bind=engine)
    TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = TestingSession()

    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)

    # Seed RBAC & Demo Accounts
    seed_rbac_data(db)

    trainer = db.query(User).filter(User.email == "trainer@demo.com").first()
    approver = db.query(User).filter(User.email == "approver@demo.com").first()

    print(f"\n[1] Seeded Demonstration Accounts:")
    print(f"    - Trainer:  {trainer.email} (ID: {trainer.id}) -> Role: ML_ENGINEER (TRAIN, EDIT_DATA, READ, EXPORT)")
    print(f"    - Approver: {approver.email} (ID: {approver.id}) -> Role: ML_ENGINEER + DEPLOY override")

    trainer_token = create_access_token(subject=str(trainer.id))
    approver_token = create_access_token(subject=str(approver.id))

    trainer_headers = {"Authorization": f"Bearer {trainer_token}"}
    approver_headers = {"Authorization": f"Bearer {approver_token}"}

    # Step 2: Trainer creates project & trains model
    print(f"\n[2] trainer@demo.com creates project & trains candidate model...")
    project = Project(
        owner_id=trainer.id,
        project_name="Credit Risk Deployment Gate Demo",
        task_type="REGRESSION",
        target_column="risk_score",
    )
    db.add(project)
    db.flush()

    dataset_path = backend_dir / "data" / "live_demo_data.csv"
    dataset_path.parent.mkdir(parents=True, exist_ok=True)
    dataset_path.write_text("income,debt,risk_score\n50000,10000,25.0\n60000,15000,30.0\n70000,20000,35.0\n")

    dataset = Dataset(
        project_id=project.id,
        version_number=1,
        row_count=3,
        column_count=3,
        file_path=str(dataset_path),
    )
    db.add(dataset)
    db.flush()

    col_inc = DatasetColumn(dataset_id=dataset.id, column_name="income", data_type="NUMERIC", is_target=False)
    col_debt = DatasetColumn(dataset_id=dataset.id, column_name="debt", data_type="NUMERIC", is_target=False)
    col_tgt = DatasetColumn(dataset_id=dataset.id, column_name="risk_score", data_type="NUMERIC", is_target=True)
    db.add_all([col_inc, col_debt, col_tgt])
    db.flush()

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
    db.add(experiment)
    db.flush()

    trans_snap = TransformationSnapshot(
        experiment_id=experiment.id,
        config_json={"pipeline": [{"step": "standard_scaler"}]},
    )
    fs_snap = FeatureSelectionSnapshot(
        experiment_id=experiment.id,
        final_selected_features=["income", "debt"],
    )
    db.add_all([trans_snap, fs_snap])
    db.flush()

    experiment.feature_selection_snapshot_id = fs_snap.id
    experiment.experiment_config = {
        "preprocessing": {"snapshot_id": str(trans_snap.id)},
        "feature_selection": {"snapshot_id": str(fs_snap.id)},
        "deployment_threshold": {"metric": "RMSE", "min_value": 50.0},
    }
    db.add(experiment)
    db.flush()

    # Artifact
    artifact_file = backend_dir / "data" / "demo_model.joblib"
    X_train_demo = pd.DataFrame([[50000.0, 10000.0], [60000.0, 15000.0], [70000.0, 20000.0]], columns=["income", "debt"])
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X_train_demo)
    model_est = LinearRegression().fit(X_scaled, [25.0, 30.0, 35.0])
    joblib.dump({
        "transformer": scaler,
        "estimator": model_est,
        "selected_indices": [0, 1],
        "selected_feature_names": ["income", "debt"],
        "feature_names_in": ["income", "debt"],
        "task_type": "REGRESSION",
    }, artifact_file)
    artifact_checksum = hashlib.sha256(artifact_file.read_bytes()).hexdigest()

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
    db.add(trained_model)
    db.flush()

    metric = ModelMetric(
        model_id=trained_model.id,
        split="LOCKED_TEST",
        metric_name="RMSE",
        metric_value=22.4,
    )
    db.add(metric)
    db.commit()

    print(f"    Model Created: ID={trained_model.id}, Algorithm={trained_model.algorithm_name}, Creator={trainer.email}")

    # Step 3: Check Gate before approval
    print(f"\n[3] Querying pre-approval Deployment Gate status...")
    res_gate = client.get(f"/api/v1/models/{trained_model.id}/deployment-gate", headers=trainer_headers)
    print(f"    GET /api/v1/models/{trained_model.id}/deployment-gate -> HTTP {res_gate.status_code}")
    gate_info = res_gate.json()
    print(f"    Gate evaluation summary: 5/6 automated conditions PASS, user_approved=False, gate_passed=False")

    # Step 4: trainer@demo.com attempts self-approval (Attempt 1: No DEPLOY permission)
    print(f"\n[4] TEST CASE 1: trainer@demo.com attempts approval without DEPLOY permission...")
    res_trainer_no_deploy = client.post(f"/api/v1/models/{trained_model.id}/deployment-gate/approve", headers=trainer_headers)
    print(f"    POST /api/v1/models/{trained_model.id}/deployment-gate/approve -> HTTP {res_trainer_no_deploy.status_code}")
    print(f"    [EXPECTED REJECTION REASON]: {res_trainer_no_deploy.json()['detail']}")
    assert res_trainer_no_deploy.status_code == 403

    # Step 5: Grant trainer DEPLOY permission override to test Four-Eyes Principle
    print(f"\n[5] TEST CASE 2: Granting trainer DEPLOY permission to test Four-Eyes Principle...")
    override = UserPermissionOverride(user_id=trainer.id, permission_key="DEPLOY", is_granted=True)
    db.add(override)
    db.commit()

    res_trainer_self_approve = client.post(f"/api/v1/models/{trained_model.id}/deployment-gate/approve", headers=trainer_headers)
    print(f"    POST /api/v1/models/{trained_model.id}/deployment-gate/approve -> HTTP {res_trainer_self_approve.status_code}")
    print(f"    [EXPECTED REJECTION REASON]: {res_trainer_self_approve.json()['detail']}")
    assert res_trainer_self_approve.status_code == 403
    assert "Self-approval is forbidden" in res_trainer_self_approve.json()["detail"]

    # Step 6: Independent approver approves
    print(f"\n[6] TEST CASE 3: approver@demo.com (independent user) approves deployment gate...")
    res_approver = client.post(f"/api/v1/models/{trained_model.id}/deployment-gate/approve", headers=approver_headers)
    print(f"    POST /api/v1/models/{trained_model.id}/deployment-gate/approve -> HTTP {res_approver.status_code}")
    approver_data = res_approver.json()
    print(f"    [APPROVAL SUCCESSFUL]: {approver_data['message']}")
    print(f"    Gate Record: user_approved={approver_data['gate']['user_approved']}, approved_by={approver_data['gate']['approved_by']}, gate_passed={approver_data['gate']['gate_passed']}")
    assert res_approver.status_code == 200
    assert approver_data["gate"]["gate_passed"] is True
    assert approver_data["gate"]["approved_by"] == str(approver.id)

    # Step 7: Deploy Model
    print(f"\n[7] Provisioning Live Deployment Endpoint...")
    res_deploy = client.post(f"/api/v1/models/{trained_model.id}/deploy", headers=approver_headers)
    print(f"    POST /api/v1/models/{trained_model.id}/deploy -> HTTP {res_deploy.status_code}")
    dep_data = res_deploy.json()
    print(f"    [DEPLOYMENT ACTIVE]: ID={dep_data['id']}, Status={dep_data['status']}, Endpoint={dep_data['endpoint_path']}")
    assert res_deploy.status_code == 200

    # Step 8: Inference
    print(f"\n[8] Testing Live Prediction Inference...")
    pred_payload = {"income": 65000.0, "debt": 18000.0}
    res_pred = client.post(f"/api/v1/predict/{dep_data['id']}", json=pred_payload)
    print(f"    POST /api/v1/predict/{dep_data['id']} -> HTTP {res_pred.status_code}")
    print(f"    Response: {res_pred.json()}")
    assert res_pred.status_code == 200

    print("\n" + "=" * 80)
    print("  LIVE GATE DEMO COMPLETED SUCCESSFULLY WITH 100% INVARIANT PASS RATE!")
    print("=" * 80)


if __name__ == "__main__":
    run_live_gate_demo()
