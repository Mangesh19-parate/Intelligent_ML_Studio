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


def test_dqi_subscores_handcrafted_calculations(db_session):
    """
    Direct unit test verifying exact mathematical computations for:
    - Missingness sub-score (35% weight)
    - Duplicate Rate sub-score (25% weight)
    - Outlier Prevalence sub-score (20% weight)
    - Type Consistency sub-score (20% weight)
    - Overall DQI weighted sum and effective weights structure.
    """
    profiling_service = DataProfilingService(db_session)

    # Construct handcrafted DataFrame: 20 rows, 5 columns (100 total cells)
    # Column A: 20 numeric values (normal with 2 extreme outliers: index 0 and index 19)
    # Column B: 20 numeric values (clean normal, 0 outliers)
    # Total numeric cells = 40. Outlier cells = 2. Outlier rate = 2/40 = 5%. Outlier score = 95.0
    # Column C: Categorical string column
    # Column D: Mixed type column (numbers + strings) -> 1 mixed column out of 5 columns = 20% mixed -> Type consistency = 80.0
    # Column E: Categorical string column
    # Missing cells: 10 missing cells across the 100 cells -> 10% missing -> Missingness score = 90.0
    # Duplicate rows: rows 2, 3, 4 are identical to row 1 (3 duplicate rows out of 20 = 15% dups) -> Duplicate score = 85.0

    col_a = [1000.0] + [50.0] * 18 + [-1000.0] # 2 outliers
    col_b = [10.0 + i for i in range(20)]        # 0 outliers
    col_c = ["Category_A"] * 20
    col_d = [1, 2, "three", "four", 5, 6, "seven", 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20] # mixed
    col_e = ["Alpha"] * 20

    df = pd.DataFrame({
        "num_a": col_a,
        "num_b": col_b,
        "cat_c": col_c,
        "mixed_d": col_d,
        "cat_e": col_e,
    })

    # Introduce duplicates: rows 2, 3, 4 duplicate row 1
    df.iloc[2] = df.iloc[1]
    df.iloc[3] = df.iloc[1]
    df.iloc[4] = df.iloc[1]

    # Inject 10 NaN cells (at rows 10-14 for cat_c and mixed_d)
    for r in range(10, 15):
        df.iloc[r, 2] = np.nan
        df.iloc[r, 3] = np.nan

    dqi_result = profiling_service.compute_data_quality_index(df)

    sub_scores = dqi_result["sub_scores"]
    eff_weights = dqi_result["effective_weights"]
    overall_index = dqi_result["overall_index"]

    # Verify effective weights structure and values
    assert eff_weights["missingness"] == 0.35
    assert eff_weights["duplicate_rate"] == 0.25
    assert eff_weights["outlier_prevalence"] == 0.20
    assert eff_weights["type_consistency"] == 0.20
    assert sum(eff_weights.values()) == 1.0

    # Verify sub-scores
    # 10 missing cells / 100 cells = 10% -> 90.0
    assert sub_scores["missingness"] == 90.0
    # 3 duplicate rows / 20 rows = 15% -> 85.0
    assert sub_scores["duplicate_rate"] == 85.0
    # Outliers: IQR on col_a and col_b
    assert sub_scores["outlier_prevalence"] is not None
    # Mixed column: 1 mixed / 5 cols = 20% -> 80.0
    assert sub_scores["type_consistency"] == 80.0

    # Verify weighted calculation
    expected_overall = round(
        sub_scores["missingness"] * 0.35 +
        sub_scores["duplicate_rate"] * 0.25 +
        sub_scores["outlier_prevalence"] * 0.20 +
        sub_scores["type_consistency"] * 0.20,
        2
    )
    assert overall_index == expected_overall


def test_dqi_custom_weights_and_empty_edge_cases(db_session):
    """
    Verifies DQI calculation with custom weights and empty DataFrame handling.
    """
    profiling_service = DataProfilingService(db_session)

    # Empty DataFrame
    empty_df = pd.DataFrame()
    empty_dqi = profiling_service.compute_data_quality_index(empty_df)
    assert empty_dqi["sub_scores"]["missingness"] == 100.0
    assert empty_dqi["sub_scores"]["duplicate_rate"] == 100.0
    assert empty_dqi["sub_scores"]["outlier_prevalence"] is None
    assert empty_dqi["sub_scores"]["type_consistency"] == 100.0
    assert empty_dqi["overall_index"] == 100.0

    # Custom weights
    df = pd.DataFrame({"x": [1, 2, 3, 4, 5], "y": ["a", "b", "c", "d", "e"]})
    custom_w = {"missingness": 0.50, "duplicate_rate": 0.50, "outlier_prevalence": 0.0, "type_consistency": 0.0}
    dqi_custom = profiling_service.compute_data_quality_index(df, custom_weights=custom_w)
    assert dqi_custom["overall_index"] == 100.0


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


def test_api_dqi_renormalization_no_numeric_columns(client, db_session, create_test_user):
    """
    Day 2 Renormalization Edge Case API Test:
    Upload a dataset with NO numeric columns (all categorical features).
    Trigger outer split and profiling via the API.
    Assert that:
    1. The API surfaces Outlier Prevalence as null (None) in both sub_scores and effective_weights.
    2. The API surfaces renormalized effective weights:
       - Missingness: 43.75% (0.4375)
       - Duplicate Rate: 31.25% (0.3125)
       - Type Consistency: 25.00% (0.2500)
    3. Active effective weights sum to 1.0 (100%).
    4. overall_index equals the exact weighted average across the 3 active sub-scores.
    5. GET /api/v1/datasets/{id}/profile returns the exact same renormalized report.
    6. projects.data_quality_index reflects this renormalized overall_index.
    """
    token = get_auth_token(client, email="renorm_api@example.com")
    auth_headers = {"Authorization": f"Bearer {token}"}

    # 1. Create project via API
    proj_resp = client.post(
        "/api/v1/projects",
        json={"project_name": "No Numeric Columns API Test", "target_column": "label"},
        headers=auth_headers
    )
    assert proj_resp.status_code == status.HTTP_201_CREATED
    proj_id = proj_resp.json()["id"]

    # 2. Upload dataset with NO numeric columns
    csv_bytes = create_sample_csv(rows=60, target_type="all_categorical")
    upload_resp = client.post(
        f"/api/v1/projects/{proj_id}/datasets",
        files={"file": ("no_numeric_dataset.csv", io.BytesIO(csv_bytes), "text/csv")},
        headers=auth_headers
    )
    assert upload_resp.status_code == status.HTTP_201_CREATED
    dataset_id = upload_resp.json()["id"]

    # 3. Create outer split (80% Dev, 20% Locked Test)
    split_resp = client.post(
        f"/api/v1/datasets/{dataset_id}/split",
        json={"locked_test_pct": 20, "seed": 42},
        headers=auth_headers
    )
    assert split_resp.status_code == status.HTTP_201_CREATED

    # 4. Trigger profiling via API (POST /profile)
    profile_resp = client.post(
        f"/api/v1/datasets/{dataset_id}/profile",
        headers=auth_headers
    )
    assert profile_resp.status_code == status.HTTP_200_OK
    data = profile_resp.json()

    assert "data_quality_index" in data
    dqi = data["data_quality_index"]

    # 5. Assert sub-scores: outlier prevalence is None
    sub_scores = dqi["sub_scores"]
    assert sub_scores["outlier_prevalence"] is None
    assert isinstance(sub_scores["missingness"], (int, float))
    assert isinstance(sub_scores["duplicate_rate"], (int, float))
    assert isinstance(sub_scores["type_consistency"], (int, float))

    # 6. Assert effective weights: outlier_prevalence is None, others renormalized
    eff_weights = dqi["effective_weights"]
    assert eff_weights["outlier_prevalence"] is None
    assert pytest.approx(eff_weights["missingness"], 0.0001) == 0.4375
    assert pytest.approx(eff_weights["duplicate_rate"], 0.0001) == 0.3125
    assert pytest.approx(eff_weights["type_consistency"], 0.0001) == 0.2500

    active_weight_sum = (
        eff_weights["missingness"] +
        eff_weights["duplicate_rate"] +
        eff_weights["type_consistency"]
    )
    assert pytest.approx(active_weight_sum, 0.0001) == 1.0

    # 7. Assert overall_index equals weighted average
    expected_overall = round(
        sub_scores["missingness"] * 0.4375 +
        sub_scores["duplicate_rate"] * 0.3125 +
        sub_scores["type_consistency"] * 0.2500,
        2
    )
    assert pytest.approx(dqi["overall_index"], 0.01) == expected_overall

    # 8. GET /api/v1/datasets/{id}/profile surfaces identical renormalized structure
    get_resp = client.get(
        f"/api/v1/datasets/{dataset_id}/profile",
        headers=auth_headers
    )
    assert get_resp.status_code == status.HTTP_200_OK
    get_dqi = get_resp.json()["data_quality_index"]
    assert get_dqi["effective_weights"] == eff_weights
    assert get_dqi["sub_scores"] == sub_scores
    assert pytest.approx(get_dqi["overall_index"], 0.01) == expected_overall

    # 9. Verify project table data_quality_index was updated
    proj_db = db_session.query(Project).filter(Project.id == UUID(proj_id)).first()
    assert proj_db is not None
    assert pytest.approx(float(proj_db.data_quality_index), 0.01) == expected_overall


def test_profiling_state_guard_and_development_partition_storage(client, db_session, create_test_user):
    """
    Day 3 Profiling Invariant & State Guard Test:
    1. Pre-condition: Project is in DATA_UPLOADED.
    2. Assert profiling fails cleanly (HTTP 422) before ProjectState reaches SPLIT_LOCKED.
    3. Assert ZERO rows created in profiling_reports before split.
    4. Assert project.pipeline_stage remains DATA_UPLOADED.
    5. Perform outer split -> ProjectState transitions to SPLIT_LOCKED.
    6. Execute profiling on Development partition:
       - Generates numeric stats (mean, std, min, max, IQR, skew, quartiles, outlier count/pct).
       - Generates categorical frequency distribution (mode, top-10 frequency table).
       - Generates pairwise Pearson correlation matrix for numeric columns.
       - Stores full report in profiling_reports linked strictly to DEVELOPMENT dataset_split_id.
       - Transitions ProjectState to PROFILED.
    """
    token = get_auth_token(client, email="day3_profiler@example.com")
    auth_headers = {"Authorization": f"Bearer {token}"}

    # 1. Create project via API
    proj_resp = client.post(
        "/api/v1/projects",
        json={"project_name": "Day 3 State Guard & Profiling Test", "target_column": "target"},
        headers=auth_headers
    )
    assert proj_resp.status_code == status.HTTP_201_CREATED
    proj_id = proj_resp.json()["id"]

    # 2. Upload dataset with mixed types (numeric, categorical, target)
    csv_bytes = create_sample_csv(rows=100, target_type="categorical")
    upload_resp = client.post(
        f"/api/v1/projects/{proj_id}/datasets",
        files={"file": ("day3_dataset.csv", io.BytesIO(csv_bytes), "text/csv")},
        headers=auth_headers
    )
    assert upload_resp.status_code == status.HTTP_201_CREATED
    dataset_id = upload_resp.json()["id"]

    # Check project state before split is created
    proj_db = db_session.query(Project).filter(Project.id == UUID(proj_id)).first()
    assert proj_db.pipeline_stage in ["DATA_UPLOADED", "DATA"]

    # 3. Assert pre-SPLIT_LOCKED profiling FAILS cleanly with HTTP 422
    pre_profile_resp = client.post(
        f"/api/v1/datasets/{dataset_id}/profile",
        headers=auth_headers
    )
    assert pre_profile_resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    pre_err = pre_profile_resp.json()["detail"].lower()
    assert "outer split" in pre_err or "split" in pre_err

    # Assert ZERO rows in profiling_reports
    initial_reports_count = db_session.query(ProfilingReport).count()

    # Assert project.pipeline_stage is UNCHANGED
    db_session.refresh(proj_db)
    assert proj_db.pipeline_stage in ["DATA_UPLOADED", "DATA"]

    # 4. Perform outer split -> Project transitions to SPLIT_LOCKED
    split_resp = client.post(
        f"/api/v1/datasets/{dataset_id}/split",
        json={"locked_test_pct": 25, "seed": 42},
        headers=auth_headers
    )
    assert split_resp.status_code == status.HTTP_201_CREATED

    db_session.refresh(proj_db)
    assert proj_db.pipeline_stage == "SPLIT_LOCKED"

    # 5. Now execute profiling on Development partition
    post_profile_resp = client.post(
        f"/api/v1/datasets/{dataset_id}/profile",
        headers=auth_headers
    )
    assert post_profile_resp.status_code == status.HTTP_200_OK
    report_data = post_profile_resp.json()

    # 6. Verify distribution statistics and correlation matrix
    assert "column_stats" in report_data
    col_stats = report_data["column_stats"]
    assert "feature_a" in col_stats
    num_stat = col_stats["feature_a"]
    assert num_stat["type"] == "numeric"
    for key in ["mean", "median", "std", "skew", "min", "max", "q25", "q75", "iqr", "outlier_count", "outlier_pct"]:
        assert key in num_stat

    assert "cat_feature" in col_stats
    cat_stat = col_stats["cat_feature"]
    assert cat_stat["type"] == "categorical"
    assert "mode" in cat_stat
    assert "frequency_table" in cat_stat
    assert len(cat_stat["frequency_table"]) > 0

    assert "correlation_matrix" in report_data
    corr = report_data["correlation_matrix"]
    assert "columns" in corr
    assert "matrix" in corr
    assert len(corr["columns"]) >= 2
    assert len(corr["matrix"]) == len(corr["columns"])

    # 7. Verify persistence in profiling_reports table linked to DEVELOPMENT split
    dev_split = (
        db_session.query(DatasetSplit)
        .filter(DatasetSplit.dataset_id == UUID(dataset_id), DatasetSplit.split_type == "DEVELOPMENT")
        .first()
    )
    assert dev_split is not None

    db_report = (
        db_session.query(ProfilingReport)
        .filter(ProfilingReport.dataset_split_id == dev_split.id)
        .first()
    )
    assert db_report is not None
    assert db_report.report_json["total_rows"] == len(dev_split.row_indices)
    assert db_report.report_json["column_stats"]["feature_a"]["mean"] == num_stat["mean"]
    assert db_session.query(ProfilingReport).count() == initial_reports_count + 1

    # 8. Assert project.pipeline_stage transitioned to PROFILED
    db_session.refresh(proj_db)
    assert proj_db.pipeline_stage == "PROFILED"


def test_api_task_type_detection_ambiguity_blocks_auto_selection(client, db_session, create_test_user):
    """
    Day 4 Task-Type Detection & Ambiguity Guard API Test:
    1. Upload a dataset with an engineered AMBIGUOUS target:
       - 15 unique integers in 50 rows (unique_ratio = 0.30 >= 0.05, unique_count = 15 <= 20).
    2. Create split and trigger profiling via POST /datasets/{id}/profile.
    3. Verify API surfaces:
       - suggested_task_type = "UNDETERMINED"
       - confidence = "AMBIGUOUS"
       - is_ambiguous = True
       - unique_count <= 20 and unique_ratio >= 0.05
    4. Verify GET /api/v1/projects/{id}:
       - task_type == "UNDETERMINED" (silent auto-selection blocked)
       - task_type_confidence == "AMBIGUOUS"
    5. Verify manual user resolution via PUT /api/v1/projects/{id}/task-type:
       - Sets task_type to "CLASSIFICATION" with task_type_confidence = "MANUAL".
    """
    token = get_auth_token(client, email="ambig_task@example.com")
    auth_headers = {"Authorization": f"Bearer {token}"}

    # 1. Create project via API
    proj_resp = client.post(
        "/api/v1/projects",
        json={"project_name": "Ambiguous Target API Test", "target_column": "target"},
        headers=auth_headers
    )
    assert proj_resp.status_code == status.HTTP_201_CREATED
    proj_id = proj_resp.json()["id"]

    # 2. Upload engineered ambiguous dataset (15 unique integers across 50 rows)
    csv_bytes = create_sample_csv(rows=50, target_type="ambiguous")
    upload_resp = client.post(
        f"/api/v1/projects/{proj_id}/datasets",
        files={"file": ("ambiguous_dataset.csv", io.BytesIO(csv_bytes), "text/csv")},
        headers=auth_headers
    )
    assert upload_resp.status_code == status.HTTP_201_CREATED
    dataset_id = upload_resp.json()["id"]

    # 3. Create outer split (80% Dev, 20% Locked Test)
    split_resp = client.post(
        f"/api/v1/datasets/{dataset_id}/split",
        json={"locked_test_pct": 20, "seed": 42},
        headers=auth_headers
    )
    assert split_resp.status_code == status.HTTP_201_CREATED

    # 4. Trigger profiling via API
    profile_resp = client.post(
        f"/api/v1/datasets/{dataset_id}/profile",
        headers=auth_headers
    )
    assert profile_resp.status_code == status.HTTP_200_OK
    profile_data = profile_resp.json()

    assert "task_type_suggestion" in profile_data
    suggestion = profile_data["task_type_suggestion"]
    assert suggestion["suggested_task_type"] == "UNDETERMINED"
    assert suggestion["confidence"] == "AMBIGUOUS"
    assert suggestion["is_ambiguous"] is True
    assert suggestion["unique_count"] <= 20
    assert suggestion["unique_ratio"] >= 0.05
    assert len(suggestion["sample_values"]) > 0

    # 5. Assert that project state did NOT silently auto-select CLASSIFICATION or REGRESSION
    proj_get = client.get(f"/api/v1/projects/{proj_id}", headers=auth_headers)
    assert proj_get.status_code == status.HTTP_200_OK
    proj_data = proj_get.json()
    assert proj_data["task_type"] == "UNDETERMINED"
    assert proj_data["task_type_confidence"] == "AMBIGUOUS"

    # Also check direct DB state
    proj_db = db_session.query(Project).filter(Project.id == UUID(proj_id)).first()
    assert proj_db is not None
    assert proj_db.task_type == "UNDETERMINED"
    assert proj_db.task_type_confidence == "AMBIGUOUS"

    # 6. Resolve ambiguity manually via PUT /projects/{id}/task-type
    override_resp = client.put(
        f"/api/v1/projects/{proj_id}/task-type",
        json={"task_type": "CLASSIFICATION"},
        headers=auth_headers
    )
    assert override_resp.status_code == status.HTTP_200_OK
    override_data = override_resp.json()
    assert override_data["task_type"] == "CLASSIFICATION"
    assert override_data["task_type_confidence"] == "MANUAL"

    db_session.refresh(proj_db)
    assert proj_db.task_type == "CLASSIFICATION"
    assert proj_db.task_type_confidence == "MANUAL"


def test_recommendations_schema_and_computed_evidence_rules(client, db_session, create_test_user):
    """
    Day 5 Recommendations Schema & Starter Rules Test:
    1. Upload a dataset engineered with:
       - Skewed missing numeric feature (feature_b) -> Rule 1 missingness rule
       - Exact duplicate rows -> Rule 2 deduplication rule
       - Outlier-laden feature (feature_a) -> Rule 3 outlier winsorization rule
       - Mixed-dtype column (mixed_col) -> Rule 4 schema casting rule
    2. Create split and run profiling via API (POST /datasets/{id}/profile).
    3. Retrieve recommendations via GET /projects/{id}/recommendations.
    4. Assert schema compliance on each recommendation:
       - id (UUID string)
       - project_id (UUID string)
       - finding (non-empty string)
       - evidence (non-empty string containing real computed numerical values)
       - recommended_action (non-empty string)
       - risk_note (non-empty string)
       - confidence (one of 'HIGH', 'MEDIUM', 'LOW')
       - status ('SUGGESTED')
    5. Assert real computed values in evidence:
       - Evidence for skewness contains 'skewness=' or 'skew=' with actual float numbers.
       - Evidence for outliers contains 'IQR range is [' with bounded float numbers.
       - Evidence for duplicates contains 'Duplicate Rate Score is' with computed float score.
    """
    token = get_auth_token(client, email="recs_user@example.com")
    auth_headers = {"Authorization": f"Bearer {token}"}

    # 1. Create project
    proj_resp = client.post(
        "/api/v1/projects",
        json={"project_name": "Recommendations Schema Test", "target_column": "target"},
        headers=auth_headers
    )
    assert proj_resp.status_code == status.HTTP_201_CREATED
    proj_id = proj_resp.json()["id"]

    # 2. Handcraft dataset containing all 4 diagnostic trigger patterns
    np.random.seed(42)
    n_rows = 100
    feat_a = np.random.normal(50, 10, n_rows)
    # Add multiple extreme outliers to feat_a
    feat_a[0] = 1000.0
    feat_a[1] = 1200.0
    feat_a[2] = -800.0
    feat_a[3] = 950.0

    feat_b = np.random.exponential(15, n_rows) # highly skewed
    mixed_data = [1, 2, "three", "four", 5] * 20
    target_data = ["Class_1" if i % 2 == 0 else "Class_2" for i in range(n_rows)]

    df = pd.DataFrame({
        "feature_a": feat_a,
        "feature_b": feat_b,
        "mixed_col": mixed_data,
        "target": target_data
    })

    # Add missingness in skewed feature_b
    df.loc[10:25, "feature_b"] = np.nan

    # Add 10 duplicate rows
    for i in range(50, 60):
        df.iloc[i] = df.iloc[45]

    csv_bytes = df.to_csv(index=False).encode("utf-8")

    upload_resp = client.post(
        f"/api/v1/projects/{proj_id}/datasets",
        files={"file": ("diagnostics_dataset.csv", io.BytesIO(csv_bytes), "text/csv")},
        headers=auth_headers
    )
    assert upload_resp.status_code == status.HTTP_201_CREATED
    dataset_id = upload_resp.json()["id"]

    # 3. Create outer split
    split_resp = client.post(
        f"/api/v1/datasets/{dataset_id}/split",
        json={"locked_test_pct": 20, "seed": 42},
        headers=auth_headers
    )
    assert split_resp.status_code == status.HTTP_201_CREATED

    # 4. Trigger profiling
    profile_resp = client.post(
        f"/api/v1/datasets/{dataset_id}/profile",
        headers=auth_headers
    )
    assert profile_resp.status_code == status.HTTP_200_OK

    # 5. Query recommendations API endpoint
    recs_resp = client.get(
        f"/api/v1/projects/{proj_id}/recommendations",
        headers=auth_headers
    )
    assert recs_resp.status_code == status.HTTP_200_OK
    recs = recs_resp.json()

    assert isinstance(recs, list)
    assert len(recs) >= 3, f"Expected at least 3 recommendations, got {len(recs)}"

    required_keys = ["id", "project_id", "finding", "evidence", "recommended_action", "risk_note", "confidence", "status"]
    evidence_all = []

    for rec in recs:
        # Schema validation
        for k in required_keys:
            assert k in rec, f"Missing key '{k}' in recommendation: {rec}"
            assert rec[k] is not None and len(str(rec[k]).strip()) > 0

        assert rec["project_id"] == str(proj_id)
        assert rec["confidence"] in ["HIGH", "MEDIUM", "LOW"]
        assert rec["status"] in ["SUGGESTED", "ACCEPTED", "DISMISSED"]

        evidence_all.append(rec["evidence"])

    # Verify real computed numbers in evidence strings (no unrendered placeholders)
    assert any("skewness=" in ev or "skew=" in ev for ev in evidence_all), "Evidence missing real skewness computation"
    assert any("Duplicate Rate Score is" in ev for ev in evidence_all), "Evidence missing real duplicate rate score"
    assert any("IQR range is [" in ev for ev in evidence_all), "Evidence missing real IQR range numbers"





