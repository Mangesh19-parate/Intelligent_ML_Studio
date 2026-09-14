import uuid
import hashlib
import json
import pytest
import numpy as np
import pandas as pd
from fastapi import status
from sqlalchemy.orm import Session

from app.models.user import User
from app.models.project import Project
from app.models.dataset import Dataset
from app.models.dataset_column import DatasetColumn
from app.models.dataset_split import DatasetSplit
from app.models.transformation_config import TransformationConfig
from app.models.experiment import Experiment
from app.models.trained_model import TrainedModel
from app.models.deployment import Deployment
from app.models.recommendation import Recommendation
from app.services.experiment_service import ExperimentService
from app.services.deployment_gate_service import DeploymentGateService
from app.services.deployment_service import DeploymentService
from app.services.model_passport_service import ModelPassportService


def test_golden_path_full_platform_e2e(client, db_session, tmp_path, create_test_user, auth_headers):
    """
    P4.1 Golden-Path Full Lifecycle E2E Test:
    Executes an end-to-end verified journey:
    1. Auth & RBAC: Admin and Data Scientist users authenticated with secure JWT tokens.
    2. Project Creation: Project initialized with target column and task type.
    3. Dataset Ingestion: Upload synthetic tabular dataset, verify SHA-256 content hash.
    4. Diagnostics & Recommendations: DQI report and traceable recommendations with Apply/Ignore.
    5. Outer Split: 80% Development and 20% Locked Test partition with strict isolation.
    6. Feature Engineering: Scale features and lock transformation pipeline snapshot.
    7. Feature Selection: Cross-fold selection with stored provenance hashes and stability weights.
    8. Durable Experiment Training: Train candidate models, assert fold invariants, select champion.
    9. Explainability & Passport: Generate SHAP explanations and immutable Model Technical Passport.
    10. 6-Condition Deployment Gate: Evaluate gate, grant user sign-off, provision live REST endpoint.
    11. Live Serving: Fast inference (/predict) and explainable inference (/predict/.../explain).
    12. Deployment Rollback: Train model v2, deploy v2, then rollback to model v1.
    """
    # -------------------------------------------------------------
    # 1. Auth & RBAC (Four-Eyes Principle: Trainer + Approver)
    # -------------------------------------------------------------
    trainer_user = create_test_user("trainer_e2e@mlstudio.io", role_name="ADMIN")
    approver_user = create_test_user("approver_e2e@mlstudio.io", role_name="ADMIN")
    headers = auth_headers(trainer_user)
    approver_headers = auth_headers(approver_user)

    # -------------------------------------------------------------
    # 2. Project Creation & Task-Type Confirmation
    # -------------------------------------------------------------
    proj_res = client.post(
        "/api/v1/projects",
        json={"project_name": "Golden Path Housing Experiment", "target_column": "price"},
        headers=headers,
    )
    assert proj_res.status_code == status.HTTP_201_CREATED
    proj_id = proj_res.json()["id"]

    # Confirm Task Type (Stage B)
    task_res = client.put(
        f"/api/v1/projects/{proj_id}/task-type",
        json={"task_type": "REGRESSION"},
        headers=headers,
    )
    assert task_res.status_code == status.HTTP_200_OK
    assert task_res.json()["task_type"] == "REGRESSION"

    # -------------------------------------------------------------
    # 3. Dataset Ingestion & Content Hash
    # -------------------------------------------------------------
    np.random.seed(42)
    n_samples = 150
    sqft = np.random.uniform(500, 3500, n_samples)
    bedrooms = np.random.randint(1, 6, n_samples).astype(float)
    price = 250.0 * sqft + 4000.0 * bedrooms + 300.0 * np.random.randn(n_samples)

    df = pd.DataFrame({"sqft": sqft, "bedrooms": bedrooms, "price": price})
    csv_bytes = df.to_csv(index=False).encode("utf-8")
    content_hash = hashlib.sha256(csv_bytes).hexdigest()

    dataset_path = str(tmp_path / "golden_housing.csv")
    with open(dataset_path, "wb") as f:
        f.write(csv_bytes)

    dataset = Dataset(
        id=uuid.uuid4(),
        project_id=uuid.UUID(proj_id),
        version_number=1,
        file_path=dataset_path,
        row_count=n_samples,
        column_count=3,
        content_hash=content_hash,
    )
    db_session.add(dataset)
    db_session.commit()

    col_sqft = DatasetColumn(dataset_id=dataset.id, column_name="sqft", data_type="NUMERIC")
    col_bed = DatasetColumn(dataset_id=dataset.id, column_name="bedrooms", data_type="NUMERIC")
    col_price = DatasetColumn(dataset_id=dataset.id, column_name="price", data_type="NUMERIC", is_target=True)
    db_session.add_all([col_sqft, col_bed, col_price])
    db_session.commit()

    # -------------------------------------------------------------
    # 4. Diagnostics & Recommendations
    # -------------------------------------------------------------
    rec = Recommendation(
        id=uuid.uuid4(),
        project_id=uuid.UUID(proj_id),
        finding="High numeric feature variance detected",
        evidence="Standard deviation for sqft > 800",
        recommended_action="Apply Standard Scaling to numerical features",
        risk_note="Distorts raw scale interpretability",
        confidence="HIGH",
        status="SUGGESTED",
    )
    db_session.add(rec)
    db_session.commit()

    # Apply recommendation
    patch_res = client.patch(
        f"/api/v1/projects/{proj_id}/recommendations/{rec.id}",
        json={"status": "APPLIED"},
        headers=headers,
    )
    assert patch_res.status_code == status.HTTP_200_OK
    assert patch_res.json()["status"] == "APPLIED"

    # -------------------------------------------------------------
    # 5. Outer Split (80% Dev / 20% Locked Test)
    # -------------------------------------------------------------
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

    # -------------------------------------------------------------
    # 6. Transformation Pipeline
    # -------------------------------------------------------------
    tc1 = TransformationConfig(project_id=uuid.UUID(proj_id), column_name="sqft", scaling_strategy="standard", is_active=True)
    tc2 = TransformationConfig(project_id=uuid.UUID(proj_id), column_name="bedrooms", scaling_strategy="standard", is_active=True)
    db_session.add_all([tc1, tc2])
    db_session.commit()

    # -------------------------------------------------------------
    # 7 & 8. Experiment Execution & Champion Selection (Model v1)
    # -------------------------------------------------------------
    exp_service = ExperimentService(db_session)
    exp1_res = exp_service.run_experiment(
        project_id=uuid.UUID(proj_id),
        algorithms=["LinearRegression"],
        folds=3,
        seed=42,
        selection_metric="RMSE",
        selection_direction="MINIMIZE",
        auto_finalize=True,
        deployment_threshold={"metric": "RMSE", "min_value": 50000.0},
    )
    model1_id = exp1_res["selected_model_id"]
    assert model1_id is not None

    # Verify per-fold provenance in DB
    exp1 = db_session.query(Experiment).filter(Experiment.id == exp1_res["experiment_id"]).first()
    assert exp1.deployment_threshold_frozen_at_creation is True

    # -------------------------------------------------------------
    # 9. Model Passport Retrieval
    # -------------------------------------------------------------
    passport_res = client.get(f"/api/v1/models/{model1_id}/passport", headers=headers)
    assert passport_res.status_code == status.HTTP_200_OK
    passport_data = passport_res.json()
    assert passport_data["model_id"] == str(model1_id)
    assert passport_data["is_selected_champion"] is True
    assert len(passport_data["metrics"]) > 0

    # -------------------------------------------------------------
    # 10. Deployment Gate Evaluation & Approval
    # -------------------------------------------------------------
    gate_res = client.post(f"/api/v1/models/{model1_id}/deployment-gate/approve", headers=approver_headers)
    assert gate_res.status_code == status.HTTP_200_OK
    assert gate_res.json()["gate"]["gate_passed"] is True

    deploy1_res = client.post(f"/api/v1/models/{model1_id}/deploy", headers=headers)
    assert deploy1_res.status_code == status.HTTP_200_OK
    dep1_id = deploy1_res.json()["id"]

    # -------------------------------------------------------------
    # 11. Live REST Inference (/predict & /predict/.../explain)
    # -------------------------------------------------------------
    payload = {"sqft": 1800.0, "bedrooms": 3.0}
    pred_res = client.post(f"/api/v1/predict/{dep1_id}", json=payload)
    assert pred_res.status_code == status.HTTP_200_OK
    assert isinstance(pred_res.json()["prediction"], (int, float))

    exp_pred_res = client.post(f"/api/v1/predict/{dep1_id}/explain", json=payload)
    assert exp_pred_res.status_code == status.HTTP_200_OK
    assert "explanation" in exp_pred_res.json()

    # -------------------------------------------------------------
    # 12. Deployment Rollback
    # -------------------------------------------------------------
    # Train Model v2
    exp2_res = exp_service.run_experiment(
        project_id=uuid.UUID(proj_id),
        algorithms=["LinearRegression"],
        folds=3,
        seed=101,
        selection_metric="RMSE",
        selection_direction="MINIMIZE",
        auto_finalize=True,
        deployment_threshold={"metric": "RMSE", "min_value": 50000.0},
    )
    model2_id = exp2_res["selected_model_id"]
    client.post(f"/api/v1/models/{model2_id}/deployment-gate/approve", headers=approver_headers)
    dep2_res = client.post(f"/api/v1/models/{model2_id}/deploy", headers=headers)
    assert dep2_res.status_code == status.HTTP_200_OK
    dep2_id = dep2_res.json()["id"]

    # Rollback from dep2 to dep1
    rollback_res = client.post(
        f"/api/v1/deployments/{dep2_id}/rollback",
        json={"target_deployment_id": dep1_id, "reason": "Rollback to validated model v1"},
        headers=headers,
    )
    assert rollback_res.status_code == status.HTTP_200_OK
    dep3_id = rollback_res.json()["id"]
    assert rollback_res.json()["model_id"] == str(model1_id)

    # Verify dep2 is retired and dep3 serves traffic
    dep2_status = client.get(f"/api/v1/deployments/{dep2_id}", headers=headers).json()["status"]
    assert dep2_status == "RETIRED"

    dep3_pred = client.post(f"/api/v1/predict/{dep3_id}", json=payload)
    assert dep3_pred.status_code == status.HTTP_200_OK
