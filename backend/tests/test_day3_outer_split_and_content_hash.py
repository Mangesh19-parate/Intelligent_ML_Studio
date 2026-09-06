import io
import uuid
import hashlib
import pytest
import pandas as pd
from fastapi import HTTPException

from app.models.dataset import Dataset
from app.models.dataset_split import DatasetSplit
from app.models.project import Project
from app.services.dataset_split_service import DatasetSplitService
from app.services.pipeline_guards import require_split_exists

def create_sample_csv(n_rows: int = 50, target_col: str = "label") -> bytes:
    data = {
        "feature_1": [i * 2.5 for i in range(n_rows)],
        "feature_2": [f"group_{i % 3}" for i in range(n_rows)],
        target_col: ["class_a" if i % 2 == 0 else "class_b" for i in range(n_rows)],
    }
    df = pd.DataFrame(data)
    buf = io.StringIO()
    df.to_csv(buf, index=False)
    return buf.getvalue().encode("utf-8")

def get_auth_token(client, email="day3_engineer@example.com", role_name="ML_ENGINEER"):
    client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Day 3 Test Engineer",
            "email": email,
            "password": "password123",
            "role_name": role_name,
        },
    )
    login_resp = client.post(
        "/api/v1/auth/login",
        json={
            "email": email,
            "password": "password123",
        },
    )
    return login_resp.json()["access_token"]

def test_sha256_content_hash_computed_and_stored(client, db_session):
    """
    Day 3 Verification: SHA-256 dataset_content_hash computation and storage
    """
    token = get_auth_token(client, email="hash_user@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    proj = client.post("/api/v1/projects", json={"project_name": "Content Hash Project"}, headers=headers).json()
    csv_bytes = create_sample_csv(30)
    expected_hash = hashlib.sha256(csv_bytes).hexdigest()

    ds_resp = client.post(
        f"/api/v1/projects/{proj['id']}/datasets",
        files={"file": ("dataset.csv", csv_bytes, "text/csv")},
        headers=headers,
    )
    assert ds_resp.status_code == 201
    ds_data = ds_resp.json()

    assert ds_data["content_hash"] == expected_hash
    assert len(ds_data["content_hash"]) == 64

    # Direct DB check
    ds_db = db_session.query(Dataset).filter(Dataset.id == uuid.UUID(ds_data["id"])).first()
    assert ds_db is not None
    assert ds_db.content_hash == expected_hash

def test_duplicate_dataset_same_project_rejected(client, db_session):
    """
    Day 3 Verification: UNIQUE(project_id, dataset_content_hash) rejection
    Uploading identical content to the same project must return 409 Conflict.
    """
    token = get_auth_token(client, email="dup_user@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    proj = client.post("/api/v1/projects", json={"project_name": "Duplicate Test Project"}, headers=headers).json()
    csv_bytes = create_sample_csv(40)

    # 1. First upload succeeds
    r1 = client.post(
        f"/api/v1/projects/{proj['id']}/datasets",
        files={"file": ("raw_data.csv", csv_bytes, "text/csv")},
        headers=headers,
    )
    assert r1.status_code == 201

    # 2. Duplicate upload to SAME project must fail with 409 Conflict
    r2 = client.post(
        f"/api/v1/projects/{proj['id']}/datasets",
        files={"file": ("copy_raw_data.csv", csv_bytes, "text/csv")},
        headers=headers,
    )
    assert r2.status_code == 409
    assert "identical content already exists in this project" in r2.json()["detail"]

def test_duplicate_dataset_different_project_allowed(client, db_session):
    """
    Day 3 Verification: UNIQUE(project_id, dataset_content_hash) is project-scoped.
    Uploading identical content to different projects must succeed.
    """
    token = get_auth_token(client, email="multi_proj_user@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    proj1 = client.post("/api/v1/projects", json={"project_name": "Project Alpha"}, headers=headers).json()
    proj2 = client.post("/api/v1/projects", json={"project_name": "Project Beta"}, headers=headers).json()
    csv_bytes = create_sample_csv(40)

    r1 = client.post(
        f"/api/v1/projects/{proj1['id']}/datasets",
        files={"file": ("shared_data.csv", csv_bytes, "text/csv")},
        headers=headers,
    )
    assert r1.status_code == 201

    r2 = client.post(
        f"/api/v1/projects/{proj2['id']}/datasets",
        files={"file": ("shared_data.csv", csv_bytes, "text/csv")},
        headers=headers,
    )
    assert r2.status_code == 201
    assert r1.json()["content_hash"] == r2.json()["content_hash"]

def test_outer_split_membership_keyed_by_row_uid(client, db_session):
    """
    Day 3 Verification: dataset_splits membership is keyed strictly by row_uid (UUID string),
    never positional integer indices.
    """
    token = get_auth_token(client, email="split_uid_user@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    proj = client.post(
        "/api/v1/projects",
        json={"project_name": "Split Keyed By row_uid", "target_column": "label"},
        headers=headers,
    ).json()

    n_rows = 60
    csv_bytes = create_sample_csv(n_rows, target_col="label")
    ds = client.post(
        f"/api/v1/projects/{proj['id']}/datasets",
        files={"file": ("data_for_split.csv", csv_bytes, "text/csv")},
        headers=headers,
    ).json()

    split_res = client.post(
        f"/api/v1/datasets/{ds['id']}/split",
        json={"locked_test_pct": 25, "seed": 101},
        headers=headers,
    )
    assert split_res.status_code == 201
    split_data = split_res.json()
    assert split_data["development_rows"] == 45
    assert split_data["locked_test_rows"] == 15

    # Direct DB inspection of DatasetSplit records
    dev_split = (
        db_session.query(DatasetSplit)
        .filter(DatasetSplit.dataset_id == uuid.UUID(ds["id"]), DatasetSplit.split_type == "DEVELOPMENT")
        .first()
    )
    test_split = (
        db_session.query(DatasetSplit)
        .filter(DatasetSplit.dataset_id == uuid.UUID(ds["id"]), DatasetSplit.split_type == "LOCKED_TEST")
        .first()
    )

    assert dev_split is not None
    assert test_split is not None

    dev_indices = dev_split.row_indices
    test_indices = test_split.row_indices

    # Assert membership items are UUID strings, NOT integers
    assert len(dev_indices) == 45
    assert len(test_indices) == 15
    for uid in dev_indices:
        assert isinstance(uid, str)
        assert len(uid) == 36
        uuid.UUID(uid)  # Validates valid UUID format

    for uid in test_indices:
        assert isinstance(uid, str)
        assert len(uid) == 36
        uuid.UUID(uid)

    # Disjoint check
    assert set(dev_indices).isdisjoint(set(test_indices))

def test_outer_split_immutability(client, db_session):
    """
    Day 3 Verification: Calling create_outer_split twice on the same dataset must be rejected.
    """
    token = get_auth_token(client, email="immutability_user@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    proj = client.post("/api/v1/projects", json={"project_name": "Immutable Split Proj"}, headers=headers).json()
    csv_bytes = create_sample_csv(30)
    ds = client.post(
        f"/api/v1/projects/{proj['id']}/datasets",
        files={"file": ("immutability_data.csv", csv_bytes, "text/csv")},
        headers=headers,
    ).json()

    # 1. First split succeeds
    r1 = client.post(
        f"/api/v1/datasets/{ds['id']}/split",
        json={"locked_test_pct": 20, "seed": 42},
        headers=headers,
    )
    assert r1.status_code == 201

    # 2. Re-splitting the same dataset version is rejected
    r2 = client.post(
        f"/api/v1/datasets/{ds['id']}/split",
        json={"locked_test_pct": 30, "seed": 99},
        headers=headers,
    )
    assert r2.status_code == 400
    assert "Outer split already exists" in r2.json()["detail"]

def test_project_state_transitions_data_uploaded_to_split_locked(client, db_session):
    """
    Day 3 Verification: ProjectState transition from DATA_UPLOADED to SPLIT_LOCKED
    """
    token = get_auth_token(client, email="state_wire_user@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    proj = client.post("/api/v1/projects", json={"project_name": "State Lifecycle Proj"}, headers=headers).json()
    proj_db = db_session.query(Project).filter(Project.id == uuid.UUID(proj["id"])).first()

    # 1. Dataset uploaded -> DATA_UPLOADED
    csv_bytes = create_sample_csv(50)
    ds = client.post(
        f"/api/v1/projects/{proj['id']}/datasets",
        files={"file": ("state_data.csv", csv_bytes, "text/csv")},
        headers=headers,
    ).json()

    db_session.refresh(proj_db)
    assert proj_db.pipeline_stage in ["DATA_UPLOADED", "DATA"]

    # 2. Outer split created -> SPLIT_LOCKED
    client.post(
        f"/api/v1/datasets/{ds['id']}/split",
        json={"locked_test_pct": 20, "seed": 42},
        headers=headers,
    )

    db_session.refresh(proj_db)
    assert proj_db.pipeline_stage in ["SPLIT_LOCKED", "SPLIT"]

def test_get_development_data_retrieves_strictly_development_partition(client, db_session):
    """
    Day 3 Verification: get_development_data correctly filters by row_uid
    """
    token = get_auth_token(client, email="dev_data_user@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    proj = client.post("/api/v1/projects", json={"project_name": "Dev Data Isolation Proj"}, headers=headers).json()
    csv_bytes = create_sample_csv(40)
    ds = client.post(
        f"/api/v1/projects/{proj['id']}/datasets",
        files={"file": ("isolation_data.csv", csv_bytes, "text/csv")},
        headers=headers,
    ).json()

    client.post(
        f"/api/v1/datasets/{ds['id']}/split",
        json={"locked_test_pct": 25, "seed": 42},
        headers=headers,
    )

    split_service = DatasetSplitService(db_session)
    dev_df = split_service.get_development_data(ds["id"])
    assert len(dev_df) == 30
    assert "row_uid" in dev_df.columns

    # Verify locked test data contains remaining 10 rows
    locked_df = split_service.get_locked_test_data(ds["id"])
    assert len(locked_df) == 10
    assert set(dev_df["row_uid"]).isdisjoint(set(locked_df["row_uid"]))
