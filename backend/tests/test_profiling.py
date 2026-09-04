import io
import pytest
import numpy as np
import pandas as pd
from uuid import UUID
from fastapi import status

from app.models.dataset import Dataset
from app.models.dataset_split import DatasetSplit
from app.models.project import Project
from app.models.profiling_report import ProfilingReport
from app.models.recommendation import Recommendation
from app.services.dataset_service import DatasetService
from app.services.dataset_split_service import DatasetSplitService
from app.services.data_profiling_service import DataProfilingService
from app.services.task_type_service import TaskTypeDetectionService
from app.services.diagnostics_service import DiagnosticsService

def get_auth_token(client, email="profiler@example.com", role_name="ML_ENGINEER"):
    reg_resp = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Test Profiler",
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

def create_sample_csv(rows: int = 100, target_type: str = "categorical") -> bytes:
    np.random.seed(42)
    feature_a = np.random.normal(loc=50, scale=15, size=rows)
    # Add a few intentional outliers in feature_a
    feature_a[0] = 500.0
    feature_a[1] = -300.0

    feature_b = np.random.exponential(scale=10, size=rows)
    cat_feature = np.random.choice(["Red", "Blue", "Green"], size=rows)

    if target_type == "categorical":
        target = np.random.choice(["Class_A", "Class_B", "Class_C"], size=rows)
    elif target_type == "continuous":
        target = np.random.normal(loc=1000, scale=250, size=rows)
    elif target_type == "ambiguous":
        # 15 unique integer values across rows
        target = np.random.choice(range(1, 16), size=rows)
    elif target_type == "all_categorical":
        # No numeric columns at all
        df = pd.DataFrame({
            "color": np.random.choice(["Red", "Blue", "Green"], size=rows),
            "size": np.random.choice(["Small", "Medium", "Large"], size=rows),
            "label": np.random.choice(["Yes", "No"], size=rows),
        })
        return df.to_csv(index=False).encode("utf-8")
    else:
        target = np.random.choice(["A", "B"], size=rows)

    df = pd.DataFrame({
        "feature_a": feature_a,
        "feature_b": feature_b,
        "cat_feature": cat_feature,
        "target": target
    })

    # Add some null values to test missingness calculation
    df.loc[10:15, "feature_b"] = np.nan
    # Add 2 duplicate rows to test duplicate calculation
    df.iloc[5] = df.iloc[4]
    df.iloc[6] = df.iloc[4]

    return df.to_csv(index=False).encode("utf-8")


def test_acceptance_a_adversarial_locked_test_isolation(db_session, create_test_user):
    """
    Acceptance Check a:
    Adversarial test asserting zero overlap between Development row indices used in profiling
    and Locked Test partition row indices.
    """
    test_user = create_test_user(email="user_a@example.com")

    # 1. Setup project & dataset
    project = Project(
        owner_id=test_user.id,
        project_name="Adversarial Profiling Test",
        target_column="target"
    )
    db_session.add(project)
    db_session.commit()

    csv_bytes = create_sample_csv(rows=120, target_type="categorical")
    dataset_service = DatasetService(db_session)
    dataset = dataset_service.upload(
        project_id=project.id,
        filename="adversarial_test.csv",
        content=csv_bytes,
        uploaded_by_id=test_user.id
    )
    dataset_service.detect_structural_schema(dataset.id)

    # 2. Perform outer split (70% Dev, 30% Locked Test)
    split_service = DatasetSplitService(db_session)
    split_info = split_service.create_outer_split(dataset.id, locked_test_pct=30, seed=12345)

    # 3. Retrieve locked test indices directly from database
    locked_split = (
        db_session.query(DatasetSplit)
        .filter(DatasetSplit.dataset_id == dataset.id, DatasetSplit.split_type == "LOCKED_TEST")
        .first()
    )
    assert locked_split is not None
    locked_test_indices = set(locked_split.row_indices)
    assert len(locked_test_indices) == split_info["locked_test_rows"]

    # 4. Run profiling service
    profiling_service = DataProfilingService(db_session)
    report = profiling_service.generate_report(dataset.id)

    # 5. Retrieve Development partition DataFrame
    dev_split = (
        db_session.query(DatasetSplit)
        .filter(DatasetSplit.dataset_id == dataset.id, DatasetSplit.split_type == "DEVELOPMENT")
        .first()
    )
    dev_indices = set(dev_split.row_indices)

    # ASSERTION: Zero overlap between Development indices used for profiling and Locked Test indices
    overlap = dev_indices.intersection(locked_test_indices)
    assert len(overlap) == 0, f"DATA LEAKAGE DETECTED! Overlapping row indices: {overlap}"

    # Verify report is linked strictly to dev_split.id
    assert report["dataset_split_id"] == str(dev_split.id)
    assert report["total_rows"] == len(dev_indices)
    assert report["data_quality_index"]["overall_index"] > 0


def test_acceptance_b_missing_split_guard(client, db_session, create_test_user):
    """
    Acceptance Check b:
    Calling POST /profile on a dataset with no split yet returns a clear 422 error,
    not a crash or silent full-dataset profile.
    """
    test_user = create_test_user(email="user_b@example.com")
    token = get_auth_token(client, email="user_b_api@example.com")
    auth_headers = {"Authorization": f"Bearer {token}"}

    # Create project via API
    proj_resp = client.post(
        "/api/v1/projects",
        json={"project_name": "Unsplit Project Test", "target_column": "target"},
        headers=auth_headers
    )
    assert proj_resp.status_code == 201
    proj_id = proj_resp.json()["id"]

    # Upload dataset via API
    csv_bytes = create_sample_csv(rows=50, target_type="categorical")
    upload_resp = client.post(
        f"/api/v1/projects/{proj_id}/datasets",
        files={"file": ("unsplit.csv", io.BytesIO(csv_bytes), "text/csv")},
        headers=auth_headers
    )
    assert upload_resp.status_code == 201
    dataset_id = upload_resp.json()["id"]

    # Trigger profiling WITHOUT creating a split first
    resp = client.post(
        f"/api/v1/datasets/{dataset_id}/profile",
        headers=auth_headers
    )
    assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    data = resp.json()
    assert "outer split" in data["detail"].lower() or "split" in data["detail"].lower()


def test_acceptance_c_dqi_no_numeric_columns_renormalization(db_session, create_test_user):
    """
    Acceptance Check c:
    Profile a dataset with NO numeric columns.
    Assert Outlier Prevalence is reported as null/None, and the remaining 3 weights
    renormalize to sum to 100% (Missingness 43.75%, Duplicate 31.25%, Type Consistency 25.0%).
    """
    test_user = create_test_user(email="user_c@example.com")

    project = Project(
        owner_id=test_user.id,
        project_name="Non Numeric DQI Test",
        target_column="label"
    )
    db_session.add(project)
    db_session.commit()

    csv_bytes = create_sample_csv(rows=80, target_type="all_categorical")
    dataset_service = DatasetService(db_session)
    dataset = dataset_service.upload(
        project_id=project.id,
        filename="all_categorical.csv",
        content=csv_bytes,
        uploaded_by_id=test_user.id
    )
    dataset_service.detect_structural_schema(dataset.id)

    split_service = DatasetSplitService(db_session)
    split_service.create_outer_split(dataset.id, locked_test_pct=25, seed=42)

    profiling_service = DataProfilingService(db_session)
    report = profiling_service.generate_report(dataset.id)
    dqi = report["data_quality_index"]

    # Assert sub_scores
    sub_scores = dqi["sub_scores"]
    assert sub_scores["outlier_prevalence"] is None
    assert sub_scores["missingness"] == 100.0
    assert sub_scores["duplicate_rate"] >= 0.0
    assert sub_scores["type_consistency"] == 100.0

    # Assert effective weights renormalization
    eff_weights = dqi["effective_weights"]
    assert eff_weights["outlier_prevalence"] is None
    # Default weights: Missingness 0.35, Duplicate 0.25, Outlier 0.20, Type Consistency 0.20
    # Renormalized: sum = 0.80
    # Missingness: 0.35 / 0.80 = 0.4375
    # Duplicate: 0.25 / 0.80 = 0.3125
    # Type Consistency: 0.20 / 0.80 = 0.2500
    assert pytest.approx(eff_weights["missingness"], 0.0001) == 0.4375
    assert pytest.approx(eff_weights["duplicate_rate"], 0.0001) == 0.3125
    assert pytest.approx(eff_weights["type_consistency"], 0.0001) == 0.2500

    # Total active effective weights must sum exactly to 1.0 (100%)
    active_weights_sum = (
        eff_weights["missingness"] +
        eff_weights["duplicate_rate"] +
        eff_weights["type_consistency"]
    )
    assert pytest.approx(active_weights_sum, 0.0001) == 1.0

    # Overall index must equal weighted average of the 3 active sub-scores
    expected_overall = round(
        sub_scores["missingness"] * 0.4375 +
        sub_scores["duplicate_rate"] * 0.3125 +
        sub_scores["type_consistency"] * 0.2500,
        2
    )
    assert pytest.approx(dqi["overall_index"], 0.01) == expected_overall


def test_acceptance_d_task_type_detection_synthetic_targets(db_session, create_test_user):
    """
    Acceptance Check d:
    Test task-type detection against three synthetic targets:
    1. Obviously categorical (string labels) -> CLASSIFICATION (HIGH)
    2. Obviously continuous (float values) -> REGRESSION (HIGH)
    3. Deliberately constructed AMBIGUOUS target -> blocks auto-selection, keeps UNDETERMINED.
    """
    test_user = create_test_user(email="user_d@example.com")
    dataset_service = DatasetService(db_session)
    split_service = DatasetSplitService(db_session)
    task_service = TaskTypeDetectionService(db_session)

    # 1. Target 1: Obviously Categorical (string labels)
    proj_cat = Project(owner_id=test_user.id, project_name="Target Categorical", target_column="target")
    db_session.add(proj_cat)
    db_session.commit()

    ds_cat = dataset_service.upload(
        project_id=proj_cat.id,
        filename="cat_target.csv",
        content=create_sample_csv(rows=100, target_type="categorical"),
        uploaded_by_id=test_user.id
    )
    dataset_service.detect_structural_schema(ds_cat.id)
    split_service.create_outer_split(ds_cat.id, locked_test_pct=20, seed=42)

    res_cat = task_service.suggest_task_type(ds_cat.id)
    assert res_cat["suggested_task_type"] == "CLASSIFICATION"
    assert res_cat["confidence"] == "HIGH"
    db_session.refresh(proj_cat)
    assert proj_cat.task_type == "CLASSIFICATION"
    assert proj_cat.task_type_confidence == "HIGH"

    # 2. Target 2: Obviously Continuous (float numbers)
    proj_reg = Project(owner_id=test_user.id, project_name="Target Continuous", target_column="target")
    db_session.add(proj_reg)
    db_session.commit()

    ds_reg = dataset_service.upload(
        project_id=proj_reg.id,
        filename="reg_target.csv",
        content=create_sample_csv(rows=100, target_type="continuous"),
        uploaded_by_id=test_user.id
    )
    dataset_service.detect_structural_schema(ds_reg.id)
    split_service.create_outer_split(ds_reg.id, locked_test_pct=20, seed=42)

    res_reg = task_service.suggest_task_type(ds_reg.id)
    assert res_reg["suggested_task_type"] == "REGRESSION"
    assert res_reg["confidence"] == "HIGH"
    db_session.refresh(proj_reg)
    assert proj_reg.task_type == "REGRESSION"
    assert proj_reg.task_type_confidence == "HIGH"

    # 3. Target 3: Deliberately Ambiguous (15 unique integers in 50 rows -> unique_ratio=0.30)
    # unique_count <= 20 but unique_ratio >= 0.05 -> violates rule 2a and rule 2b -> Rule 2c AMBIGUOUS
    proj_amb = Project(owner_id=test_user.id, project_name="Target Ambiguous", target_column="target")
    db_session.add(proj_amb)
    db_session.commit()

    ds_amb = dataset_service.upload(
        project_id=proj_amb.id,
        filename="amb_target.csv",
        content=create_sample_csv(rows=50, target_type="ambiguous"),
        uploaded_by_id=test_user.id
    )
    dataset_service.detect_structural_schema(ds_amb.id)
    split_service.create_outer_split(ds_amb.id, locked_test_pct=20, seed=42)

    res_amb = task_service.suggest_task_type(ds_amb.id)
    assert res_amb["suggested_task_type"] == "UNDETERMINED"
    assert res_amb["confidence"] == "AMBIGUOUS"
    assert res_amb["is_ambiguous"] is True
    assert res_amb["unique_count"] <= 20
    assert res_amb["unique_ratio"] >= 0.05
    assert len(res_amb["sample_values"]) > 0

    # Project task_type MUST remain UNDETERMINED
    db_session.refresh(proj_amb)
    assert proj_amb.task_type == "UNDETERMINED"
    assert proj_amb.task_type_confidence == "AMBIGUOUS"


def test_diagnostics_five_field_recommendations(db_session, create_test_user):
    """
    Verifies that all generated recommendation rows contain all 5 non-empty fields:
    finding, evidence, recommended_action, risk_note, confidence.
    """
    test_user = create_test_user(email="user_diag@example.com")

    project = Project(
        owner_id=test_user.id,
        project_name="Diagnostics Recommendations Test",
        target_column="target"
    )
    db_session.add(project)
    db_session.commit()

    csv_bytes = create_sample_csv(rows=100, target_type="categorical")
    dataset_service = DatasetService(db_session)
    dataset = dataset_service.upload(
        project_id=project.id,
        filename="diag_test.csv",
        content=csv_bytes,
        uploaded_by_id=test_user.id
    )
    dataset_service.detect_structural_schema(dataset.id)

    split_service = DatasetSplitService(db_session)
    split_service.create_outer_split(dataset.id, locked_test_pct=20, seed=42)

    profiling_service = DataProfilingService(db_session)
    report = profiling_service.generate_report(dataset.id)

    # Check persisted recommendations in DB
    recs = db_session.query(Recommendation).filter(Recommendation.project_id == project.id).all()
    assert len(recs) > 0

    for rec in recs:
        assert rec.finding is not None and len(rec.finding.strip()) > 0
        assert rec.evidence is not None and len(rec.evidence.strip()) > 0
        assert rec.recommended_action is not None and len(rec.recommended_action.strip()) > 0
        assert rec.risk_note is not None and len(rec.risk_note.strip()) > 0
        assert rec.confidence in ["HIGH", "MEDIUM", "LOW"]
        assert rec.status == "SUGGESTED"


def test_profiling_api_endpoints_full_lifecycle(client, db_session, create_test_user):
    """
    Full end-to-end API lifecycle test:
    1. POST /datasets/{id}/profile
    2. GET /datasets/{id}/profile
    3. GET /projects/{id}/recommendations
    4. PUT /projects/{id}/task-type
    """
    token = get_auth_token(client, email="lifecycle@example.com")
    auth_headers = {"Authorization": f"Bearer {token}"}

    # Create project via API
    proj_resp = client.post(
        "/api/v1/projects",
        json={"project_name": "API Lifecycle Profiling Test", "target_column": "target"},
        headers=auth_headers
    )
    assert proj_resp.status_code == 201
    proj_id = proj_resp.json()["id"]

    # Upload dataset via API
    csv_bytes = create_sample_csv(rows=100, target_type="categorical")
    upload_resp = client.post(
        f"/api/v1/projects/{proj_id}/datasets",
        files={"file": ("api_test.csv", io.BytesIO(csv_bytes), "text/csv")},
        headers=auth_headers
    )
    assert upload_resp.status_code == 201
    dataset_id = upload_resp.json()["id"]

    # Create split
    split_resp = client.post(
        f"/api/v1/datasets/{dataset_id}/split",
        json={"locked_test_pct": 20, "seed": 42},
        headers=auth_headers
    )
    assert split_resp.status_code == 201

    # 1. Trigger profiling
    post_resp = client.post(
        f"/api/v1/datasets/{dataset_id}/profile",
        headers=auth_headers
    )
    assert post_resp.status_code == status.HTTP_200_OK
    post_data = post_resp.json()
    assert "data_quality_index" in post_data
    assert "column_stats" in post_data
    assert "correlation_matrix" in post_data

    # 2. Retrieve profiling report
    get_resp = client.get(
        f"/api/v1/datasets/{dataset_id}/profile",
        headers=auth_headers
    )
    assert get_resp.status_code == status.HTTP_200_OK
    get_data = get_resp.json()
    assert get_data["dataset_id"] == str(dataset_id)

    # 3. Retrieve recommendations
    recs_resp = client.get(
        f"/api/v1/projects/{proj_id}/recommendations",
        headers=auth_headers
    )
    assert recs_resp.status_code == status.HTTP_200_OK
    recs_data = recs_resp.json()
    assert isinstance(recs_data, list)
    assert len(recs_data) > 0
    first_rec = recs_data[0]
    for key in ["finding", "evidence", "recommended_action", "risk_note", "confidence"]:
        assert key in first_rec

    # 4. User task-type manual confirmation / override
    put_resp = client.put(
        f"/api/v1/projects/{proj_id}/task-type",
        json={"task_type": "REGRESSION"},
        headers=auth_headers
    )
    assert put_resp.status_code == status.HTTP_200_OK
    put_data = put_resp.json()
    assert put_data["task_type"] == "REGRESSION"
    assert put_data["task_type_confidence"] == "MANUAL"

    # Confirm project pipeline stage was updated to PROFILED
    proj_resp = client.get(f"/api/v1/projects/{proj_id}", headers=auth_headers)
    assert proj_resp.status_code == status.HTTP_200_OK
    assert proj_resp.json()["pipeline_stage"] == "PROFILED"
