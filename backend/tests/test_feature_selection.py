import io
import uuid
import pytest
import numpy as np
import pandas as pd
from fastapi import status

from app.models.dataset import Dataset
from app.models.dataset_split import DatasetSplit
from app.models.experiment import Experiment
from app.models.feature_selection_fold_result import FeatureSelectionFoldResult
from app.models.feature_importance_score import FeatureImportanceScore
from app.models.project import Project
from app.models.user import User
from app.models.role import Role
from app.services.dataset_service import DatasetService
from app.services.dataset_split_service import DatasetSplitService
from app.services.feature_selection_service import FeatureSelectionService
from app.services.transformation_service import TransformationService

def get_auth_token(client, email="engineer@example.com", role_name="ML_ENGINEER"):
    reg_resp = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Test User",
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

def create_synthetic_dataset_bytes(n_samples: int = 120, task: str = "classification") -> bytes:
    np.random.seed(42)
    x1 = np.random.normal(0, 1, n_samples)
    x2 = 2.0 * x1 + np.random.normal(0, 0.5, n_samples)  # strongly correlated with x1
    x3 = np.random.uniform(10, 50, n_samples)             # moderately informative
    x4 = np.random.normal(100, 20, n_samples)            # pure noise
    
    category = np.random.choice(["TypeA", "TypeB", "TypeC"], size=n_samples)

    if task == "classification":
        # Binary target determined by x1 + x2
        logits = 1.5 * x1 + 0.8 * x2 + np.random.normal(0, 0.5, n_samples)
        target = (logits > np.median(logits)).astype(int)
    else:
        # Continuous regression target
        target = 3.0 * x1 + 2.0 * x2 + 0.5 * x3 + np.random.normal(0, 1.0, n_samples)

    df = pd.DataFrame({
        "feat_strong1": x1,
        "feat_strong2": x2,
        "feat_moderate": x3,
        "feat_noise": x4,
        "category_col": category,
        "target": target,
    })
    
    buf = io.BytesIO()
    df.to_csv(buf, index=False)
    buf.seek(0)
    return buf.getvalue()


# =============================================================================
# 1. Mathematical Rank Aggregation Engine Tests (SRS §2.7)
# =============================================================================

def test_rank_aggregation_single_feature():
    """
    SRS §2.7: p = 1 -> rank score = 1 (avoids p - 1 = 0 division error).
    """
    raw_scores = np.array([42.5])
    ranks, norm_scores = FeatureSelectionService.calculate_technique_rank_scores(raw_scores)
    assert len(ranks) == 1
    assert ranks[0] == 1.0
    assert norm_scores[0] == 1.0


def test_rank_aggregation_ties_average_ranking():
    """
    SRS §2.7: Ties receive average rank.
    Example: scores [10, 10, 5] -> ranks [1.5, 1.5, 3.0]
    Normalized scores for p=3:
    r_j = 1 - (rank - 1) / (3 - 1)
    rank 1.5 -> 1 - 0.5 / 2 = 0.75
    rank 3.0 -> 1 - 2.0 / 2 = 0.0
    """
    raw_scores = np.array([10.0, 10.0, 5.0])
    ranks, norm_scores = FeatureSelectionService.calculate_technique_rank_scores(raw_scores)
    
    np.testing.assert_array_almost_equal(ranks, [1.5, 1.5, 3.0])
    np.testing.assert_array_almost_equal(norm_scores, [0.75, 0.75, 0.0])


def test_rank_aggregation_fold_with_skipped_technique():
    """
    SRS §2.7: EnsembleScore_j = (1 / T_applied) * sum_{T in Applied} r_{j,T}.
    Techniques with SKIPPED or FAILED status must NOT dilute T_applied.
    """
    feature_names = ["feat1", "feat2", "feat3"]
    technique_results = {
        "Correlation": {
            "status": "APPLIED",
            "raw_scores": np.array([0.9, 0.5, 0.1]),
            "status_reason": None,
        },
        "Lasso": {
            "status": "SKIPPED",
            "raw_scores": None,
            "status_reason": "Skipped due to single sample",
        },
        "Random Forest": {
            "status": "APPLIED",
            "raw_scores": np.array([0.8, 0.4, 0.2]),
            "status_reason": None,
        },
        "Permutation": {
            "status": "FAILED",
            "raw_scores": None,
            "status_reason": "Convergence error",
        },
    }

    payload, ensemble = FeatureSelectionService.aggregate_technique_scores_for_fold(
        feature_names, technique_results
    )

    assert payload["Correlation"]["feat1"]["status"] == "APPLIED"
    assert payload["Lasso"]["feat1"]["status"] == "SKIPPED"
    assert payload["Lasso"]["feat1"]["status_reason"] == "Skipped due to single sample"
    assert payload["Permutation"]["feat1"]["status"] == "FAILED"
    
    # T_applied = 2 (Correlation + Random Forest)
    # Correlation ranks: feat1=1 (1.0), feat2=2 (0.5), feat3=3 (0.0)
    # Random Forest ranks: feat1=1 (1.0), feat2=2 (0.5), feat3=3 (0.0)
    # Ensemble: feat1 = (1.0 + 1.0)/2 = 1.0, feat2 = (0.5 + 0.5)/2 = 0.5, feat3 = (0.0 + 0.0)/2 = 0.0
    assert ensemble["feat1"] == 1.0
    assert ensemble["feat2"] == 0.5
    assert ensemble["feat3"] == 0.0


# =============================================================================
# 2. Technique Selectors Tests
# =============================================================================

def test_four_selectors_classification():
    np.random.seed(42)
    n, p = 80, 4
    X = np.random.normal(0, 1, (n, p))
    # y strongly correlated with column 0 and 1
    y = (X[:, 0] * 2.0 + X[:, 1] * 1.5 + np.random.normal(0, 0.3, n) > 0).astype(int)

    # 1. Correlation
    corr = FeatureSelectionService.compute_correlation_scores(X, y, "CLASSIFICATION")
    assert len(corr) == p
    assert corr[0] > corr[3]  # col 0 more important than noise col 3

    # 2. Lasso
    lasso = FeatureSelectionService.compute_lasso_scores(X, y, "CLASSIFICATION", seed=42)
    assert len(lasso) == p
    assert lasso[0] > lasso[3]

    # 3. Random Forest
    rf = FeatureSelectionService.compute_random_forest_scores(X, y, "CLASSIFICATION", seed=42)
    assert len(rf) == p
    assert rf[0] > rf[3]

    # 4. Permutation
    perm = FeatureSelectionService.compute_permutation_scores(X, y, "CLASSIFICATION", seed=42)
    assert len(perm) == p
    assert perm[0] >= 0.0


def test_four_selectors_regression():
    np.random.seed(42)
    n, p = 80, 4
    X = np.random.normal(0, 1, (n, p))
    # y continuous regression target
    y = X[:, 0] * 3.0 + X[:, 1] * 2.0 + np.random.normal(0, 0.5, n)

    corr = FeatureSelectionService.compute_correlation_scores(X, y, "REGRESSION")
    assert len(corr) == p
    assert corr[0] > corr[3]

    lasso = FeatureSelectionService.compute_lasso_scores(X, y, "REGRESSION", seed=42)
    assert len(lasso) == p
    assert lasso[0] > lasso[3]

    rf = FeatureSelectionService.compute_random_forest_scores(X, y, "REGRESSION", seed=42)
    assert len(rf) == p
    assert rf[0] > rf[3]

    perm = FeatureSelectionService.compute_permutation_scores(X, y, "REGRESSION", seed=42)
    assert len(perm) == p
    assert perm[0] > perm[3]


# =============================================================================
# 3. CV Harness & Invariant 1 / 2 (Zero Leakage) Integration Tests
# =============================================================================

def test_cv_feature_selection_classification_end_to_end(db_session):
    role = db_session.query(Role).filter(Role.role_name == "ML_ENGINEER").first()
    user = User(
        id=uuid.uuid4(),
        full_name="ML Dev",
        email="mldev@test.com",
        password_hash="fake",
        role_id=role.id,
    )
    db_session.add(user)
    
    project = Project(
        id=uuid.uuid4(),
        owner_id=user.id,
        project_name="Classification Project",
        task_type="CLASSIFICATION",
        target_column="target",
        pipeline_stage="TRANSFORMED",
    )
    db_session.add(project)
    db_session.commit()

    # Upload dataset and perform outer split
    csv_bytes = create_synthetic_dataset_bytes(100, task="classification")
    ds_service = DatasetService(db_session)
    dataset = ds_service.upload(project.id, "customers.csv", csv_bytes, uploaded_by_id=user.id)
    ds_service.detect_structural_schema(dataset.id)

    split_service = DatasetSplitService(db_session)
    split_service.create_outer_split(dataset.id, locked_test_pct=20, seed=42)

    # Configure categorical encoding
    trans_service = TransformationService(db_session)
    trans_service.set_encoding_strategy(project.id, "category_col", "one_hot")

    # Run CV Feature Selection
    fs_service = FeatureSelectionService(db_session)
    result = fs_service.run_cv_feature_selection(
        project_id=project.id,
        n_splits=5,
        cv_strategy="STRATIFIED_KFOLD",
        seed=42,
        threshold=0.3,
    )

    assert result["status"] == "COMPLETED"
    assert result["fold_count"] == 5
    assert len(result["features"]) > 0

    # Verify Experiment record created
    exp = db_session.query(Experiment).filter(Experiment.id == result["experiment_id"]).first()
    assert exp is not None
    assert exp.status == "COMPLETED"
    assert exp.completed_at is not None

    # Verify 5 Fold Results stored
    folds = db_session.query(FeatureSelectionFoldResult).filter(
        FeatureSelectionFoldResult.experiment_id == exp.id
    ).all()
    assert len(folds) == 5
    for fold in folds:
        assert 0 <= fold.fold_index < 5
        assert len(fold.selected_features) > 0
        assert "Correlation" in fold.technique_scores
        assert "Lasso" in fold.technique_scores
        assert "Random Forest" in fold.technique_scores
        assert "Permutation" in fold.technique_scores

    # Verify Live FeatureImportanceScore table populated
    scores = db_session.query(FeatureImportanceScore).filter(
        FeatureImportanceScore.project_id == project.id
    ).all()
    assert len(scores) > 0
    # Informative feature should have higher rank score than noise
    score_map = {s.column_name: float(s.avg_rank_score) for s in scores}
    assert score_map.get("feat_strong1", 0.0) > score_map.get("feat_noise", 0.0)

    # Verify Project Stage transitioned to FEATURE_SELECTED
    db_session.refresh(project)
    assert project.pipeline_stage == "FEATURE_SELECTED"


def test_cv_feature_selection_regression_end_to_end(db_session):
    role = db_session.query(Role).filter(Role.role_name == "ML_ENGINEER").first()
    user = User(
        id=uuid.uuid4(),
        full_name="ML Dev Reg",
        email="mldev_reg@test.com",
        password_hash="fake",
        role_id=role.id,
    )
    db_session.add(user)

    project = Project(
        id=uuid.uuid4(),
        owner_id=user.id,
        project_name="Regression Project",
        task_type="REGRESSION",
        target_column="target",
        pipeline_stage="TRANSFORMED",
    )
    db_session.add(project)
    db_session.commit()

    csv_bytes = create_synthetic_dataset_bytes(80, task="regression")
    ds_service = DatasetService(db_session)
    dataset = ds_service.upload(project.id, "housing.csv", csv_bytes, uploaded_by_id=user.id)
    ds_service.detect_structural_schema(dataset.id)

    split_service = DatasetSplitService(db_session)
    split_service.create_outer_split(dataset.id, locked_test_pct=20, seed=42)

    fs_service = FeatureSelectionService(db_session)
    result = fs_service.run_cv_feature_selection(
        project_id=project.id,
        n_splits=3,
        cv_strategy="KFOLD",
        seed=123,
    )

    assert result["status"] == "COMPLETED"
    assert result["fold_count"] == 3


# =============================================================================
# 4. Live Threshold & Selection Update Tests
# =============================================================================

def test_feature_selection_threshold_updates(db_session):
    role = db_session.query(Role).filter(Role.role_name == "ML_ENGINEER").first()
    user = User(
        id=uuid.uuid4(),
        full_name="ML User",
        email="user_thresh@test.com",
        password_hash="fake",
        role_id=role.id,
    )
    db_session.add(user)
    project = Project(id=uuid.uuid4(), owner_id=user.id, project_name="Threshold Test")
    db_session.add(project)
    db_session.commit()

    fs_service = FeatureSelectionService(db_session)
    fs_service.importance_repo.upsert_scores(
        project.id,
        {"feat_a": 0.95, "feat_b": 0.60, "feat_c": 0.20},
    )

    # 1. Update by numeric threshold = 0.50
    res = fs_service.update_feature_selection(project.id, threshold=0.50)
    feat_map = {f["column_name"]: f["is_selected"] for f in res["features"]}
    assert feat_map["feat_a"] is True
    assert feat_map["feat_b"] is True
    assert feat_map["feat_c"] is False

    # 2. Update by explicit column selection
    res2 = fs_service.update_feature_selection(
        project.id, selected_features=["feat_a", "feat_c"]
    )
    feat_map2 = {f["column_name"]: f["is_selected"] for f in res2["features"]}
    assert feat_map2["feat_a"] is True
    assert feat_map2["feat_b"] is False
    assert feat_map2["feat_c"] is True


# =============================================================================
# 5. API Endpoints & RBAC Permissions
# =============================================================================

def test_api_feature_selection_endpoints(client):
    token = get_auth_token(client, email="mle@studio.com", role_name="ML_ENGINEER")
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Create project
    proj_resp = client.post(
        "/api/v1/projects",
        headers=headers,
        json={"project_name": "API FS Project"},
    )
    assert proj_resp.status_code == 201
    project_id = proj_resp.json()["id"]

    # 2. Upload dataset & split
    csv_bytes = create_synthetic_dataset_bytes(100, task="classification")
    files = {"file": ("dataset.csv", io.BytesIO(csv_bytes), "text/csv")}
    upload_resp = client.post(f"/api/v1/projects/{project_id}/datasets", headers=headers, files=files)
    assert upload_resp.status_code == 201
    dataset_id = upload_resp.json()["id"]

    split_resp = client.post(
        f"/api/v1/datasets/{dataset_id}/split",
        headers=headers,
        json={"test_percentage": 20.0, "seed": 42},
    )
    assert split_resp.status_code == 201

    # 3. Set target column & task type
    patch_resp = client.put(
        f"/api/v1/projects/{project_id}",
        headers=headers,
        json={"task_type": "CLASSIFICATION", "target_column": "target"},
    )
    assert patch_resp.status_code == 200
    assert patch_resp.status_code == 200

    # 4. Run CV feature selection via API (requires TRAIN permission)
    run_resp = client.post(
        f"/api/v1/projects/{project_id}/feature-selection/run",
        headers=headers,
        json={"n_splits": 5, "seed": 42, "threshold": 0.25},
    )
    assert run_resp.status_code == 200
    run_data = run_resp.json()
    assert run_data["project_id"] == project_id
    assert "experiment_id" in run_data
    experiment_id = run_data["experiment_id"]

    # 5. Fetch feature importance scores (requires READ permission)
    scores_resp = client.get(
        f"/api/v1/projects/{project_id}/feature-importance",
        headers=headers,
    )
    assert scores_resp.status_code == 200
    scores_data = scores_resp.json()
    assert len(scores_data["features"]) > 0

    # 6. Fetch fold results for the experiment
    folds_resp = client.get(
        f"/api/v1/projects/{project_id}/experiments/{experiment_id}/folds",
        headers=headers,
    )
    assert folds_resp.status_code == 200
    folds_data = folds_resp.json()
    assert folds_data["fold_count"] == 5
    assert len(folds_data["folds"]) == 5

    # 7. Update threshold via API (requires EDIT_DATA permission)
    thresh_resp = client.put(
        f"/api/v1/projects/{project_id}/feature-selection/threshold",
        headers=headers,
        json={"threshold": 0.8},
    )
    assert thresh_resp.status_code == 200


def test_api_feature_selection_viewer_cannot_run(client):
    viewer_token = get_auth_token(client, email="viewer@studio.com", role_name="VIEWER")
    headers = {"Authorization": f"Bearer {viewer_token}"}

    # VIEWER lacks TRAIN permission -> should receive 403 Forbidden
    dummy_id = uuid.uuid4()
    resp = client.post(
        f"/api/v1/projects/{dummy_id}/feature-selection/run",
        headers=headers,
        json={"n_splits": 5},
    )
    assert resp.status_code == status.HTTP_403_FORBIDDEN


def test_cv_feature_selection_multiclass_and_zero_variance(db_session):
    """
    Test multiclass classification string targets with a zero-variance feature column.
    """
    role = db_session.query(Role).filter(Role.role_name == "ML_ENGINEER").first()
    user = User(
        id=uuid.uuid4(),
        full_name="Multiclass Dev",
        email="multiclass@test.com",
        password_hash="fake",
        role_id=role.id,
    )
    db_session.add(user)

    project = Project(
        id=uuid.uuid4(),
        owner_id=user.id,
        project_name="Multiclass Project",
        task_type="CLASSIFICATION",
        target_column="species",
        pipeline_stage="TRANSFORMED",
    )
    db_session.add(project)
    db_session.commit()

    np.random.seed(99)
    n_samples = 90
    df = pd.DataFrame({
        "feat_informative": np.random.normal(0, 1, n_samples),
        "feat_zero_var": np.ones(n_samples),  # constant zero variance
        "feat_noise": np.random.uniform(0, 10, n_samples),
        "species": np.random.choice(["setosa", "versicolor", "virginica"], size=n_samples),
    })
    buf = io.BytesIO()
    df.to_csv(buf, index=False)
    buf.seek(0)

    ds_service = DatasetService(db_session)
    dataset = ds_service.upload(project.id, "iris.csv", buf.getvalue(), uploaded_by_id=user.id)
    ds_service.detect_structural_schema(dataset.id)

    split_service = DatasetSplitService(db_session)
    split_service.create_outer_split(dataset.id, locked_test_pct=20, seed=42)

    fs_service = FeatureSelectionService(db_session)
    result = fs_service.run_cv_feature_selection(
        project_id=project.id,
        n_splits=3,
        cv_strategy="STRATIFIED_KFOLD",
        seed=42,
    )

    assert result["status"] == "COMPLETED"
    assert result["fold_count"] == 3
    # feat_zero_var should have lowest rank score
    scores = {f["column_name"]: f["avg_rank_score"] for f in result["features"]}
    assert scores["feat_zero_var"] <= scores["feat_informative"]

