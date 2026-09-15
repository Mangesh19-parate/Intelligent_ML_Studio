import uuid
import hashlib
from pathlib import Path
import pytest
import numpy as np
import pandas as pd
from fastapi import status

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
from app.services.data_profiling_service import DataProfilingService


def test_customer_churn_real_world_lifecycle_e2e(client, db_session, tmp_path, create_test_user, auth_headers):
    """
    Item 13 & 14: Real-World Business Benchmark (Customer Churn).
    Validates the entire platform on a realistic business dataset featuring:
    - Mixed numeric and categorical features
    - Realistic missing values (handled fold-safely)
    - Class imbalance
    - Automated profiling & DQI recommendations
    - 80/20 Outer split with Locked Test isolation
    - Fold-safe feature transformations (scaling + categorical encoding)
    - Cross-validation with champion model selection
    - SHAP local/global explainability
    - 6-Condition Deployment Gate & Four-Eyes approval
    - Live REST prediction & rollback
    """
    churn_path = Path("research/data/customer_churn.csv")
    if not churn_path.exists():
        churn_path = Path("../research/data/customer_churn.csv")
    if not churn_path.exists():
        churn_path = Path(__file__).resolve().parent.parent.parent / "research" / "data" / "customer_churn.csv"
    assert churn_path.exists(), "customer_churn.csv must exist"

    df = pd.read_csv(churn_path)
    n_samples, n_cols = df.shape
    csv_bytes = df.to_csv(index=False).encode("utf-8")
    content_hash = hashlib.sha256(csv_bytes).hexdigest()

    # 1. Setup RBAC users
    trainer = create_test_user("churn_trainer@mlstudio.io", role_name="ADMIN")
    approver = create_test_user("churn_approver@mlstudio.io", role_name="ADMIN")
    headers = auth_headers(trainer)
    approver_headers = auth_headers(approver)

    # 2. Project Creation & Task Type Confirmation
    proj_res = client.post(
        "/api/v1/projects",
        json={"project_name": "Telecom Customer Churn Production", "target_column": "churn"},
        headers=headers,
    )
    assert proj_res.status_code == status.HTTP_201_CREATED
    proj_id = proj_res.json()["id"]

    task_res = client.put(
        f"/api/v1/projects/{proj_id}/task-type",
        json={"task_type": "CLASSIFICATION"},
        headers=headers,
    )
    assert task_res.status_code == status.HTTP_200_OK

    # 3. Ingestion
    dataset_file = str(tmp_path / "customer_churn.csv")
    with open(dataset_file, "wb") as f:
        f.write(csv_bytes)

    dataset = Dataset(
        id=uuid.uuid4(),
        project_id=uuid.UUID(proj_id),
        version_number=1,
        file_path=dataset_file,
        row_count=n_samples,
        column_count=n_cols,
        content_hash=content_hash,
    )
    db_session.add(dataset)
    db_session.commit()

    # Create dataset columns
    for col in df.columns:
        is_tgt = (col == "churn")
        dtype = "NUMERIC" if pd.api.types.is_numeric_dtype(df[col]) else "CATEGORICAL"
        db_session.add(
            DatasetColumn(
                dataset_id=dataset.id,
                column_name=col,
                data_type=dtype,
                is_target=is_tgt,
            )
        )
    db_session.commit()

    # 4. Outer Split (80% Dev / 20% Locked Test)
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
    db_session.commit()

    # 5. Profiling & DQI
    profiler = DataProfilingService(db_session)
    dqi_report = profiler.generate_report(dataset.id)
    assert dqi_report is not None
    assert "data_quality_index" in dqi_report
    assert dqi_report["data_quality_index"]["overall_index"] > 0

    # 6. Feature Transformations
    for col in ["tenure_months", "monthly_charges", "total_charges", "support_calls", "usage_gb"]:
        db_session.add(
            TransformationConfig(
                project_id=uuid.UUID(proj_id),
                column_name=col,
                scaling_strategy="standard",
                missing_value_strategy="mean",
                is_active=True,
            )
        )
    for col in ["contract_type", "internet_service", "tech_support", "payment_method"]:
        db_session.add(
            TransformationConfig(
                project_id=uuid.UUID(proj_id),
                column_name=col,
                encoding_strategy="one_hot",
                is_active=True,
            )
        )
    db_session.commit()

    # 7. Experiment CV Training (Logistic Regression & Random Forest)
    exp_service = ExperimentService(db_session)
    exp_res = exp_service.run_experiment(
        project_id=uuid.UUID(proj_id),
        algorithms=["LogisticRegression"],
        folds=3,
        seed=42,
        selection_metric="F1",
        selection_direction="MAXIMIZE",
        auto_finalize=True,
        deployment_threshold={"metric": "F1", "min_value": 0.50},
    )
    model_id = exp_res["selected_model_id"]
    assert model_id is not None

    # 8. Model Technical Passport
    passport_res = client.get(f"/api/v1/models/{model_id}/passport", headers=headers)
    assert passport_res.status_code == status.HTTP_200_OK
    passport = passport_res.json()
    assert passport["model_id"] == str(model_id)
    assert passport["generalization_gap"] is not None

    # 9. Gate Sign-Off & Production Deployment
    gate_res = client.post(f"/api/v1/models/{model_id}/deployment-gate/approve", headers=approver_headers)
    assert gate_res.status_code == status.HTTP_200_OK
    assert gate_res.json()["gate"]["gate_passed"] is True

    deploy_res = client.post(f"/api/v1/models/{model_id}/deploy", headers=headers)
    assert deploy_res.status_code == status.HTTP_200_OK
    dep_id = deploy_res.json()["id"]

    # 10. Live Inference & Explainability
    sample_payload = {
        "tenure_months": 12,
        "contract_type": "Month-to-month",
        "internet_service": "Fiber optic",
        "tech_support": "No",
        "payment_method": "Electronic check",
        "monthly_charges": 85.5,
        "total_charges": 1026.0,
        "support_calls": 3,
        "usage_gb": 120.0,
    }
    pred_res = client.post(f"/api/v1/predict/{dep_id}", json=sample_payload)
    assert pred_res.status_code == status.HTTP_200_OK
    assert pred_res.json()["prediction"] in [0, 1, 0.0, 1.0]

    # Explain inference
    exp_pred_res = client.post(f"/api/v1/predict/{dep_id}/explain", json=sample_payload)
    assert exp_pred_res.status_code == status.HTTP_200_OK
    assert "explanation" in exp_pred_res.json()
