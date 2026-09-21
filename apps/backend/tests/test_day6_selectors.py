"""
Day 6 — Comprehensive Unit & Integration Tests:
Platform Scope Boundary (Closing Stability Circular Dependency per SRS v9 §1).

Asserts explicit rejection of RANK_AGGREGATION_STABILITY through the platform's
Feature Engineering endpoint, returning HTTP 400 with:
"research-only method, not available in platform experiments."
Ensures RANK_AGGREGATION is the only supported platform selection method and
stability scoring is not referenced/used in platform code.
"""

import io
import uuid
import pytest
import numpy as np
import pandas as pd
from fastapi import HTTPException, status

from app.models.dataset import Dataset
from app.models.dataset_split import DatasetSplit
from app.models.project import Project
from app.models.user import User
from app.models.role import Role
from app.services.dataset_service import DatasetService
from app.services.dataset_split_service import DatasetSplitService
from app.services.feature_selection_service import FeatureSelectionService


def get_auth_token(client, email="day6_engineer@example.com"):
    reg_resp = client.post(
        "/api/v1/auth/signup",
        json={
            "full_name": "Day 6 User",
            "email": email,
            "password": "password123",
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


def create_mock_project_and_data(client):
    token = get_auth_token(client, email=f"user_{uuid.uuid4().hex[:8]}@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Create project
    proj_resp = client.post(
        "/api/v1/projects",
        headers=headers,
        json={"project_name": f"Day 6 Project {uuid.uuid4().hex[:6]}"},
    )
    assert proj_resp.status_code == 201
    project_id = proj_resp.json()["id"]

    # 2. Upload dataset
    np.random.seed(42)
    n = 60
    x1 = np.random.normal(0, 1, n)
    x2 = np.random.normal(0, 1, n)
    y = (x1 + x2 > 0).astype(int)
    df = pd.DataFrame({"feat_a": x1, "feat_b": x2, "target": y})
    csv_bytes = df.to_csv(index=False).encode("utf-8")

    upload_resp = client.post(
        f"/api/v1/projects/{project_id}/datasets",
        files={"file": ("data.csv", io.BytesIO(csv_bytes), "text/csv")},
        headers=headers,
    )
    assert upload_resp.status_code == 201
    dataset_id = upload_resp.json()["id"]

    # 3. Outer Split
    split_resp = client.post(
        f"/api/v1/datasets/{dataset_id}/split",
        headers=headers,
        json={"test_percentage": 20.0, "seed": 42},
    )
    assert split_resp.status_code == 201

    # 4. Target column & task type
    patch_resp = client.put(
        f"/api/v1/projects/{project_id}",
        headers=headers,
        json={"task_type": "CLASSIFICATION", "target_column": "target"},
    )
    assert patch_resp.status_code == 200

    return project_id, headers


# =============================================================================
# 1. API Validation Tests: Reject RANK_AGGREGATION_STABILITY (SRS v9 §1)
# =============================================================================

def test_api_rejection_rank_aggregation_stability_exact(client):
    """
    Per SRS v9 §1: Attempting to configure RANK_AGGREGATION_STABILITY must return 400
    with 'research-only method, not available in platform experiments.'
    """
    project_id, headers = create_mock_project_and_data(client)

    resp = client.post(
        f"/api/v1/projects/{project_id}/feature-selection/run",
        json={"method": "RANK_AGGREGATION_STABILITY"},
        headers=headers,
    )
    assert resp.status_code == status.HTTP_400_BAD_REQUEST
    data = resp.json()
    assert data["detail"] == "research-only method, not available in platform experiments."


def test_api_rejection_rank_aggregation_stability_case_insensitive(client):
    """
    Case-insensitive rejection test for 'rank_aggregation_stability'.
    """
    project_id, headers = create_mock_project_and_data(client)

    resp = client.post(
        f"/api/v1/projects/{project_id}/feature-selection/run",
        json={"method": "rank_aggregation_stability"},
        headers=headers,
    )
    assert resp.status_code == status.HTTP_400_BAD_REQUEST
    assert resp.json()["detail"] == "research-only method, not available in platform experiments."


def test_api_rejection_selection_method_alias(client):
    """
    Rejection test when specified via selection_method field alias.
    """
    project_id, headers = create_mock_project_and_data(client)

    resp = client.post(
        f"/api/v1/projects/{project_id}/feature-selection/run",
        json={"selection_method": "RANK_AGGREGATION_STABILITY"},
        headers=headers,
    )
    assert resp.status_code == status.HTTP_400_BAD_REQUEST
    assert resp.json()["detail"] == "research-only method, not available in platform experiments."


def test_api_rejection_stability_keyword_variations(client):
    """
    Rejection test for any stability-bearing variation.
    """
    project_id, headers = create_mock_project_and_data(client)

    for method_name in ["RANK_AGGREGATION_PLUS_STABILITY", "stability", "STABILITY"]:
        resp = client.post(
            f"/api/v1/projects/{project_id}/feature-selection/run",
            json={"method": method_name},
            headers=headers,
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert resp.json()["detail"] == "research-only method, not available in platform experiments."


# =============================================================================
# 2. Service-Layer Direct Validation Test
# =============================================================================

def test_service_layer_rejection_rank_aggregation_stability(db_session, client):
    """
    FeatureSelectionService.run_cv_feature_selection directly raises HTTPException 400.
    """
    project_id, _ = create_mock_project_and_data(client)
    service = FeatureSelectionService(db_session)

    with pytest.raises(HTTPException) as exc_info:
        service.run_cv_feature_selection(
            project_id=project_id,
            method="RANK_AGGREGATION_STABILITY",
        )

    assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
    assert exc_info.value.detail == "research-only method, not available in platform experiments."


# =============================================================================
# 3. Platform Accepted Method Verification (RANK_AGGREGATION / Default)
# =============================================================================

def test_platform_accepted_method_rank_aggregation(client):
    """
    RANK_AGGREGATION is the only method selectable in the platform UI's dropdown.
    Explicitly passing RANK_AGGREGATION or omitting method succeeds.
    """
    project_id, headers = create_mock_project_and_data(client)

    # Explicit RANK_AGGREGATION
    resp1 = client.post(
        f"/api/v1/projects/{project_id}/feature-selection/run",
        json={"method": "RANK_AGGREGATION", "n_splits": 2},
        headers=headers,
    )
    assert resp1.status_code == status.HTTP_200_OK
    data1 = resp1.json()
    assert len(data1["features"]) == 2

    # Default (omitted method)
    resp2 = client.post(
        f"/api/v1/projects/{project_id}/feature-selection/run",
        json={"n_splits": 2},
        headers=headers,
    )
    assert resp2.status_code == status.HTTP_200_OK
    data2 = resp2.json()
    assert len(data2["features"]) == 2
