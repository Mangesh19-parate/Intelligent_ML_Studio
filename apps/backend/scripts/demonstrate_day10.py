import sys
from pathlib import Path

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

import json
import uuid
import time
import numpy as np
import pandas as pd
from datetime import datetime, timezone
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base
from app.core.seeder import seed_rbac_data
from app.models.project import Project
from app.models.dataset import Dataset
from app.models.dataset_column import DatasetColumn
from app.models.dataset_split import DatasetSplit
from app.models.transformation_config import TransformationConfig
from app.models.experiment import Experiment
from app.models.trained_model import TrainedModel
from app.models.user import User
from app.models.role import Role
from app.models.deployment import Deployment
from app.models.prediction_log import PredictionLog
from app.models.deployment_gate import DeploymentGate
from app.services.experiment_service import ExperimentService
from app.services.deployment_gate_service import DeploymentGateService
from app.services.deployment_service import DeploymentService
from app.services.prediction_service import PredictionService
from app.services.model_registry_service import ModelRegistryService


def run_demonstration():
    # In-memory engine with all models created directly from metadata
    test_engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=test_engine)
    Session = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    db = Session()
    seed_rbac_data(db)

    try:
        # Create user
        admin_role = db.query(Role).filter(Role.role_name == "ADMIN").first()
        admin_user = User(
            id=uuid.uuid4(),
            full_name="Demo Admin",
            email="demo_admin@mlstudio.io",
            password_hash="demo_hash",
            role_id=admin_role.id,
            is_active=True,
        )
        db.add(admin_user)
        db.commit()

        # Create Demo Project
        project = Project(
            id=uuid.uuid4(),
            owner_id=admin_user.id,
            project_name="Day 10 Production Demonstration",
            task_type="REGRESSION",
            target_column="price",
            pipeline_stage="SPLIT",
        )
        db.add(project)
        db.commit()

        # Synthetic dataset
        np.random.seed(42)
        n = 150
        sqft = np.random.uniform(600, 3200, n)
        bedrooms = np.random.randint(1, 5, n).astype(float)
        price = 280.0 * sqft + 5500.0 * bedrooms + 200.0 * np.random.randn(n)

        df = pd.DataFrame({"sqft": sqft, "bedrooms": bedrooms, "price": price})
        csv_bytes = df.to_csv(index=False).encode("utf-8")
        data_path = str(backend_dir / "data" / "demo_housing.csv")
        Path(data_path).parent.mkdir(parents=True, exist_ok=True)
        with open(data_path, "wb") as f:
            f.write(csv_bytes)

        dataset = Dataset(
            id=uuid.uuid4(),
            project_id=project.id,
            version_number=1,
            file_path=data_path,
            row_count=n,
            column_count=3,
            content_hash="demo_hash_12345",
        )
        db.add(dataset)
        db.commit()

        db.add_all([
            DatasetColumn(dataset_id=dataset.id, column_name="sqft", data_type="NUMERIC"),
            DatasetColumn(dataset_id=dataset.id, column_name="bedrooms", data_type="NUMERIC"),
            DatasetColumn(dataset_id=dataset.id, column_name="price", data_type="NUMERIC", is_target=True),
        ])

        n_dev = int(n * 0.8)
        db.add_all([
            DatasetSplit(dataset_id=dataset.id, split_type="DEVELOPMENT", split_seed=42, row_indices=list(range(n_dev))),
            DatasetSplit(dataset_id=dataset.id, split_type="LOCKED_TEST", split_seed=42, row_indices=list(range(n_dev, n))),
        ])

        db.add_all([
            TransformationConfig(project_id=project.id, column_name="sqft", scaling_strategy="standard", is_active=True),
            TransformationConfig(project_id=project.id, column_name="bedrooms", scaling_strategy="standard", is_active=True),
        ])
        db.commit()

        exp_service = ExperimentService(db)
        gate_service = DeploymentGateService(db)
        deploy_service = DeploymentService(db)
        predict_service = PredictionService(db)
        registry_service = ModelRegistryService(db)

        print("\n" + "="*80)
        print("ML STUDIO DAY 10 DEMONSTRATION: GATED DEPLOYMENT & DECOUPLED INFERENCE")
        print("="*80)

        # 1. Run New Gated Experiment with Frozen Threshold
        print("\n[STEP 1] Running Experiment with Frozen Creation Threshold (RMSE <= 50,000)...")
        exp_res = exp_service.run_experiment(
            project_id=project.id,
            algorithms=["LinearRegression", "RandomForestRegressor"],
            folds=3,
            seed=42,
            selection_metric="RMSE",
            selection_direction="MINIMIZE",
            auto_finalize=True,
            deployment_threshold={"metric": "RMSE", "min_value": 50000.0},
        )
        model_id = exp_res["selected_model_id"]
        exp_obj = db.query(Experiment).filter(Experiment.id == exp_res["experiment_id"]).first()
        model_obj = db.query(TrainedModel).filter(TrainedModel.id == model_id).first()

        print(f"  Experiment ID:                           {exp_obj.id}")
        print(f"  Winning Model:                           {model_obj.algorithm_name} (ID: {model_obj.id})")
        print(f"  deployment_threshold_frozen_at_creation: {exp_obj.deployment_threshold_frozen_at_creation}")
        print(f"  experiment_config.deployment_threshold:  {exp_obj.experiment_config.get('deployment_threshold')}")

        # 2. Schema check
        input_schema = registry_service.get_input_schema(model_id)
        print(f"\n[STEP 2] Derived Input Feature Schema (ModelRegistryService.get_input_schema):")
        print(f"  {json.dumps(input_schema, indent=2)}")

        # 3. Gate Check before approval
        print("\n[STEP 3] Deployment Gate Evaluation (pre-approval):")
        gate_pre = gate_service.check_gate(model_id, user_approved=False)
        print(f"  1. locked_test_evaluated:         {gate_pre.locked_test_evaluated}")
        print(f"  2. schema_locked:                 {gate_pre.schema_locked}")
        print(f"  3. artifact_verified:             {gate_pre.artifact_verified}")
        print(f"  4. lineage_complete:              {gate_pre.lineage_complete}")
        print(f"  5. performance_threshold_passed:  {gate_pre.performance_threshold_passed}")
        print(f"  6. user_approved:                 {gate_pre.user_approved}")
        print(f"  -> gate_passed:                   {gate_pre.gate_passed}")

        # 4. Approve Gate
        print("\n[STEP 4] Approving Gate via DeploymentGateService.approve()...")
        gate_approved = gate_service.approve(model_id, admin_user.id)
        print(f"  -> user_approved: {gate_approved.user_approved}, gate_passed: {gate_approved.gate_passed}")

        # 5. Deploy to Production
        print("\n[STEP 5] Deploying Model via DeploymentService.deploy()...")
        deployment = deploy_service.deploy(model_id, admin_user.id)
        print(f"  Deployment ID:   {deployment.id}")
        print(f"  Endpoint Path:   {deployment.endpoint_path}")
        print(f"  Status:          {deployment.status}")

        # 6. Fast Prediction (/predict)
        sample_input = {"sqft": 1800.0, "bedrooms": 3.0}
        print(f"\n[STEP 6] Executing Fast Prediction: POST {deployment.endpoint_path}")
        print(f"  Input Payload: {sample_input}")
        pred_res, _ = predict_service.predict(deployment.id, sample_input)
        print(f"  Prediction Output:       ${pred_res.prediction:,.2f}")
        print(f"  Inference Latency:       {pred_res.latency_ms} ms  (Decoupled fast path, no SHAP overhead)")
        print(f"  Request ID:              {pred_res.request_id}")

        # 7. Predict with Explanation (/predict/.../explain)
        print(f"\n[STEP 7] Executing Explainable Prediction: POST {deployment.endpoint_path}/explain")
        explain_res = predict_service.predict_with_explanation(deployment.id, sample_input)
        print(f"  Prediction Output:       ${explain_res.prediction:,.2f}")
        print(f"  Base Prediction Latency: {explain_res.latency_ms} ms")
        print(f"  SHAP Explanation Latency:{explain_res.explanation_latency_ms} ms  (Measurably isolated timed block)")
        print(f"  Total End-to-End Latency:{explain_res.total_latency_ms} ms")
        print(f"  SHAP Base Value:         ${explain_res.explanation['base_value']:,.2f}")
        print(f"  Feature Contributions:   {json.dumps(explain_res.explanation['contributions'], indent=4)}")

        # 8. Inspect Audit Logs
        print("\n[STEP 8] Verifying Prediction Logs in Database (SRS §2.15):")
        logs = db.query(PredictionLog).filter(PredictionLog.deployment_id == deployment.id).order_by(PredictionLog.requested_at.asc()).all()
        for i, l in enumerate(logs, 1):
            print(f"  Log #{i}: Request={str(l.request_id)[:8]} | Status={l.status} | Mode={l.payload_mode} | Input={l.input_payload} | PredLatency={l.latency_ms}ms | ExplLatency={l.explanation_latency_ms}ms")

        print("\n" + "="*80)
        print("DEMONSTRATION COMPLETED SUCCESSFULLY")
        print("="*80 + "\n")

    finally:
        db.close()


if __name__ == "__main__":
    run_demonstration()
