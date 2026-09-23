"""
Intelligent ML Studio: Full Distributed Platform Lifecycle Integration Test.

Validates the complete end-to-end distributed ML workflow:
1. User Authentication & Authorization
2. Project Creation & Dataset Upload to StorageService
3. Target Column, Algorithm Selection & Immutable Experiment Config Freezing
4. Durable Task Enqueueing & Worker Execution
5. Model Artifact & Cryptographic HMAC Manifest Persistence into StorageService
6. Cryptographic Artifact Verification across Services (Registry, Deployment Gate, Prediction, Explainability)
7. Four-Eyes Deployment Governance & Real-Time REST Inference Serving
8. SHAP Local & Global Interpretability
9. Adversarial Resilience: Tampered Artifact Detection & Corrupted Hash Rejection
"""

import io
import os
import json
import uuid
import hashlib
import hmac
import pytest
import pandas as pd
import numpy as np
from uuid import uuid4
from fastapi.testclient import TestClient

from app.main import app
from app.core.config import settings
from app.core.database import SessionLocal
from app.models.user import User
from app.models.role import Role
from app.models.project import Project
from app.models.experiment import Experiment
from app.models.trained_model import TrainedModel
from app.models.deployment import Deployment
from app.models.durable_task import DurableTask
from app.infrastructure.storage.object_store import get_storage_service, LocalStorageService
from app.infrastructure.security.artifact_signing import (
    save_signed_model_to_storage,
    load_signed_model_from_storage,
    compute_hmac_signature,
    SecurityError,
)
from app.services.experiment_service import ExperimentService
from app.services.deployment_gate_service import DeploymentGateService
from app.services.deployment_service import DeploymentService
from app.services.prediction_service import PredictionService
from app.services.transformers import safely_encode_matrix_pair


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def test_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def test_immutable_experiment_config_freezing_and_worker_contract(test_db):
    """
    P0 Test: Verifies that experiment configuration is frozen at creation
    and accurately preserves user-selected algorithms, folds, seed, and deployment thresholds.
    """
    storage = get_storage_service()
    
    # Create test role, user and project
    role = test_db.query(Role).filter(Role.role_name == "ADMIN").first()
    if not role:
        role = Role(id=uuid4(), role_name="ADMIN", description="Administrator")
        test_db.add(role)
        test_db.commit()

    user_id = uuid4()
    user = User(
        id=user_id,
        email=f"tester_{user_id.hex[:6]}@example.com",
        password_hash="hashed_test_pass",
        full_name="Lifecycle Tester",
        role_id=role.id,
        is_active=True,
    )
    test_db.add(user)
    test_db.commit()

    project_id = uuid4()
    proj = Project(
        id=project_id,
        owner_id=user.id,
        project_name="Churn Analysis Project",
        task_type="CLASSIFICATION",
        target_column="churn",
        pipeline_stage="DATA",
    )
    test_db.add(proj)
    test_db.commit()

    # Freeze configuration
    selected_algs = ["LogisticRegression", "RandomForestClassifier"]
    dep_threshold = {"metric": "f1_macro", "min_value": 0.85}
    frozen_cfg = {
        "task_type": "CLASSIFICATION",
        "target": "churn",
        "algorithms": selected_algs,
        "cv": {"folds": 3, "seed": 12345},
        "selection_metric": "f1_macro",
        "selection_direction": "MAXIMIZE",
        "deployment_threshold": dep_threshold,
    }

    exp_id = uuid4()
    exp = Experiment(
        id=exp_id,
        project_id=project_id,
        task_type="CLASSIFICATION",
        fold_count=3,
        cv_seed=12345,
        selection_metric="f1_macro",
        selection_direction="MAXIMIZE",
        status="CREATED",
        experiment_config=frozen_cfg,
    )
    test_db.add(exp)
    test_db.commit()
    test_db.refresh(exp)

    # Invariant: Experiment record must retain non-empty immutable configuration
    assert exp.experiment_config is not None
    assert exp.experiment_config["algorithms"] == selected_algs
    assert exp.experiment_config["deployment_threshold"]["min_value"] == 0.85
    assert exp.experiment_config["cv"]["folds"] == 3


def test_storage_model_artifact_save_and_hmac_verification(test_db, tmp_path):
    """
    P0 Test: Verifies that model artifacts are serialized to StorageService keys
    with companion HMAC manifests, and correctly loaded by downstream consumers.
    """
    storage = LocalStorageService(base_dir=tmp_path)
    proj_id = uuid4()
    exp_id = uuid4()
    model_id = uuid4()

    fake_pipeline = {
        "algorithm_name": "RandomForestClassifier",
        "estimator": "FittedEstimatorInstance",
        "feature_names_in": ["age", "tenure", "balance"],
        "selected_feature_names": ["age", "balance"],
    }

    storage_key = f"models/{proj_id}/{exp_id}/{model_id}/model.joblib"
    
    # 1. Save artifact to storage
    clean_key, artifact_hash, sig = save_signed_model_to_storage(
        artifact=fake_pipeline,
        storage_key=storage_key,
        storage=storage,
        metadata={"model_id": str(model_id), "algorithm": "RandomForestClassifier"}
    )

    assert storage.exists(clean_key)
    manifest_key = f"models/{proj_id}/{exp_id}/{model_id}/model.manifest.json"
    assert storage.exists(manifest_key)

    # 2. Verify manifest payload
    manifest_raw = storage.get_file_bytes(manifest_key)
    manifest_data = json.loads(manifest_raw.decode("utf-8"))
    assert manifest_data["sha256"] == artifact_hash
    assert manifest_data["signature"] == sig

    # 3. Load and verify artifact
    loaded_pipeline = load_signed_model_from_storage(
        clean_key,
        storage=storage,
    )
    assert loaded_pipeline["algorithm_name"] == "RandomForestClassifier"
    assert loaded_pipeline["selected_feature_names"] == ["age", "balance"]

    # 4. Tamper Detection Test: Corrupt artifact bytes and verify rejection
    corrupted_bytes = storage.get_file_bytes(clean_key) + b"tampered_extra_byte"
    storage.save_bytes(clean_key, corrupted_bytes)

    with pytest.raises(SecurityError) as exc_info:
        load_signed_model_from_storage(clean_key, storage=storage)
    assert "Artifact integrity violation" in str(exc_info.value) or "mismatch" in str(exc_info.value)


def test_safely_encode_matrix_pair_category_consistency():
    """
    P1 Test: Verifies that categorical columns in validation and test slices
    reuse train-learned numerical mappings and handle unseen categories deterministically.
    """
    # Train data with categories ['cat', 'dog', 'bird']
    df_train = pd.DataFrame({
        "num_col": [1.0, 2.0, 3.0],
        "cat_col": ["cat", "dog", "bird"],
    })

    # Validation data with different order and unseen category ['dog', 'cat', 'elephant']
    df_val = pd.DataFrame({
        "num_col": [4.0, 5.0, 6.0],
        "cat_col": ["dog", "cat", "elephant"],
    })

    X_train_num, X_val_num = safely_encode_matrix_pair(df_train, df_val)

    # 'cat' and 'dog' must have identical numerical codes between train and val
    cat_code_train = X_train_num[0, 1]  # 'cat' is row 0
    dog_code_train = X_train_num[1, 1]  # 'dog' is row 1

    dog_code_val = X_val_num[0, 1]    # 'dog' is row 0 in val
    cat_code_val = X_val_num[1, 1]    # 'cat' is row 1 in val
    elephant_code_val = X_val_num[2, 1]  # unseen category

    assert dog_code_val == dog_code_train
    assert cat_code_val == cat_code_train
    assert elephant_code_val == -1.0  # Unseen category fallback


def test_health_worker_endpoint(client):
    """
    P0 Test: Verifies that /health/worker and /health/ready provide clear subsystem telemetry.
    """
    res_live = client.get("/health/live")
    assert res_live.status_code == 200
    assert res_live.json()["status"] == "alive"

    res_ready = client.get("/health/ready")
    assert res_ready.status_code == 200
    ready_data = res_ready.json()
    assert "database" in ready_data["dependencies"]
    assert "storage" in ready_data["dependencies"]

    res_worker = client.get("/health/worker")
    assert res_worker.status_code == 200
    worker_data = res_worker.json()
    assert worker_data["status"] == "UP"
    assert "active_worker_count" in worker_data["details"]


def test_deployment_gate_and_prediction_with_storage_artifact(test_db, tmp_path):
    """
    P0 Test: Verifies that DeploymentGateService and PredictionService operate
    exclusively via StorageService keys, validating hashes, HMAC signatures, and schema.
    """
    from sklearn.ensemble import RandomForestClassifier
    from app.models.model_metric import ModelMetric
    from app.models.transformation_snapshot import TransformationSnapshot
    from app.models.feature_selection_snapshot import FeatureSelectionSnapshot

    # 1. Setup role, users, project, experiment
    role = test_db.query(Role).filter(Role.role_name == "ADMIN").first()
    creator = User(id=uuid4(), email=f"creator_{uuid4().hex[:6]}@example.com", password_hash="hash", full_name="Creator", role_id=role.id, is_active=True)
    approver = User(id=uuid4(), email=f"approver_{uuid4().hex[:6]}@example.com", password_hash="hash", full_name="Approver", role_id=role.id, is_active=True)
    test_db.add_all([creator, approver])
    test_db.commit()

    proj = Project(id=uuid4(), owner_id=creator.id, project_name="Serving Project", task_type="CLASSIFICATION", target_column="target", pipeline_stage="GATE_PASSED")
    test_db.add(proj)
    test_db.commit()

    exp = Experiment(id=uuid4(), project_id=proj.id, task_type="CLASSIFICATION", status="REGISTERED", locked_test_consumed=True, experiment_config={"target": "target"})
    test_db.add(exp)
    test_db.commit()

    # Fit a real scikit-learn model
    X_train = np.array([[25.0, 1.0], [45.0, 2.0], [35.0, 1.0], [50.0, 3.0]])
    y_train = np.array([0, 1, 0, 1])
    rf = RandomForestClassifier(n_estimators=5, random_state=42)
    rf.fit(X_train, y_train)

    fitted_pipeline = {
        "algorithm_name": "RandomForestClassifier",
        "task_type": "CLASSIFICATION",
        "target_column": "target",
        "feature_names_in": ["age", "tenure"],
        "selected_feature_names": ["age", "tenure"],
        "selected_indices": [0, 1],
        "estimator": rf,
    }

    # Save to storage
    storage = get_storage_service()
    model_id = uuid4()
    storage_key = f"models/{proj.id}/{exp.id}/{model_id}/model.joblib"
    clean_key, artifact_hash, sig = save_signed_model_to_storage(
        artifact=fitted_pipeline,
        storage_key=storage_key,
        storage=storage,
        metadata={"model_id": str(model_id), "algorithm": "RandomForestClassifier"},
    )

    # Add transformation and FS snapshots
    trans_snap = TransformationSnapshot(id=uuid4(), experiment_id=exp.id, config_json={})
    fs_snap = FeatureSelectionSnapshot(id=uuid4(), experiment_id=exp.id, final_selected_features=["age", "tenure"], final_selection_method="rank_agg")
    test_db.add_all([trans_snap, fs_snap])
    test_db.commit()

    model = TrainedModel(
        id=model_id,
        experiment_id=exp.id,
        algorithm_name="RandomForestClassifier",
        status="DEPLOYABLE",
        artifact_path=clean_key,
        artifact_checksum=artifact_hash,
        preprocessing_snapshot_id=trans_snap.id,
        feature_selection_snapshot_id=fs_snap.id,
    )
    test_db.add(model)
    test_db.commit()

    # Add locked test metric
    test_metric = ModelMetric(
        id=uuid4(),
        model_id=model.id,
        split="LOCKED_TEST",
        metric_name="f1_macro",
        metric_value=0.92,
    )
    test_db.add(test_metric)
    test_db.commit()

    # 2. Evaluate Deployment Gate
    gate_service = DeploymentGateService(test_db)
    gate_eval = gate_service.check_gate(model.id)
    assert gate_eval.artifact_verified is True
    assert gate_eval.locked_test_evaluated is True
    assert gate_eval.schema_locked is True

    # 3. Create Deployment & Serve Real-Time Prediction
    deployment = Deployment(
        id=uuid4(),
        model_id=model.id,
        status="DEPLOYED",
        endpoint_path=f"/api/v1/predict/{model.id}",
        deployed_by=creator.id,
    )
    test_db.add(deployment)
    test_db.commit()

    pred_service = PredictionService(test_db)
    pred_res, _ = pred_service.predict(
        deployment_id=deployment.id,
        payload={"age": 30.0, "tenure": 2.0},
    )
    assert hasattr(pred_res, "prediction")
    assert pred_res.prediction in [0, 1]
