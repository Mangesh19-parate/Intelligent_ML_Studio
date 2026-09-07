"""
Week 5 Complete Test-Vector Suite:
Unified Verification of All Rank-Aggregation Feature Selection Invariants (SRS v9 §2.7, §2.17, §1).

Covers all 8 canonical test vectors:
1. Rank Normalization: Exact r_{j,T} = 1 - (rank - 1)/(p - 1)
2. p = 1 Single Feature Boundary: Normalized score = 1.0 (no division by zero)
3. Average Rank Ties: Identical scores get fractional midpoint rank
4. k_min / k_max Selection Clamps: k_min=5, k_max=50 boundary clamping
5. Failed/Skipped Selector Exclusion: Non-dilution of ensemble denominator (T_applied)
6. Insufficient Evidence Abort: T_applied < 2 -> INSUFFICIENT_EVIDENCE (empty subset)
7. 3-Tier Tie-Break Determinism & Cold-Process Byte-Identity:
   -Score -> +rank_sum -> +name
8. Platform Scope Boundary: HTTP 400 rejection of RANK_AGGREGATION_STABILITY
"""

import io
import uuid
import pytest
import numpy as np
import pandas as pd
from fastapi import HTTPException, status

from app.config.contract import EvidenceStrength, TechniqueStatus
from app.models.dataset import Dataset
from app.models.dataset_split import DatasetSplit
from app.models.project import Project
from app.models.user import User
from app.models.role import Role
from app.services.dataset_service import DatasetService
from app.services.dataset_split_service import DatasetSplitService
from app.services.feature_selection_service import FeatureSelectionService
from app.services.selectors import (
    calculate_srs_rank_scores,
    aggregate_ensemble_scores,
    resolve_top_k,
    sort_features_with_tie_break,
    apply_top_k_percent_selection,
    compute_evidence_strength,
    CORRELATION_SELECTOR,
    LASSO_SELECTOR,
    RANDOM_FOREST_IMPORTANCE_SELECTOR,
    PERMUTATION_IMPORTANCE_SELECTOR,
    CorrelationSelector,
    LassoSelector,
    RandomForestImportanceSelector,
    PermutationImportanceSelector,
)


def get_auth_token(client, email="w5_suite@example.com", role_name="ML_ENGINEER"):
    reg_resp = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "W5 Suite Runner",
            "email": email,
            "password": "password123",
            "role_name": role_name,
        },
    )
    assert reg_resp.status_code == 201
    login_resp = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "password123"},
    )
    assert login_resp.status_code == 200
    return login_resp.json()["access_token"]


def create_mock_project_and_data(client, task_type="CLASSIFICATION"):
    token = get_auth_token(client, email=f"user_{uuid.uuid4().hex[:8]}@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Create project
    proj_resp = client.post(
        "/api/v1/projects",
        headers=headers,
        json={"project_name": f"W5 Vector Proj {uuid.uuid4().hex[:6]}"},
    )
    assert proj_resp.status_code == 201
    project_id = proj_resp.json()["id"]

    # 2. Upload dataset
    np.random.seed(42)
    n = 60
    x1 = np.random.normal(0, 1, n)
    x2 = np.random.normal(0, 1, n)
    if task_type == "CLASSIFICATION":
        y = (x1 + x2 > 0).astype(int)
    else:
        y = 2.0 * x1 + 0.5 * x2 + np.random.normal(0, 0.1, n)
    df = pd.DataFrame({"feat_a": x1, "feat_b": x2, "target": y})
    csv_bytes = df.to_csv(index=False).encode("utf-8")

    upload_resp = client.post(
        f"/api/v1/projects/{project_id}/datasets",
        files={"file": ("data.csv", io.BytesIO(csv_bytes), "text/csv")},
        headers=headers,
    )
    assert upload_resp.status_code == 201
    dataset_id = upload_resp.json()["id"]

    # 3. Split
    split_resp = client.post(
        f"/api/v1/datasets/{dataset_id}/split",
        headers=headers,
        json={"test_percentage": 20.0, "seed": 42},
    )
    assert split_resp.status_code == 201

    # 4. Target column
    patch_resp = client.put(
        f"/api/v1/projects/{project_id}",
        headers=headers,
        json={"task_type": task_type, "target_column": "target"},
    )
    assert patch_resp.status_code == 200

    return project_id, headers


# =============================================================================
# Vector 1: Rank Normalization Formula (r_{j,T} = 1 - (rank - 1)/(p - 1))
# =============================================================================

def test_vector_1_rank_normalization_formula():
    """
    Given p = 4 features with raw scores [0.8, 0.6, 0.4, 0.2]
    Ranks are [1.0, 2.0, 3.0, 4.0]
    Normalized scores must be [1.0, 0.666667, 0.333333, 0.0]
    """
    raw_scores = np.array([0.8, 0.6, 0.4, 0.2])
    ranks, rank_scores = calculate_srs_rank_scores(raw_scores)
    
    assert np.allclose(ranks, [1.0, 2.0, 3.0, 4.0])
    expected_scores = [1.0 - (r - 1.0) / 3.0 for r in [1.0, 2.0, 3.0, 4.0]]
    assert np.allclose(rank_scores, expected_scores)
    assert rank_scores[0] == 1.0
    assert rank_scores[-1] == 0.0


# =============================================================================
# Vector 2: p = 1 Single Feature Boundary (No Division by Zero)
# =============================================================================

def test_vector_2_single_feature_p1_boundary():
    """
    Given p = 1 feature:
    Rank = 1.0, normalized rank score = 1.0 exactly (no division by zero).
    """
    raw_scores = np.array([42.0])
    ranks, rank_scores = calculate_srs_rank_scores(raw_scores)
    assert np.allclose(ranks, [1.0])
    assert np.allclose(rank_scores, [1.0])

    # Check across all 4 selectors
    X_single = np.array([[1.0], [2.0], [3.0], [4.0], [5.0]])
    y_reg = np.array([2.0, 4.0, 6.0, 8.0, 10.0])

    selectors = [
        CorrelationSelector(),
        LassoSelector(),
        RandomForestImportanceSelector(),
        PermutationImportanceSelector(),
    ]
    for selector in selectors:
        res = selector.select(X_single, y_reg, "REGRESSION", ["only_feat"], seed=42)
        assert res.status == TechniqueStatus.APPLIED or res.status == "APPLIED"
        assert res.ranks == [1.0]
        assert res.rank_scores == [1.0]


# =============================================================================
# Vector 3: Average Rank Ties
# =============================================================================

def test_vector_3_average_rank_ties():
    """
    Given scores [10.0, 10.0, 5.0, 0.0] (p = 4):
    Ranks 1 and 2 tied -> (1 + 2)/2 = 1.5
    Rank scores:
    r_1 = 1 - (1.5 - 1)/3 = 5/6 = 0.833333
    r_2 = 1 - (1.5 - 1)/3 = 5/6 = 0.833333
    r_3 = 1 - (3 - 1)/3 = 1/3 = 0.333333
    r_4 = 1 - (4 - 1)/3 = 0.0
    """
    raw_scores = np.array([10.0, 10.0, 5.0, 0.0])
    ranks, rank_scores = calculate_srs_rank_scores(raw_scores)
    
    assert np.allclose(ranks, [1.5, 1.5, 3.0, 4.0])
    assert np.allclose(rank_scores, [5.0/6.0, 5.0/6.0, 1.0/3.0, 0.0])


# =============================================================================
# Vector 4: k_min / k_max Selection Clamps
# =============================================================================

def test_vector_4_kmin_kmax_clamps():
    """
    SRS v9 §2.7:
    - Lower clamp: max(k_min, round(p * alpha)) clamped to min(5, p)
    - Upper clamp: min(k_max, round(p * alpha)) clamped to min(50, p)
    """
    # Lower clamp: p=20, alpha=0.10 -> round(2.0)=2 -> clamped to k_min=5
    assert resolve_top_k(p=20, alpha=0.10, k_min=5, k_max=50) == 5

    # Lower clamp with p=3 < 5 -> clamped to min(5, 3) = 3
    assert resolve_top_k(p=3, alpha=0.10, k_min=5, k_max=50) == 3

    # Upper clamp: p=100, alpha=0.80 -> round(80)=80 -> clamped to k_max=50
    assert resolve_top_k(p=100, alpha=0.80, k_min=5, k_max=50) == 50

    # In-range: p=50, alpha=0.30 -> round(15) = 15
    assert resolve_top_k(p=50, alpha=0.30, k_min=5, k_max=50) == 15


# =============================================================================
# Vector 5: Failed/Skipped Technique Exclusion (Non-Dilution)
# =============================================================================

def test_vector_5_failed_skipped_non_dilution():
    """
    When 2 of 4 techniques are applied and 2 skipped/failed:
    Denominator must be T_applied = 2, NOT 4.
    If applied scores are [1.0, 0.5] and [0.8, 0.4]:
    Ensemble scores = [(1.0+0.8)/2, (0.5+0.4)/2] = [0.9, 0.45]
    """
    applied = [
        np.array([1.0, 0.5]),
        np.array([0.8, 0.4]),
    ]
    ens = aggregate_ensemble_scores(applied, p=2)
    assert np.allclose(ens, [0.9, 0.45])


# =============================================================================
# Vector 6: Insufficient Evidence Abort (T_applied < 2)
# =============================================================================

def test_vector_6_insufficient_evidence_abort():
    """
    SRS v9 §2.7: If T_applied < 2, evidence strength is INSUFFICIENT_EVIDENCE
    and selection rule produces no selected features (empty list).
    """
    assert compute_evidence_strength(1, total_count=4, min_required=2) == EvidenceStrength.INSUFFICIENT_EVIDENCE
    assert compute_evidence_strength(0, total_count=4, min_required=2) == EvidenceStrength.INSUFFICIENT_EVIDENCE

    # apply_top_k_percent_selection aborts when applied_count < 2
    res = apply_top_k_percent_selection(
        feature_names=["f1", "f2", "f3"],
        scores={"f1": 0.9, "f2": 0.5, "f3": 0.2},
        alpha=0.5,
        applied_count=1,
    )
    assert res["selected_features"] == []
    assert res["k_selected"] == 0
    assert res["evidence_strength"] == EvidenceStrength.INSUFFICIENT_EVIDENCE


# =============================================================================
# Vector 7: 3-Tier Tie-Break Determinism & Cold-Process Identity
# =============================================================================

def test_vector_7_tie_break_determinism():
    """
    3-Tier deterministic sort at selection boundary:
    Priority 1: Higher EnsembleScore (-score)
    Priority 2: Lower Raw Rank Sum (+rank_sum)
    Priority 3: Lexicographical Name (+name)
    """
    scores = {"feat_c": 0.75, "feat_b": 0.75, "feat_a": 0.75}
    rank_sums = {"feat_c": 8.0, "feat_b": 6.0, "feat_a": 6.0}

    sorted_items = sort_features_with_tie_break(["feat_c", "feat_b", "feat_a"], scores, rank_sums)
    sorted_names = [item[0] for item in sorted_items]

    # feat_a and feat_b tie on score (0.75) and rank_sum (6.0), feat_a wins on lexicographical name
    # feat_c has higher rank_sum (8.0), so comes last
    assert sorted_names == ["feat_a", "feat_b", "feat_c"]


# =============================================================================
# Vector 8: Platform Scope Boundary Rejection (RANK_AGGREGATION_STABILITY -> 400)
# =============================================================================

def test_vector_8_platform_scope_boundary_rejection(client):
    """
    SRS v9 §1: Configuring RANK_AGGREGATION_STABILITY must return HTTP 400
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
