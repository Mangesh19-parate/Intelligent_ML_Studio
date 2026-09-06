import io
import uuid
import pytest
import pandas as pd
from app.models.dataset import Dataset
from app.models.dataset_column import DatasetColumn
from app.models.dataset_split import DatasetSplit
from app.services.dataset_service import DatasetService
from app.services.dataset_split_service import DatasetSplitService

def test_structural_schema_detection_and_invariants(client, create_test_user, db_session):
    user = create_test_user("steward_d2@example.com", role_name="DATA_STEWARD")
    login_data = client.post(
        "/api/v1/auth/login",
        json={"email": "steward_d2@example.com", "password": "password123"}
    ).json()
    headers = {"Authorization": f"Bearer {login_data['access_token']}"}

    # 1. Create project with target column 'outcome'
    proj_resp = client.post(
        "/api/v1/projects",
        json={"project_name": "Day 2 Validation Project", "target_column": "outcome"},
        headers=headers
    )
    assert proj_resp.status_code == 201
    project_id = proj_resp.json()["id"]

    # 2. Synthetic CSV with numeric, categorical, datetime, mixed columns and nulls
    csv_text = (
        "num_col,cat_col,date_col,mixed_col,outcome\n"
        "10.5,Red,2026-01-01,100,0\n"
        "20.0,Blue,2026-01-02,TextValue,1\n"
        ",Red,2026-01-03,200,0\n"
        "40.2,,2026-01-04,300,1\n"
    )
    csv_bytes = csv_text.encode("utf-8")

    # 3. Upload dataset
    upload_resp = client.post(
        "/api/v1/datasets/upload",
        data={"project_id": project_id},
        files={"file": ("validation_test.csv", io.BytesIO(csv_bytes), "text/csv")},
        headers=headers
    )
    assert upload_resp.status_code == 201
    dataset_id = upload_resp.json()["id"]

    # 4. Verify structural schema columns
    col_resp = client.get(
        f"/api/v1/datasets/{dataset_id}/columns",
        headers=headers
    )
    assert col_resp.status_code == 200
    columns = {c["column_name"]: c for c in col_resp.json()}

    # Assert expected user columns
    assert len(columns) == 5
    assert "row_uid" not in columns  # row_uid must not be exposed as a user feature column

    # Column: num_col -> NUMERIC, missing = 25.0%
    assert columns["num_col"]["data_type"] == "NUMERIC"
    assert float(columns["num_col"]["missing_percentage"]) == 25.0
    assert columns["num_col"]["unique_count"] == 3
    assert columns["num_col"]["is_target"] is False

    # Column: cat_col -> CATEGORICAL, missing = 25.0%
    assert columns["cat_col"]["data_type"] == "CATEGORICAL"
    assert float(columns["cat_col"]["missing_percentage"]) == 25.0
    assert columns["cat_col"]["unique_count"] == 2
    assert columns["cat_col"]["is_target"] is False

    # Column: date_col -> DATETIME, missing = 0.0%
    assert columns["date_col"]["data_type"] == "DATETIME"
    assert float(columns["date_col"]["missing_percentage"]) == 0.0
    assert columns["date_col"]["unique_count"] == 4

    # Column: outcome -> NUMERIC, is_target = True
    assert columns["outcome"]["data_type"] == "NUMERIC"
    assert columns["outcome"]["is_target"] is True

    # 5. Pre-split invariant check: Ensure ZERO profiling / correlation metrics exist in column payload
    forbidden_keys = {
        "skewness", "kurtosis", "variance", "std_dev", "mean", "median",
        "correlation", "task_type", "suggested_task_type", "data_quality_index"
    }
    for col in col_resp.json():
        for f_key in forbidden_keys:
            assert f_key not in col, f"Leakage detected: {f_key} present in pre-split structural column metadata"

def test_immutable_row_uid_assignment_and_persistence(client, create_test_user, db_session):
    user = create_test_user("mle_d2@example.com", role_name="ML_ENGINEER")
    login_data = client.post(
        "/api/v1/auth/login",
        json={"email": "mle_d2@example.com", "password": "password123"}
    ).json()
    headers = {"Authorization": f"Bearer {login_data['access_token']}"}

    proj_resp = client.post(
        "/api/v1/projects",
        json={"project_name": "Row UID Test Project"},
        headers=headers
    )
    project_id = proj_resp.json()["id"]

    csv_bytes = b"feature_1,feature_2\n10,Alpha\n20,Beta\n30,Gamma\n40,Delta\n50,Epsilon\n"

    upload_resp = client.post(
        "/api/v1/datasets/upload",
        data={"project_id": project_id},
        files={"file": ("data_with_uids.csv", io.BytesIO(csv_bytes), "text/csv")},
        headers=headers
    )
    assert upload_resp.status_code == 201
    dataset_id = upload_resp.json()["id"]

    ds_service = DatasetService(db_session)
    dataset = ds_service.dataset_repo.get_by_id(dataset_id)
    assert dataset is not None

    # Load dataframe and verify row_uid assignment
    split_service = DatasetSplitService(db_session)
    df = split_service._load_full_dataframe(dataset)

    assert "row_uid" in df.columns
    assert len(df["row_uid"]) == 5
    assert len(set(df["row_uid"])) == 5  # all unique

    # Validate that every row_uid is a valid RFC 4122 UUID string
    for r_uid in df["row_uid"]:
        parsed_uuid = uuid.UUID(r_uid)
        assert parsed_uuid.version in (4, 5)

    original_uids = df["row_uid"].tolist()

    # Re-trigger detect_structural_schema and confirm row_uids remain unchanged (immutable)
    ds_service.detect_structural_schema(dataset.id)
    df_reloaded = split_service._load_full_dataframe(dataset)
    assert df_reloaded["row_uid"].tolist() == original_uids

def test_split_references_row_uid(client, create_test_user, db_session):
    user = create_test_user("steward_split_d2@example.com", role_name="DATA_STEWARD")
    login_data = client.post(
        "/api/v1/auth/login",
        json={"email": "steward_split_d2@example.com", "password": "password123"}
    ).json()
    headers = {"Authorization": f"Bearer {login_data['access_token']}"}

    proj_resp = client.post(
        "/api/v1/projects",
        json={"project_name": "Split Row UID Project", "target_column": "target"},
        headers=headers
    )
    project_id = proj_resp.json()["id"]

    # 10 rows
    rows = [f"val_{i},{i % 2}" for i in range(10)]
    csv_content = ("feature,target\n" + "\n".join(rows) + "\n").encode("utf-8")

    upload_resp = client.post(
        "/api/v1/datasets/upload",
        data={"project_id": project_id},
        files={"file": ("split_data.csv", io.BytesIO(csv_content), "text/csv")},
        headers=headers
    )
    dataset_id = upload_resp.json()["id"]

    # Create outer split (20% locked test = 2 rows, 80% dev = 8 rows)
    split_resp = client.post(
        f"/api/v1/datasets/{dataset_id}/split",
        json={"locked_test_pct": 20, "seed": 42},
        headers=headers
    )
    assert split_resp.status_code == 201

    # Check splits in DB
    dev_split = db_session.query(DatasetSplit).filter(
        DatasetSplit.dataset_id == uuid.UUID(dataset_id),
        DatasetSplit.split_type == "DEVELOPMENT"
    ).first()
    test_split = db_session.query(DatasetSplit).filter(
        DatasetSplit.dataset_id == uuid.UUID(dataset_id),
        DatasetSplit.split_type == "LOCKED_TEST"
    ).first()

    assert dev_split is not None
    assert test_split is not None

    dev_uids = dev_split.row_indices
    test_uids = test_split.row_indices

    assert len(dev_uids) == 8
    assert len(test_uids) == 2

    # Partition isolation: No overlap between dev and test row_uids
    assert set(dev_uids).intersection(set(test_uids)) == set()

    # Verify get_development_data uses row_uids and returns 8 rows
    split_service = DatasetSplitService(db_session)
    dev_df = split_service.get_development_data(dataset_id)
    assert len(dev_df) == 8
    assert set(dev_df["row_uid"]) == set(dev_uids)

    # Verify get_locked_test_data returns 2 rows
    test_df = split_service.get_locked_test_data(dataset_id)
    assert len(test_df) == 2
    assert set(test_df["row_uid"]) == set(test_uids)
