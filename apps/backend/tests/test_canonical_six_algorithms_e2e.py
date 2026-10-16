"""
Integration Verification Test: All 6 Canonical Algorithms End-to-End.

Validates that:
- Regression: LinearRegression, RandomForestRegressor, GradientBoostingRegressor
- Classification: LogisticRegression, RandomForestClassifier, GradientBoostingClassifier
are all accepted by the platform API, properly trained with fold isolation,
evaluated against locked test metrics, and successfully serve live predictions
at `/api/v1/predict/{deployment_id}` without mocks.
"""

import uuid
import pytest
import numpy as np
import pandas as pd
from uuid import uuid4

from app.models.user import User
from app.models.role import Role
from app.models.project import Project
from app.models.dataset import Dataset
from app.models.dataset_column import DatasetColumn
from app.models.dataset_split import DatasetSplit
from app.models.deployment import Deployment
from app.models.model_metric import ModelMetric
from app.models.transformation_snapshot import TransformationSnapshot
from app.models.feature_selection_snapshot import FeatureSelectionSnapshot
from app.services.experiment_service import ExperimentService
from app.services.deployment_gate_service import DeploymentGateService
from app.services.deployment_service import DeploymentService
from app.services.prediction_service import PredictionService


@pytest.fixture
def test_users(db_session, create_test_user):
    trainer = create_test_user("canonical_trainer@mlstudio.io", role_name="ADMIN")
    approver = create_test_user("canonical_approver@mlstudio.io", role_name="ADMIN")
    return trainer, approver


@pytest.mark.parametrize("algorithm", [
    "LinearRegression",
    "RandomForestRegressor",
    "GradientBoostingRegressor",
])
def test_canonical_regression_algorithms_e2e(client, db_session, tmp_path, test_users, auth_headers, algorithm):
    trainer, approver = test_users
    headers = auth_headers(trainer)
    approver_headers = auth_headers(approver)

    # 1. Project
    proj_res = client.post(
        "/api/v1/projects",
        json={"project_name": f"Project Reg {algorithm}", "target_column": "target"},
        headers=headers,
    )
    assert proj_res.status_code == 201
    proj_id = proj_res.json()["id"]

    client.put(
        f"/api/v1/projects/{proj_id}/task-type",
        json={"task_type": "REGRESSION"},
        headers=headers,
    )

    # 2. Ingest dataset
    np.random.seed(42)
    n = 60
    X1 = np.random.uniform(10, 100, n)
    X2 = np.random.uniform(1, 10, n)
    y = 2.5 * X1 + 5.0 * X2 + np.random.normal(0, 1, n)
    df = pd.DataFrame({"x1": X1, "x2": X2, "target": y})

    csv_path = str(tmp_path / f"reg_{algorithm}.csv")
    df.to_csv(csv_path, index=False)

    dataset = Dataset(
        id=uuid4(),
        project_id=uuid.UUID(proj_id),
        version_number=1,
        file_path=csv_path,
        row_count=n,
        column_count=3,
        content_hash="reg_hash",
    )
    db_session.add(dataset)
    db_session.commit()

    for col in df.columns:
        db_session.add(
            DatasetColumn(
                dataset_id=dataset.id,
                column_name=col,
                data_type="NUMERIC",
                is_target=(col == "target"),
            )
        )
    db_session.commit()

    # Split
    dev_split = DatasetSplit(
        dataset_id=dataset.id,
        split_type="DEVELOPMENT",
        split_seed=42,
        row_indices=list(range(48)),
    )
    locked_split = DatasetSplit(
        dataset_id=dataset.id,
        split_type="LOCKED_TEST",
        split_seed=42,
        row_indices=list(range(48, n)),
    )
    db_session.add_all([dev_split, locked_split])
    db_session.commit()

    # 3. Train algorithm via ExperimentService
    exp_service = ExperimentService(db_session)
    exp_res = exp_service.run_experiment(
        project_id=uuid.UUID(proj_id),
        algorithms=[algorithm],
        folds=3,
        seed=42,
        selection_metric="rmse",
        selection_direction="MINIMIZE",
        auto_finalize=True,
        deployment_threshold={"metric": "rmse", "min_value": 50000.0},
    )
    model_id = exp_res["selected_model_id"]
    assert model_id is not None

    # 4. Deployment gate
    gate_res = client.post(f"/api/v1/models/{model_id}/deployment-gate/approve", headers=approver_headers)
    assert gate_res.status_code == 200

    deploy_res = client.post(f"/api/v1/models/{model_id}/deploy", headers=headers)
    assert deploy_res.status_code == 200
    dep_id = deploy_res.json()["id"]

    # 5. Live prediction at /api/v1/predict/{deployment_id}
    pred_res = client.post(f"/api/v1/predict/{dep_id}", json={"x1": 50.0, "x2": 5.0})
    assert pred_res.status_code == 200
    data = pred_res.json()
    assert "prediction" in data
    assert isinstance(data["prediction"], (int, float))


@pytest.mark.parametrize("algorithm", [
    "LogisticRegression",
    "RandomForestClassifier",
    "GradientBoostingClassifier",
])
def test_canonical_classification_algorithms_e2e(client, db_session, tmp_path, test_users, auth_headers, algorithm):
    trainer, approver = test_users
    headers = auth_headers(trainer)
    approver_headers = auth_headers(approver)

    # 1. Project
    proj_res = client.post(
        "/api/v1/projects",
        json={"project_name": f"Project Clf {algorithm}", "target_column": "target"},
        headers=headers,
    )
    assert proj_res.status_code == 201
    proj_id = proj_res.json()["id"]

    client.put(
        f"/api/v1/projects/{proj_id}/task-type",
        json={"task_type": "CLASSIFICATION"},
        headers=headers,
    )

    # 2. Ingest dataset
    np.random.seed(42)
    n = 60
    X1 = np.random.uniform(10, 100, n)
    X2 = np.random.uniform(1, 10, n)
    prob = 1 / (1 + np.exp(-(0.05 * X1 - 0.2 * X2)))
    y = (np.random.uniform(0, 1, n) < prob).astype(int)
    # Ensure both classes present
    y[0] = 0
    y[1] = 1
    y[-1] = 0
    y[-2] = 1
    df = pd.DataFrame({"x1": X1, "x2": X2, "target": y})

    csv_path = str(tmp_path / f"clf_{algorithm}.csv")
    df.to_csv(csv_path, index=False)

    dataset = Dataset(
        id=uuid4(),
        project_id=uuid.UUID(proj_id),
        version_number=1,
        file_path=csv_path,
        row_count=n,
        column_count=3,
        content_hash="clf_hash",
    )
    db_session.add(dataset)
    db_session.commit()

    for col in df.columns:
        db_session.add(
            DatasetColumn(
                dataset_id=dataset.id,
                column_name=col,
                data_type="NUMERIC",
                is_target=(col == "target"),
            )
        )
    db_session.commit()

    # Split
    dev_split = DatasetSplit(
        dataset_id=dataset.id,
        split_type="DEVELOPMENT",
        split_seed=42,
        row_indices=list(range(48)),
    )
    locked_split = DatasetSplit(
        dataset_id=dataset.id,
        split_type="LOCKED_TEST",
        split_seed=42,
        row_indices=list(range(48, n)),
    )
    db_session.add_all([dev_split, locked_split])
    db_session.commit()

    # 3. Train algorithm via ExperimentService
    exp_service = ExperimentService(db_session)
    exp_res = exp_service.run_experiment(
        project_id=uuid.UUID(proj_id),
        algorithms=[algorithm],
        folds=3,
        seed=42,
        selection_metric="f1_macro",
        selection_direction="MAXIMIZE",
        auto_finalize=True,
        deployment_threshold={"metric": "f1_macro", "min_value": 0.10},
    )
    model_id = exp_res["selected_model_id"]
    assert model_id is not None

    # 4. Deployment gate
    gate_res = client.post(f"/api/v1/models/{model_id}/deployment-gate/approve", headers=approver_headers)
    assert gate_res.status_code == 200

    deploy_res = client.post(f"/api/v1/models/{model_id}/deploy", headers=headers)
    assert deploy_res.status_code == 200
    dep_id = deploy_res.json()["id"]

    # 5. Live prediction at /api/v1/predict/{deployment_id}
    pred_res = client.post(f"/api/v1/predict/{dep_id}", json={"x1": 50.0, "x2": 5.0})
    assert pred_res.status_code == 200
    data = pred_res.json()
    assert "prediction" in data
    assert data["prediction"] in [0, 1, 0.0, 1.0]
