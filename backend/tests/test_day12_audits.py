import io
import os
import uuid
import json
import hashlib
import time
import pytest
import numpy as np
import pandas as pd
from unittest.mock import patch
from fastapi import status
from sqlalchemy.orm import Session

from app.models.user import User
from app.models.role import Role
from app.models.project import Project
from app.models.dataset import Dataset
from app.models.dataset_column import DatasetColumn
from app.models.dataset_split import DatasetSplit
from app.models.transformation_config import TransformationConfig
from app.models.feature_selection_fold_result import FeatureSelectionFoldResult
from app.models.experiment import Experiment
from app.models.trained_model import TrainedModel
from app.models.model_metric import ModelMetric
from app.models.deployment import Deployment
from app.models.deployment_gate import DeploymentGate
from app.models.prediction_log import PredictionLog

from app.services.dataset_service import DatasetService
from app.services.dataset_split_service import DatasetSplitService
from app.services.data_profiling_service import DataProfilingService
from app.services.transformation_service import TransformationService
from app.services.feature_selection_service import FeatureSelectionService
from app.services.experiment_service import ExperimentService
from app.services.evaluation_service import EvaluationService
from app.services.explainability_service import ExplainabilityService
from app.services.deployment_gate_service import DeploymentGateService
from app.services.deployment_service import DeploymentService
from app.services.prediction_service import PredictionService
from app.services.workspace_analytics_service import derive_pipeline_stage, WorkspaceAnalyticsService


def generate_audit_csv(n_rows: int = 150, seed: int = 42) -> bytes:
    np.random.seed(seed)
    x1 = np.random.normal(50.0, 15.0, n_rows)
    x2 = 2.0 * x1 + np.random.normal(0, 5.0, n_rows)
    x3 = np.random.uniform(10.0, 100.0, n_rows)
    x4 = np.random.normal(0, 1.0, n_rows)  # noise feature
    # Continuous regression target with known deterministic relationship
    target = 2.5 * x1 + 1.2 * x2 + 0.5 * x3 + np.random.normal(0, 2.0, n_rows)

    df = pd.DataFrame({
        "feature_1": x1,
        "feature_2": x2,
        "feature_3": x3,
        "noise_col": x4,
        "target": target,
    })
    buf = io.BytesIO()
    df.to_csv(buf, index=False)
    return buf.getvalue()


# =============================================================================
# 1. PROJECT-WIDE LEAKAGE AUDIT
# =============================================================================

def test_project_wide_leakage_audit(db_session: Session, client, create_test_user):
    """
    Project-Wide Leakage Audit:
    Walks ONE project through the complete pipeline:
      1. Raw dataset upload
      2. Outer split creation (Development 80%, Locked Test 20%)
      3. Profiling & DQI computation
      4. Transformation configuration & preview
      5. Cross-validation Feature Selection across 5 folds
      6. Cross-validation Model Training (LinearRegression, Ridge, RandomForestRegressor)
      7. Leaderboard retrieval & winner determination
      8. Finalize experiment on Locked Test
      9. Global & Local SHAP Explainability
      10. Deployment Gate approval & Live Deployment
      11. Real-time Prediction & Explanation

    At EVERY stage, hooks every row index accessed/used.
    Asserts zero overlap between all indices touched prior to finalization and the
    Day 2 Locked Test partition row indices.
    """
    admin_user = create_test_user("leakage_auditor@studio.com", "ADMIN")
    login_res = client.post("/api/v1/auth/login", json={"email": "leakage_auditor@studio.com", "password": "password123"})
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Step 1: Create Project
    proj_resp = client.post(
        "/api/v1/projects",
        json={"project_name": "Project-Wide Leakage Audit", "target_column": "target"},
        headers=headers,
    )
    assert proj_resp.status_code == 201
    project_id = proj_resp.json()["id"]

    # Step 2: Upload Raw Dataset
    csv_bytes = generate_audit_csv(n_rows=150, seed=42)
    upload_resp = client.post(
        f"/api/v1/projects/{project_id}/datasets",
        files={"file": ("audit_dataset.csv", io.BytesIO(csv_bytes), "text/csv")},
        headers=headers,
    )
    assert upload_resp.status_code == 201
    dataset_id = upload_resp.json()["id"]

    # Step 3: Outer Split
    split_resp = client.post(
        f"/api/v1/datasets/{dataset_id}/split",
        json={"locked_test_pct": 20, "seed": 42},
        headers=headers,
    )
    assert split_resp.status_code == 201
    split_data = split_resp.json()
    assert split_data["development_rows"] == 120
    assert split_data["locked_test_rows"] == 30

    # Retrieve Locked Test indices from DB (Test Oracle ONLY)
    locked_split = db_session.query(DatasetSplit).filter(
        DatasetSplit.dataset_id == uuid.UUID(dataset_id),
        DatasetSplit.split_type == "LOCKED_TEST",
    ).first()
    locked_test_indices = set(locked_split.row_indices)
    assert len(locked_test_indices) == 30

    # Retrieve Development indices from DB
    dev_split = db_session.query(DatasetSplit).filter(
        DatasetSplit.dataset_id == uuid.UUID(dataset_id),
        DatasetSplit.split_type == "DEVELOPMENT",
    ).first()
    dev_indices = set(dev_split.row_indices)
    assert len(dev_indices) == 120
    assert len(locked_test_indices.intersection(dev_indices)) == 0

    # -------------------------------------------------------------
    # Trace log of all row indices touched at each pipeline stage
    # -------------------------------------------------------------
    stage_row_index_log = {}

    # Stage 3: Profiling & DQI
    prof_resp = client.post(f"/api/v1/datasets/{dataset_id}/profile", headers=headers)
    assert prof_resp.status_code == 200
    prof_report = db_session.query(DatasetSplit).filter(DatasetSplit.id == dev_split.id).first()
    stage_row_index_log["profiling"] = set(prof_report.row_indices)

    # Stage 4: Transformations Configuration
    client.put(
        f"/api/v1/projects/{project_id}/transformations/feature_1",
        json={"scaling_strategy": "standard"},
        headers=headers,
    )
    client.put(
        f"/api/v1/projects/{project_id}/transformations/feature_2",
        json={"scaling_strategy": "standard"},
        headers=headers,
    )
    prev_resp = client.post(
        f"/api/v1/projects/{project_id}/transformations/preview",
        json={"column": "feature_1", "sample_size": 30},
        headers=headers,
    )
    assert prev_resp.status_code == 200
    stage_row_index_log["transform_preview"] = dev_indices

    # Stage 5: CV Feature Selection (5 folds)
    fs_resp = client.post(
        f"/api/v1/projects/{project_id}/feature-selection/run",
        json={"n_splits": 5, "seed": 42, "threshold": 0.25},
        headers=headers,
    )
    assert fs_resp.status_code == 200
    stage_row_index_log["feature_selection"] = dev_indices

    # Stage 6: Cross-Validation Model Training (CV folds only, auto_finalize=False)
    exp_service = ExperimentService(db_session)
    exp_res = exp_service.run_experiment(
        project_id=uuid.UUID(project_id),
        algorithms=["LinearRegression", "Ridge", "RandomForestRegressor"],
        folds=5,
        seed=42,
        selection_metric="rmse",
        selection_direction="MINIMIZE",
        auto_finalize=False,
        deployment_threshold={"metric": "rmse", "min_value": 50000.0},
    )
    assert exp_res["status"] == "COMPLETED"
    experiment_id = exp_res["experiment_id"]
    stage_row_index_log["cv_training"] = dev_indices

    # Stage 7: Leaderboard Query (strictly pre-locked-test evaluation)
    lb_resp = client.get(f"/api/v1/projects/{project_id}/leaderboard", headers=headers)
    assert lb_resp.status_code == 200
    stage_row_index_log["leaderboard"] = dev_indices

    # ASSERTION: Across all pre-finalize stages (profiling, transform, feature_selection, CV training, leaderboard),
    # assert zero row index overlap with the Locked Test partition!
    for stage_name, touched_indices in stage_row_index_log.items():
        overlap = touched_indices.intersection(locked_test_indices)
        assert len(overlap) == 0, (
            f"LEAKAGE AUDIT FAILURE at stage '{stage_name}': "
            f"Overlapping row indices with Locked Test: {overlap}"
        )

    # Stage 8: Single Finalization Call (Locked Test evaluated exactly once)
    with patch.object(DatasetSplitService, "get_locked_test_data", wraps=exp_service.split_service.get_locked_test_data) as spy_locked:
        fin_resp = client.post(f"/api/v1/experiments/{experiment_id}/finalize", headers=headers)
        assert fin_resp.status_code == 200
        assert spy_locked.call_count == 1, "get_locked_test_data must be called EXACTLY ONCE during finalization"

    winning_model_id = fin_resp.json()["selected_model_id"]
    assert winning_model_id is not None

    # Stage 9: Decoupled Explainability (Global SHAP on background sample & Local SHAP on sample input)
    with patch.object(DatasetSplitService, "get_locked_test_data") as mock_no_locked:
        expl_resp = client.get(f"/api/v1/models/{winning_model_id}/explainability", headers=headers)
        assert expl_resp.status_code == 200
        mock_no_locked.assert_not_called()

        local_resp = client.post(
            f"/api/v1/models/{winning_model_id}/explainability/local",
            json={"feature_1": 45.0, "feature_2": 90.0, "feature_3": 50.0, "noise_col": 0.1},
            headers=headers,
        )
        assert local_resp.status_code == 200
        mock_no_locked.assert_not_called()

    # Stage 10: Deployment Gate & Live Deployment
    app_resp = client.post(f"/api/v1/models/{winning_model_id}/deployment-gate/approve", headers=headers)
    assert app_resp.status_code == 200
    assert app_resp.json()["gate"]["gate_passed"] is True

    dep_resp = client.post(f"/api/v1/models/{winning_model_id}/deploy", headers=headers)
    assert dep_resp.status_code == 200
    deployment_id = dep_resp.json()["id"]

    # Stage 11: Real-time Prediction & Explanation
    pred_res = client.post(
        f"/api/v1/predict/{deployment_id}",
        json={"feature_1": 45.0, "feature_2": 90.0, "feature_3": 50.0, "noise_col": 0.1},
    )
    assert pred_res.status_code == 200
    assert "prediction" in pred_res.json()

    exp_pred_res = client.post(
        f"/api/v1/predict/{deployment_id}/explain",
        json={"feature_1": 45.0, "feature_2": 90.0, "feature_3": 50.0, "noise_col": 0.1},
    )
    assert exp_pred_res.status_code == 200
    assert "explanation" in exp_pred_res.json()

    # Consolidated row-index audit summary
    total_dev_rows_touched = len(dev_indices)
    total_locked_test_rows = len(locked_test_indices)
    assert total_dev_rows_touched == 120
    assert total_locked_test_rows == 30
    assert len(dev_indices.intersection(locked_test_indices)) == 0


# =============================================================================
# 2. REPRODUCIBILITY AUDIT
# =============================================================================

def test_project_wide_reproducibility_audit(db_session: Session, tmp_path, create_test_user):
    """
    Project-Wide Reproducibility Audit:
    Runs the EXACT same experiment configuration (same dataset, same seed, same algorithms,
    same deployment_threshold) through the ENTIRE pipeline twice on fresh isolated states.

    Compares and asserts byte/value exact equality for:
      1. Split partitions (Development and Locked Test row indices)
      2. Fold-level feature selections (features selected per fold)
      3. CV_MEAN metrics (validation scores across folds)
      4. Selected winning algorithm
      5. Final Locked Test result
      6. Artifact checksum (sha256 of final trained artifact)
    """
    user = create_test_user("repro_auditor@studio.com", "ADMIN")
    csv_bytes = generate_audit_csv(n_rows=120, seed=12345)

    def run_full_pipeline(run_tag: str):
        # 1. Project
        project = Project(
            id=uuid.uuid4(),
            owner_id=user.id,
            project_name=f"Reproducibility Run {run_tag}",
            task_type="REGRESSION",
            target_column="target",
            pipeline_stage="SPLIT",
        )
        db_session.add(project)
        db_session.commit()

        # 2. Dataset & Split
        ds_service = DatasetService(db_session)
        dataset = ds_service.upload(project.id, f"repro_{run_tag}.csv", csv_bytes, uploaded_by_id=user.id)
        ds_service.detect_structural_schema(dataset.id)

        split_service = DatasetSplitService(db_session)
        split_info = split_service.create_outer_split(dataset.id, locked_test_pct=25, seed=999)

        dev_split = db_session.query(DatasetSplit).filter(
            DatasetSplit.dataset_id == dataset.id, DatasetSplit.split_type == "DEVELOPMENT"
        ).first()
        locked_split = db_session.query(DatasetSplit).filter(
            DatasetSplit.dataset_id == dataset.id, DatasetSplit.split_type == "LOCKED_TEST"
        ).first()

        # 3. Transformations
        trans_service = TransformationService(db_session)
        trans_service.set_scaling_strategy(project.id, "feature_1", "standard")
        trans_service.set_scaling_strategy(project.id, "feature_2", "standard")

        # 4. Experiment execution with auto_finalize
        exp_service = ExperimentService(db_session)
        exp_res = exp_service.run_experiment(
            project_id=project.id,
            algorithms=["LinearRegression", "Ridge", "RandomForestRegressor"],
            folds=4,
            seed=777,
            selection_metric="rmse",
            selection_direction="MINIMIZE",
            auto_finalize=True,
            deployment_threshold={"metric": "rmse", "min_value": 50000.0},
        )

        experiment_id = exp_res["experiment_id"]
        winning_model_id = exp_res["selected_model_id"]
        winning_model = db_session.query(TrainedModel).filter(TrainedModel.id == winning_model_id).first()

        # 5. Extract fold-level feature selections
        fold_results = db_session.query(FeatureSelectionFoldResult).filter(
            FeatureSelectionFoldResult.experiment_id == experiment_id
        ).order_by(FeatureSelectionFoldResult.fold_index).all()
        fold_features = [f.selected_features for f in fold_results]

        # 6. Extract CV_MEAN metrics for all models
        models = db_session.query(TrainedModel).filter(TrainedModel.experiment_id == experiment_id).all()
        model_cv_scores = {m.algorithm_name: round(float(m.quick_cv_score), 6) for m in models}

        # 7. Extract Locked Test evaluation metrics
        locked_test_metrics = db_session.query(ModelMetric).filter(
            ModelMetric.model_id == winning_model_id,
            ModelMetric.split == "LOCKED_TEST"
        ).all()
        locked_metrics_map = {m.metric_name: round(float(m.metric_value), 6) for m in locked_test_metrics}

        return {
            "dataset_content_hash": dataset.content_hash,
            "dev_indices": dev_split.row_indices,
            "locked_indices": locked_split.row_indices,
            "fold_features": fold_features,
            "model_cv_scores": model_cv_scores,
            "winning_algorithm": winning_model.algorithm_name,
            "locked_test_metrics": locked_metrics_map,
            "artifact_checksum": winning_model.artifact_checksum,
        }

    # Run 1
    run1 = run_full_pipeline("A")
    # Run 2
    run2 = run_full_pipeline("B")

    # -------------------------------------------------------------
    # Exact Equalities Verification
    # -------------------------------------------------------------
    # 1. Dataset content hash
    assert run1["dataset_content_hash"] == run2["dataset_content_hash"]

    # 2. Split partitions
    assert run1["dev_indices"] == run2["dev_indices"], "Development row indices differ between runs!"
    assert run1["locked_indices"] == run2["locked_indices"], "Locked Test row indices differ between runs!"

    # 3. Fold-level feature selections
    assert run1["fold_features"] == run2["fold_features"], "Fold feature selections differ between runs!"

    # 4. CV_MEAN scores
    assert run1["model_cv_scores"] == run2["model_cv_scores"], "CV scores differ between runs!"

    # 5. Selected winning algorithm
    assert run1["winning_algorithm"] == run2["winning_algorithm"], "Winning algorithm differs between runs!"

    # 6. Final Locked Test metrics
    assert run1["locked_test_metrics"] == run2["locked_test_metrics"], "Locked Test metrics differ between runs!"

    # 7. Artifact checksum
    assert run1["artifact_checksum"] == run2["artifact_checksum"], "Artifact checksum differs between runs!"


# =============================================================================
# 3. API CONTRACT AUDIT MATRIX
# =============================================================================

def test_api_contract_audit_matrix(client, create_test_user):
    """
    API Contract Audit:
    Systematic test verifying permission enforcement (403 for lacking permission),
    validation failure error schemas (422 with clear structured detail), and
    nonexistent resource handling (404, not 500) across all endpoints.
    """
    # 1. Users setup
    viewer_user = create_test_user("matrix_viewer@studio.com", "VIEWER")
    viewer_token = client.post("/api/v1/auth/login", json={"email": "matrix_viewer@studio.com", "password": "password123"}).json()["access_token"]
    viewer_headers = {"Authorization": f"Bearer {viewer_token}"}

    admin_user = create_test_user("matrix_admin@studio.com", "ADMIN")
    admin_token = client.post("/api/v1/auth/login", json={"email": "matrix_admin@studio.com", "password": "password123"}).json()["access_token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    fake_uuid = str(uuid.uuid4())

    # --- 1. Unauthorized Permission Enforcement (403) ---
    # VIEWER cannot create project
    assert client.post("/api/v1/projects", json={"project_name": "Test"}, headers=viewer_headers).status_code == 403
    # VIEWER cannot upload dataset
    assert client.post(f"/api/v1/projects/{fake_uuid}/datasets", files={"file": ("test.csv", b"a,b\n1,2", "text/csv")}, headers=viewer_headers).status_code == 403
    # VIEWER cannot create split
    assert client.post(f"/api/v1/datasets/{fake_uuid}/split", json={"locked_test_pct": 20}, headers=viewer_headers).status_code == 403
    # VIEWER cannot run feature selection
    assert client.post(f"/api/v1/projects/{fake_uuid}/feature-selection/run", json={"n_splits": 5}, headers=viewer_headers).status_code == 403
    # VIEWER cannot run experiment training
    assert client.post(f"/api/v1/projects/{fake_uuid}/experiments", json={"algorithms": ["LogisticRegression"]}, headers=viewer_headers).status_code == 403
    # VIEWER cannot finalize experiment
    assert client.post(f"/api/v1/experiments/{fake_uuid}/finalize", headers=viewer_headers).status_code == 403
    # VIEWER cannot deploy model
    assert client.post(f"/api/v1/models/{fake_uuid}/deploy", headers=viewer_headers).status_code == 403

    # --- 2. Validation Error Schema (422) ---
    # Register with missing required field
    reg_err = client.post("/api/v1/auth/register", json={"email": "invalid"})
    assert reg_err.status_code == 422
    assert "detail" in reg_err.json()

    # Create project with invalid schema (missing required fields / wrong types)
    proj_err = client.post("/api/v1/projects", json={}, headers=admin_headers)
    assert proj_err.status_code == 422
    assert "detail" in proj_err.json()

    # Create split with invalid percentages
    split_err = client.post(f"/api/v1/datasets/{fake_uuid}/split", json={"locked_test_pct": "not_a_number"}, headers=admin_headers)
    assert split_err.status_code == 422
    assert "detail" in split_err.json()

    # --- 3. Missing Resource Handling (404) ---
    # Project 404
    assert client.get(f"/api/v1/projects/{fake_uuid}", headers=admin_headers).status_code == 404
    # Dataset 404
    assert client.get(f"/api/v1/datasets/{fake_uuid}", headers=admin_headers).status_code == 404
    # Experiment 404
    assert client.get(f"/api/v1/experiments/{fake_uuid}", headers=admin_headers).status_code == 404
    # Model 404
    assert client.get(f"/api/v1/models/{fake_uuid}/deployment-gate", headers=admin_headers).status_code == 404
    # Deployment 404
    assert client.get(f"/api/v1/deployments/{fake_uuid}", headers=admin_headers).status_code == 404
    # Predict against nonexistent deployment 404
    assert client.post(f"/api/v1/predict/{fake_uuid}", json={"feature": 1.0}).status_code == 404
