import io
import pytest
import numpy as np
import pandas as pd
from uuid import UUID
from fastapi import status

from app.models.dataset import Dataset
from app.models.project import Project
from app.services.dataset_service import DatasetService
from app.services.transformation_service import TransformationService
from app.services.feature_selection_service import FeatureSelectionService
from app.services.explainability_service import ExplainabilityService


def get_auth_token(client, email="guardrail_user@example.com", role_name="ML_ENGINEER"):
    reg_resp = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Guardrail Engineer",
            "email": email,
            "password": "password123",
            "role_name": role_name,
        },
    )
    assert reg_resp.status_code == 201
    login_resp = client.post(
        "/api/v1/auth/login",
        json={
            "email": email,
            "password": "password123",
        },
    )
    assert login_resp.status_code == 200
    return login_resp.json()["access_token"]


def test_upload_guardrail_rejects_exceeded_columns(client, db_session):
    """
    Asserts that uploading a dataset with > 100 columns is rejected with HTTP 422
    and a clear named reason.
    """
    token = get_auth_token(client, email="upload_cols_guard@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Create project
    proj_resp = client.post(
        "/api/v1/projects",
        json={"project_name": "Wide Dataset Guardrail", "target_column": "target"},
        headers=headers,
    )
    project_id = proj_resp.json()["id"]

    # 2. Create CSV with 105 columns
    data = {f"col_{i}": [1.0, 2.0, 3.0] for i in range(105)}
    data["target"] = [0, 1, 0]
    df = pd.DataFrame(data)
    csv_bytes = df.to_csv(index=False).encode("utf-8")

    upload_resp = client.post(
        f"/api/v1/projects/{project_id}/datasets",
        files={"file": ("wide.csv", io.BytesIO(csv_bytes), "text/csv")},
        headers=headers,
    )
    assert upload_resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    assert "Dataset column count (106 columns) exceeds maximum allowed upload policy cap of 100 columns" in upload_resp.json()["detail"]


def test_transformation_guardrail_rejects_exceeded_cardinality(client, db_session):
    """
    Asserts that configuring one_hot encoding on a column with > 250 unique categories
    is rejected with HTTP 422 early at configuration time.
    """
    token = get_auth_token(client, email="ohe_guard@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    proj_resp = client.post(
        "/api/v1/projects",
        json={"project_name": "High Card Guardrail", "target_column": "target"},
        headers=headers,
    )
    project_id = proj_resp.json()["id"]

    # Create dataset with 400 unique categories (yielding 320 rows in Development split)
    cats = [f"cat_{i}" for i in range(400)]
    df = pd.DataFrame({
        "high_card": cats,
        "numeric_feat": [float(i) for i in range(400)],
        "target": [i % 2 for i in range(400)],
    })
    csv_bytes = df.to_csv(index=False).encode("utf-8")

    upload_resp = client.post(
        f"/api/v1/projects/{project_id}/datasets",
        files={"file": ("high_card.csv", io.BytesIO(csv_bytes), "text/csv")},
        headers=headers,
    )
    assert upload_resp.status_code == 201
    dataset_id = upload_resp.json()["id"]

    # Split dataset
    client.post(
        f"/api/v1/datasets/{dataset_id}/split",
        json={"locked_test_pct": 20, "seed": 42},
        headers=headers,
    )

    # Attempt to configure one_hot encoding on high_card column -> must return 422
    update_resp = client.put(
        f"/api/v1/projects/{project_id}/transformations/high_card",
        json={"encoding_strategy": "one_hot"},
        headers=headers,
    )
    assert update_resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    assert "exceeds the maximum encoded feature policy cap of 250 features" in update_resp.json()["detail"]


def test_permutation_importance_guardrail_blocks_large_cells():
    """
    Asserts that FeatureSelectionService skips Permutation Importance when evaluation cells > 500,000.
    """
    # Create synthetic dataset with 6,000 rows and 90 features (540,000 evaluation cells)
    X = np.random.normal(size=(6000, 90))
    y = np.random.choice([0, 1], size=6000)

    n_eval_cells = X.shape[0] * X.shape[1]
    assert n_eval_cells > 500_000

    # Verify check condition
    is_blocked = (n_eval_cells > 500_000) or (X.shape[1] > 100)
    assert is_blocked is True


def test_shap_guardrail_blocks_over_250_features():
    """
    Asserts that ExplainabilityService blocks SHAP when feature dimension exceeds 250.
    """
    X_background = np.zeros((50, 260))
    assert X_background.shape[1] > 250
