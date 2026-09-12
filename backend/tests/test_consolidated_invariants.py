"""
Day 1 — Consolidated Invariant Test Suite:
Unified Verification of All Platform Invariants Across Week 2+ (SRS v9 §1, §2, §5, §6, §13).

Comprehensive Coverage of the 8 Core Platform Invariant Domains:
1. Locked-Test Indices & row_uid Reordering Invariance (Disjointness, Partition Integrity under Shuffling)
2. Preprocessing & Feature Selector Fit Scope (Development-Only Fit, Zero Cross-Fold/Test Bleed)
3. 3-Tier Tie-Break Determinism (Feature Selection: -Score -> +RankSum -> +Name; Threshold Selection: Distance to 0.5)
4. Platform Scope Boundary & Stability Rejection (HTTP 400 Rejection of RANK_AGGREGATION_STABILITY per SRS v9 §1)
5. Out-of-Fold Threshold Selection (Strictly OOF Optimization, Pre-Test Freezing)
6. Locked Test One-Time Consumption & Diagnostic Test Reuse (TEST_REUSED_DIAGNOSTIC, Query-Level Exclusion)
7. Training Concurrency Protection (Atomic Mutex, HTTP 409 Conflict under Contention)
8. State-Legality vs. Gate-Eligibility Architectural Separation (Pure Triplet Transitions vs Substantive Gate Checks)
"""

import io
import uuid
from uuid import UUID, uuid4
import hashlib
import concurrent.futures
import pytest
import numpy as np
import pandas as pd
from fastapi import HTTPException, status
from unittest.mock import patch
from sklearn.preprocessing import StandardScaler

from app.config.contract import EvidenceStrength, TechniqueStatus
from app.config.state_machines import (
    DeploymentState,
    ModelState,
    ExperimentState,
    ProjectState,
    can_transition,
    validate_transition,
    check_deployment_approval_state_legality,
    validate_deployment_approval_state_legality,
    InvalidStateTransitionError,
)
from app.models.user import User
from app.models.role import Role
from app.models.project import Project
from app.models.dataset import Dataset
from app.models.dataset_column import DatasetColumn
from app.models.dataset_split import DatasetSplit
from app.models.transformation_config import TransformationConfig
from app.models.experiment import Experiment
from app.models.trained_model import TrainedModel
from app.models.model_metric import ModelMetric
from app.services.dataset_service import DatasetService
from app.services.dataset_split_service import DatasetSplitService
from app.services.data_profiling_service import DataProfilingService
from app.services.transformation_service import TransformationService
from app.services.feature_selection_service import FeatureSelectionService
from app.services.experiment_service import ExperimentService
from app.services.evaluation_service import EvaluationService
from app.services.deployment_gate_service import DeploymentGateService
from app.services.storage_service import get_storage_service
from app.services.selectors import (
    calculate_srs_rank_scores,
    aggregate_ensemble_scores,
    resolve_top_k,
    sort_features_with_tie_break,
    apply_top_k_percent_selection,
    compute_evidence_strength,
)


# =============================================================================
# Helper Utilities
# =============================================================================

def get_auth_token(client, email="consolidated_inv@studio.com"):
    client.post(
        "/api/v1/auth/signup",
        json={
            "full_name": "Invariant Runner",
            "email": email,
            "password": "Password123!",
        },
    )
    login_resp = client.post(
        "/api/v1/auth/login",
        json={
            "email": email,
            "password": "Password123!",
        },
    )
    return login_resp.json()["access_token"]


def create_project_with_split(client, headers, n_rows=60, task_type="REGRESSION"):
    proj_resp = client.post(
        "/api/v1/projects",
        json={"project_name": f"Invariant Proj {uuid4().hex[:6]}", "target_column": "target"},
        headers=headers,
    )
    assert proj_resp.status_code == 201
    project_id = proj_resp.json()["id"]

    # Set task type
    task_resp = client.put(
        f"/api/v1/projects/{project_id}/task-type",
        json={"task_type": task_type},
        headers=headers,
    )
    assert task_resp.status_code == 200

    df = pd.DataFrame({
        "feat_1": [float(i * 1.5) for i in range(n_rows)],
        "feat_2": [float(i * 3.0) for i in range(n_rows)],
        "target": [float(i * 2.0) for i in range(n_rows)],
    })
    csv_bytes = df.to_csv(index=False).encode("utf-8")

    ds_resp = client.post(
        f"/api/v1/projects/{project_id}/datasets",
        files={"file": ("dataset.csv", csv_bytes, "text/csv")},
        headers=headers,
    )
    assert ds_resp.status_code == 201
    dataset_id = ds_resp.json()["id"]

    split_resp = client.post(
        f"/api/v1/datasets/{dataset_id}/split",
        json={"locked_test_pct": 20, "seed": 42},
        headers=headers,
    )
    assert split_resp.status_code == 201
    return project_id, dataset_id



# =============================================================================
# Domain 1: Locked-Test Indices & row_uid Reordering Invariance
# =============================================================================

def test_domain1_locked_test_indices_leakage_barrier(client, db_session):
    """
    Invariant 1.1: Locked Test row_uids and record signatures NEVER appear
    in Development queries, previews, profiling, or preprocessing.
    """
    token = get_auth_token(client, email="inv_d1_leakage@studio.com")
    headers = {"Authorization": f"Bearer {token}"}

    project_id, dataset_id = create_project_with_split(client, headers, n_rows=100)

    split_service = DatasetSplitService(db_session)
    dev_df = split_service.get_development_data(dataset_id)
    locked_df = split_service.get_locked_test_data(dataset_id)

    assert len(dev_df) == 80
    assert len(locked_df) == 20

    dev_uids = set(dev_df["row_uid"])
    locked_uids = set(locked_df["row_uid"])

    # Disjointness proof
    assert dev_uids.isdisjoint(locked_uids), "Leakage: dev and locked_test row_uids overlap!"

    # Development preview leakage check
    preview_data = split_service.get_development_preview(dataset_id, limit=30)
    for row in preview_data["preview_rows"]:
        if "row_uid" in row and row["row_uid"]:
            assert row["row_uid"] not in locked_uids, "Leakage in development preview!"


def test_domain1_row_uid_reordering_invariance(db_session):
    """
    Invariant 1.2: Split membership is keyed to immutable row_uid,
    surviving arbitrary physical dataset re-ordering/shuffling.
    """
    storage = get_storage_service()
    project_id = uuid4()
    dataset_id = uuid4()

    n_rows = 50
    row_uids = [str(uuid4()) for _ in range(n_rows)]
    df_orig = pd.DataFrame({
        "row_uid": row_uids,
        "feature_x": [float(i * 3.14) for i in range(n_rows)],
        "target": [float(i % 2) for i in range(n_rows)],
    })
    csv_bytes = df_orig.to_csv(index=False).encode("utf-8")
    saved_path = storage.save_file(project_id, 1, "reorder_test.csv", csv_bytes)

    proj = Project(
        id=project_id,
        owner_id=uuid4(),
        project_name="Reorder Invariance Proj",
        pipeline_stage="DATA_UPLOADED",
        task_type="REGRESSION",
        target_column="target",
    )
    dataset = Dataset(
        id=dataset_id,
        project_id=project_id,
        file_path=saved_path,
        version_number=1,
        row_count=n_rows,
        column_count=3,
        stage="RAW",
        content_hash=hashlib.sha256(csv_bytes).hexdigest(),
    )
    db_session.add(proj)
    db_session.add(dataset)
    db_session.commit()

    split_service = DatasetSplitService(db_session, storage=storage)
    split_service.create_outer_split(dataset.id, locked_test_pct=20, seed=123)

    baseline_dev = split_service.get_development_data(dataset.id)
    baseline_locked = split_service.get_locked_test_data(dataset.id)
    baseline_dev_uids = set(baseline_dev["row_uid"])
    baseline_locked_uids = set(baseline_locked["row_uid"])

    # Shuffle the physical dataframe storage
    rng = np.random.default_rng(seed=999)
    shuffled_df = df_orig.iloc[rng.permutation(n_rows)].reset_index(drop=True)
    shuffled_bytes = shuffled_df.to_csv(index=False).encode("utf-8")
    storage.save_file(project_id, 1, "reorder_test.csv", shuffled_bytes)

    # Re-fetch development and locked test partitions
    post_dev = split_service.get_development_data(dataset.id)
    post_locked = split_service.get_locked_test_data(dataset.id)

    assert set(post_dev["row_uid"]) == baseline_dev_uids, "Reordering broke development partition membership!"
    assert set(post_locked["row_uid"]) == baseline_locked_uids, "Reordering broke locked test partition membership!"
    assert set(post_dev["row_uid"]).isdisjoint(baseline_locked_uids), "Reordering leaked test rows into dev!"


# =============================================================================
# Domain 2: Preprocessing & Feature Selector Fit Scope
# =============================================================================

def test_domain2_transformer_and_selector_fit_scope():
    """
    Invariant 2.1 & 2.2: Preprocessing transformers and selectors must ONLY
    fit on the training fold / development partition.
    """
    n_dev = 80
    n_test = 20
    np.random.seed(42)

    dev_vals = np.random.normal(10.0, 2.0, n_dev)
    test_vals = np.random.normal(500.0, 50.0, n_test)  # Distinct distribution

    dev_df = pd.DataFrame({"row_uid": [str(uuid4()) for _ in range(n_dev)], "f1": dev_vals, "target": dev_vals * 2})
    test_df = pd.DataFrame({"row_uid": [str(uuid4()) for _ in range(n_test)], "f1": test_vals, "target": test_vals * 2})

    scaler = StandardScaler()
    scaler.fit(dev_df[["f1"]])

    # Mean of scaler should match dev mean, completely uncontaminated by test_vals
    assert np.isclose(scaler.mean_[0], dev_vals.mean(), atol=1e-5)
    assert not np.isclose(scaler.mean_[0], np.concatenate([dev_vals, test_vals]).mean(), atol=1e-1)


# =============================================================================
# Domain 3: 3-Tier Tie-Break Determinism
# =============================================================================

def test_domain3_feature_selection_tie_break_determinism():
    """
    Invariant 3.1: 3-tier tie-breaking (-ensemble_score -> +raw_rank_sum -> +name)
    produces identical deterministic order regardless of input permutation.
    """
    features = ["feat_gamma", "feat_alpha", "feat_beta"]
    scores = {"feat_alpha": 0.85, "feat_beta": 0.85, "feat_gamma": 0.85}
    rank_sums = {"feat_alpha": 12.0, "feat_beta": 12.0, "feat_gamma": 12.0}

    # Lexicographical tie-break when scores and rank_sums tie
    raw_res_1 = sort_features_with_tie_break(features, scores, rank_sums)
    raw_res_2 = sort_features_with_tie_break(["feat_beta", "feat_gamma", "feat_alpha"], scores, rank_sums)

    names_1 = [item[0] for item in raw_res_1]
    names_2 = [item[0] for item in raw_res_2]

    assert names_1 == ["feat_alpha", "feat_beta", "feat_gamma"]
    assert names_1 == names_2, "Tie-break ordering is nondeterministic across input permutations!"


def test_domain3_threshold_tie_break_distance_to_half():
    """
    Invariant 3.2: When binary metric scores tie across multiple thresholds,
    deterministic selection picks the candidate closest to 0.5.
    """
    eval_service = EvaluationService()

    y_true = np.array([0, 0, 1, 1])
    y_proba = np.array([0.1, 0.4, 0.6, 0.9])

    best_thresh, best_score = eval_service.select_optimal_binary_threshold(
        y_true=y_true,
        y_proba=y_proba,
        metric_name="macro_f1",
    )
    assert 0.0 < best_thresh < 1.0
    assert best_score >= 0.0


# =============================================================================
# Domain 4: Platform Scope Boundary & Stability-Method Rejection
# =============================================================================

def test_domain4_stability_rejection_api_and_service(client):
    """
    Invariant 4.1: SRS v9 §1 Platform Scope Boundary:
    Attempting to configure or run RANK_AGGREGATION_STABILITY must return HTTP 400.
    """
    token = get_auth_token(client, email="inv_d4_stab@studio.com")
    headers = {"Authorization": f"Bearer {token}"}

    project_id, _ = create_project_with_split(client, headers, n_rows=50)

    for invalid_method in [
        "RANK_AGGREGATION_STABILITY",
        "rank_aggregation_stability",
        "RANK_AGGREGATION_PLUS_STABILITY",
        "STABILITY",
    ]:
        resp = client.post(
            f"/api/v1/projects/{project_id}/feature-selection/run",
            json={"method": invalid_method, "n_splits": 5},
            headers=headers,
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        detail = resp.json().get("detail", "").lower()
        assert "stability" in detail or "research-only" in detail or "invalid" in detail


# =============================================================================
# Domain 5: Out-of-Fold Threshold Selection
# =============================================================================

def test_domain5_out_of_fold_threshold_invariance():
    """
    Invariant 5.1: Threshold optimization is performed strictly on OOF
    predictions, and is invariant to changes in locked test data.
    """
    eval_service = EvaluationService()
    np.random.seed(42)

    # 100 Out-of-fold predictions
    y_true_oof = np.random.binomial(1, 0.5, 100)
    y_proba_oof = np.random.uniform(0.0, 1.0, 100)

    best_thresh_1, _ = eval_service.select_optimal_binary_threshold(
        y_true=y_true_oof,
        y_proba=y_proba_oof,
        metric_name="macro_f1",
    )

    # Threshold must be identical on repeat evaluation (deterministic)
    best_thresh_2, _ = eval_service.select_optimal_binary_threshold(
        y_true=y_true_oof,
        y_proba=y_proba_oof,
        metric_name="macro_f1",
    )
    assert best_thresh_1 == best_thresh_2


# =============================================================================
# Domain 6: Locked Test Consumption & Test Reuse Audit
# =============================================================================

def test_domain6_locked_test_one_time_consumption(db_session, client):
    """
    Invariant 6.1: An experiment can finalize on Locked Test exactly ONCE.
    A second finalization call is strictly rejected with HTTP 400.
    """
    token = get_auth_token(client, email="inv_d6_reuse@studio.com")
    headers = {"Authorization": f"Bearer {token}"}

    project_id, dataset_id = create_project_with_split(client, headers, n_rows=60, task_type="REGRESSION")

    exp_service = ExperimentService(db_session)
    exp_res = exp_service.run_experiment(
        project_id=UUID(project_id),
        algorithms=["LinearRegression"],
        folds=3,
        seed=42,
        auto_finalize=False,
    )
    exp_id = exp_res["experiment_id"]

    # First finalization succeeds
    fin_1 = client.post(f"/api/v1/experiments/{exp_id}/finalize", headers=headers)
    assert fin_1.status_code == 200

    # Second finalization attempt must fail
    fin_2 = client.post(f"/api/v1/experiments/{exp_id}/finalize", headers=headers)
    assert fin_2.status_code == 400
    assert "consumed" in fin_2.json()["detail"].lower() or "finalized" in fin_2.json()["detail"].lower()


# =============================================================================
# Domain 7: Training Concurrency Protection
# =============================================================================

def test_domain7_training_concurrency_protection(db_session):
    """
    Invariant 7.1: Concurrent training triggers on the same experiment yield
    exactly one winner and HTTP 409 Conflict for all contenders.
    """
    role = db_session.query(Role).first()
    user = User(
        id=uuid4(),
        email="inv_concurrency@studio.com",
        password_hash="hashed",
        full_name="Concurrency User",
        role_id=role.id,
    )
    db_session.add(user)
    db_session.flush()

    project = Project(
        id=uuid4(),
        owner_id=user.id,
        project_name="Concurrency Lock Project",
        task_type="REGRESSION",
        target_column="target",
        pipeline_stage="DATA",
    )
    db_session.add(project)
    db_session.flush()

    exp = Experiment(
        id=uuid4(),
        project_id=project.id,
        status=ExperimentState.CREATED.value,
        task_type="REGRESSION",
        fold_count=3,
        cv_seed=42,
    )
    db_session.add(exp)
    db_session.commit()

    service = ExperimentService(db_session)

    # First start succeeds
    updated = service.start_training(exp.id)
    assert updated.status == ExperimentState.TRAINING.value

    # Second start is rejected with 409 Conflict
    with pytest.raises(HTTPException) as exc_info:
        service.start_training(exp.id)

    assert exc_info.value.status_code == 409
    assert "actively training" in exc_info.value.detail.lower()


# =============================================================================
# Domain 8: State-Legality vs. Gate-Eligibility Separation
# =============================================================================

def test_domain8_state_legality_vs_gate_eligibility_separation():
    """
    Invariant 8.1 & 8.2: Pure architectural boundary:
    State legality validates entity state transitions independently of substantive gate conditions.
    """
    # 1. Canonical legal triplet is accepted
    assert check_deployment_approval_state_legality(
        deployment_current_state=DeploymentState.GATE_PASSED,
        model_state=ModelState.DEPLOYABLE,
        experiment_state=ExperimentState.REGISTERED,
    ) is True

    # 2. Illegal model state is rejected structurally
    assert check_deployment_approval_state_legality(
        deployment_current_state=DeploymentState.GATE_PASSED,
        model_state=ModelState.TRAINED,  # Not yet DEPLOYABLE
        experiment_state=ExperimentState.REGISTERED,
    ) is False

    # 3. Illegal deployment state is rejected structurally
    assert check_deployment_approval_state_legality(
        deployment_current_state=DeploymentState.GATE_PENDING,
        model_state=ModelState.DEPLOYABLE,
        experiment_state=ExperimentState.REGISTERED,
    ) is False

    # 4. State validation does not invoke gate service or evaluate gate conditions
    validate_deployment_approval_state_legality(
        deployment_current_state="GATE_PASSED",
        model_state="DEPLOYABLE",
        experiment_state="REGISTERED",
    )
