import io
import hashlib
import uuid
import pytest
import pandas as pd
from fastapi import HTTPException
from app.models.dataset import Dataset
from app.models.dataset_split import DatasetSplit
from app.models.project import Project
from app.services.dataset_split_service import DatasetSplitService
from app.services.pipeline_guards import require_split_exists
from scripts.backfill_content_hashes import backfill_content_hashes

def create_mock_csv(n_rows: int = 100, target_col: str = "label") -> bytes:
    """Generates a synthetic CSV with unique identifiable rows and a balanced target."""
    data = {
        "record_id": [f"REC_{i:04d}" for i in range(n_rows)],
        "feature_val": [i * 1.5 for i in range(n_rows)],
        "category": ["Alpha" if i % 2 == 0 else "Beta" for i in range(n_rows)],
        target_col: ["Positive" if i % 3 == 0 else "Negative" for i in range(n_rows)],
    }
    df = pd.DataFrame(data)
    csv_buf = io.StringIO()
    df.to_csv(csv_buf, index=False)
    return csv_buf.getvalue().encode("utf-8")

def get_auth_token(client, email="engineer@example.com", role_name="ML_ENGINEER"):
    reg_resp = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Test Engineer",
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

def test_adversarial_locked_test_leakage_barrier(client, db_session):
    """
    Acceptance Check (a): Adversarial Leakage Test
    Record Locked Test row indices from DB directly (test-only access).
    Call every endpoint and confirm NONE return those row indices or any values from those specific rows.
    """
    token = get_auth_token(client, email="adv_user@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Create project with target column
    proj_res = client.post(
        "/api/v1/projects",
        json={"project_name": "Adversarial Invariant Project", "target_column": "label"},
        headers=headers,
    )
    assert proj_res.status_code == 201
    project_id = proj_res.json()["id"]

    # 2. Upload dataset (100 distinct rows)
    csv_bytes = create_mock_csv(100, target_col="label")
    upload_res = client.post(
        f"/api/v1/projects/{project_id}/datasets",
        files={"file": ("adversarial_data.csv", csv_bytes, "text/csv")},
        headers=headers,
    )
    assert upload_res.status_code == 201
    dataset_id = upload_res.json()["id"]

    # 3. Create outer split via API with fixed seed
    split_payload = {"locked_test_pct": 20, "seed": 42}
    split_res = client.post(
        f"/api/v1/datasets/{dataset_id}/split",
        json=split_payload,
        headers=headers,
    )
    assert split_res.status_code == 201
    split_data = split_res.json()

    # Verify split response structure (MUST NOT contain row_indices or data rows)
    assert "row_indices" not in split_data
    assert "rows" not in split_data
    assert "data" not in split_data
    assert split_data["development_rows"] == 80
    assert split_data["locked_test_rows"] == 20
    assert split_data["split_seed"] == 42
    assert split_data["is_stratified"] is True

    # 4. DIRECT DB ACCESS (Test Oracle ONLY) to inspect what locked test rows are
    test_split_db = (
        db_session.query(DatasetSplit)
        .filter(DatasetSplit.dataset_id == uuid.UUID(dataset_id), DatasetSplit.split_type == "LOCKED_TEST")
        .first()
    )
    assert test_split_db is not None
    locked_indices = set(test_split_db.row_indices)
    assert len(locked_indices) == 20

    # Parse full original CSV to know the exact record_ids in the locked test set
    loaded_df = DatasetSplitService(db_session)._load_full_dataframe(test_split_db.dataset)
    if "row_uid" in loaded_df.columns and isinstance(next(iter(locked_indices)), str):
        locked_record_ids = set(loaded_df[loaded_df["row_uid"].isin(locked_indices)]["record_id"].tolist())
    else:
        df_full = pd.read_csv(io.BytesIO(csv_bytes))
        locked_record_ids = set(df_full.iloc[list(locked_indices)]["record_id"].tolist())

    # 5. Call GET /split summary endpoint: verify no row-level leakage
    get_split_res = client.get(
        f"/api/v1/datasets/{dataset_id}/split",
        headers=headers,
    )
    assert get_split_res.status_code == 200
    summary_data = get_split_res.json()
    assert "row_indices" not in summary_data
    for rec_id in locked_record_ids:
        assert rec_id not in str(summary_data)

    # 6. Call GET /development-preview endpoint: verify preview contains ONLY development rows
    preview_res = client.get(
        f"/api/v1/datasets/{dataset_id}/development-preview?limit=50",
        headers=headers,
    )
    assert preview_res.status_code == 200
    preview_data = preview_res.json()
    assert preview_data["total_development_rows"] == 80
    preview_rows = preview_data["preview_rows"]

    for row in preview_rows:
        row_rec_id = row["record_id"]
        # CRITICAL ASSERTION: No preview row can belong to the locked test set
        assert row_rec_id not in locked_record_ids, f"Leakage detected: {row_rec_id} found in dev preview!"

    # 7. Check that no locked-test endpoint exists (404/405)
    for bad_url in [
        f"/api/v1/datasets/{dataset_id}/locked-test",
        f"/api/v1/datasets/{dataset_id}/test-preview",
        f"/api/v1/datasets/{dataset_id}/locked-test-preview",
    ]:
        bad_res = client.get(bad_url, headers=headers)
        assert bad_res.status_code in [404, 405], f"Endpoint {bad_url} unexpectedly exists!"

def test_split_reproducibility(client, db_session):
    """
    Acceptance Check (b): Reproducibility Test
    Create two splits with the same seed on two copies of the same dataset
    and confirm the resulting partitions are identical.
    """
    token = get_auth_token(client, email="repro_user@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    # Create two projects
    p1 = client.post("/api/v1/projects", json={"project_name": "Repro P1", "target_column": "label"}, headers=headers).json()
    p2 = client.post("/api/v1/projects", json={"project_name": "Repro P2", "target_column": "label"}, headers=headers).json()

    csv_bytes = create_mock_csv(150, target_col="label")
    ds1 = client.post(f"/api/v1/projects/{p1['id']}/datasets", files={"file": ("d1.csv", csv_bytes, "text/csv")}, headers=headers).json()
    ds2 = client.post(f"/api/v1/projects/{p2['id']}/datasets", files={"file": ("d2.csv", csv_bytes, "text/csv")}, headers=headers).json()

    fixed_seed = 987654

    # Create outer split on ds1 and ds2 with identical parameters
    client.post(f"/api/v1/datasets/{ds1['id']}/split", json={"locked_test_pct": 25, "seed": fixed_seed}, headers=headers)
    client.post(f"/api/v1/datasets/{ds2['id']}/split", json={"locked_test_pct": 25, "seed": fixed_seed}, headers=headers)

    # Check DB partitions
    split1_dev = db_session.query(DatasetSplit).filter(DatasetSplit.dataset_id == uuid.UUID(ds1["id"]), DatasetSplit.split_type == "DEVELOPMENT").first()
    split1_test = db_session.query(DatasetSplit).filter(DatasetSplit.dataset_id == uuid.UUID(ds1["id"]), DatasetSplit.split_type == "LOCKED_TEST").first()

    split2_dev = db_session.query(DatasetSplit).filter(DatasetSplit.dataset_id == uuid.UUID(ds2["id"]), DatasetSplit.split_type == "DEVELOPMENT").first()
    split2_test = db_session.query(DatasetSplit).filter(DatasetSplit.dataset_id == uuid.UUID(ds2["id"]), DatasetSplit.split_type == "LOCKED_TEST").first()

    assert split1_dev.row_indices == split2_dev.row_indices
    assert split1_test.row_indices == split2_test.row_indices
    assert len(split1_test.row_indices) == 38
    assert len(split1_dev.row_indices) == 112

def test_double_split_rejection(client, db_session):
    """
    Acceptance Check (c): Double-split error handling
    Attempt to call create_outer_split() twice on the same dataset_id and confirm
    it fails with a clear error rather than silently creating a duplicate or overwriting.
    """
    token = get_auth_token(client, email="double_split@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    proj = client.post("/api/v1/projects", json={"project_name": "Double Split Guard"}, headers=headers).json()
    csv_bytes = create_mock_csv(50)
    ds = client.post(f"/api/v1/projects/{proj['id']}/datasets", files={"file": ("data.csv", csv_bytes, "text/csv")}, headers=headers).json()

    # First split creation: OK
    res1 = client.post(f"/api/v1/datasets/{ds['id']}/split", json={"locked_test_pct": 20, "seed": 123}, headers=headers)
    assert res1.status_code == 201

    # Second split creation attempt: Rejection
    res2 = client.post(f"/api/v1/datasets/{ds['id']}/split", json={"locked_test_pct": 20, "seed": 123}, headers=headers)
    assert res2.status_code == 400
    assert "already exists" in res2.json()["detail"].lower()

def test_content_hash_integrity_and_backfill(client, db_session):
    """
    Acceptance Check (d): Content hash calculation and backfill
    Confirm content_hash is populated for both freshly uploaded datasets and Day 1 backfilled ones,
    and that manual SHA-256 computation matches stored hash.
    """
    token = get_auth_token(client, email="hash_user@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    proj = client.post("/api/v1/projects", json={"project_name": "Hashing Test"}, headers=headers).json()
    csv_bytes = create_mock_csv(60)
    expected_hash = hashlib.sha256(csv_bytes).hexdigest()

    # 1. Fresh upload: verify content_hash is computed immediately
    upload_res = client.post(
        f"/api/v1/projects/{proj['id']}/datasets",
        files={"file": ("fresh.csv", csv_bytes, "text/csv")},
        headers=headers,
    )
    assert upload_res.status_code == 201
    fresh_ds = upload_res.json()
    assert fresh_ds["content_hash"] == expected_hash

    # 2. Simulate pre-existing Day 1 dataset where content_hash was NULL
    db_ds = db_session.query(Dataset).filter(Dataset.id == uuid.UUID(fresh_ds["id"])).first()
    db_ds.content_hash = None
    db_session.commit()
    db_session.refresh(db_ds)
    assert db_ds.content_hash is None

    # 3. Run backfill script
    backfilled_count = backfill_content_hashes(db=db_session)
    assert backfilled_count >= 1

    # 4. Verify DB row now has correct hash
    db_session.refresh(db_ds)
    assert db_ds.content_hash == expected_hash

def test_project_pipeline_stage_and_guard(client, db_session):
    """
    Acceptance Check (e): Pipeline Stage 'SPLIT' update and require_split_exists guard
    """
    token = get_auth_token(client, email="stage_user@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    proj = client.post("/api/v1/projects", json={"project_name": "Stage Transition Proj"}, headers=headers).json()
    csv_bytes = create_mock_csv(40)
    ds = client.post(f"/api/v1/projects/{proj['id']}/datasets", files={"file": ("test.csv", csv_bytes, "text/csv")}, headers=headers).json()

    # Before split: pipeline_stage is 'DATA'
    proj_db = db_session.query(Project).filter(Project.id == uuid.UUID(proj["id"])).first()
    assert proj_db.pipeline_stage == "DATA"

    # Guard before split must raise 400
    with pytest.raises(HTTPException) as exc_info:
        require_split_exists(db_session, uuid.UUID(proj["id"]))
    assert exc_info.value.status_code in [400, 422]

    # Create split
    client.post(f"/api/v1/datasets/{ds['id']}/split", json={"locked_test_pct": 20, "seed": 42}, headers=headers)

    # After split: pipeline_stage is 'SPLIT'
    db_session.refresh(proj_db)
    assert proj_db.pipeline_stage == "SPLIT"

    # Guard after split must pass cleanly without exception
    require_split_exists(db_session, uuid.UUID(proj["id"]))
