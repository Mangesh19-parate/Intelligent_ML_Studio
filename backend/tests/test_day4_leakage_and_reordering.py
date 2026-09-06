import io
import uuid
import hashlib
import pytest
import pandas as pd
import numpy as np
from uuid import UUID

from app.models.dataset import Dataset
from app.models.dataset_split import DatasetSplit
from app.models.project import Project
from app.services.dataset_split_service import DatasetSplitService
from app.services.data_profiling_service import DataProfilingService
from app.services.transformation_service import TransformationService
from app.services.storage_service import get_storage_service

def generate_leakage_test_csv(n_rows: int = 100) -> bytes:
    """Generates synthetic tabular data where every row has a globally unique signature."""
    data = {
        "record_id": [f"REC_SIG_{i:04d}" for i in range(n_rows)],
        "sensor_reading": [float(i * 10 + 0.5) for i in range(n_rows)],
        "category": [f"CAT_{i % 5}" for i in range(n_rows)],
        "target": ["Yes" if i % 2 == 0 else "No" for i in range(n_rows)],
    }
    df = pd.DataFrame(data)
    buf = io.StringIO()
    df.to_csv(buf, index=False)
    return buf.getvalue().encode("utf-8")

def get_auth_token(client, email="day4_tester@example.com", role_name="ML_ENGINEER"):
    client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Day 4 Leakage Tester",
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

def test_locked_test_indices(client, db_session):
    """
    Day 4 Verification: test_locked_test_indices
    Asserts that Locked Test row_uids and locked test records NEVER appear in any
    Development-partition query result (API endpoints, service queries, previews, profiling).
    """
    token = get_auth_token(client, email="leakage_barrier@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Create Project and upload distinctive dataset
    proj_resp = client.post(
        "/api/v1/projects",
        json={"project_name": "Zero-Leakage Verification Project", "target_column": "target"},
        headers=headers,
    )
    assert proj_resp.status_code == 201
    project_id = proj_resp.json()["id"]

    n_rows = 100
    csv_bytes = generate_leakage_test_csv(n_rows)
    ds_resp = client.post(
        f"/api/v1/projects/{project_id}/datasets",
        files={"file": ("leakage_test_data.csv", csv_bytes, "text/csv")},
        headers=headers,
    )
    assert ds_resp.status_code == 201
    dataset_id = ds_resp.json()["id"]

    # 2. Establish Outer Split (80% Dev, 20% Locked Test)
    split_resp = client.post(
        f"/api/v1/datasets/{dataset_id}/split",
        json={"locked_test_pct": 20, "seed": 777},
        headers=headers,
    )
    assert split_resp.status_code == 201
    split_summary = split_resp.json()
    assert split_summary["development_rows"] == 80
    assert split_summary["locked_test_rows"] == 20

    # 3. Direct DB Test Oracle: Extract the exact Locked Test row_uids and record signatures
    locked_split = (
        db_session.query(DatasetSplit)
        .filter(DatasetSplit.dataset_id == UUID(dataset_id), DatasetSplit.split_type == "LOCKED_TEST")
        .first()
    )
    assert locked_split is not None
    locked_test_row_uids = set(locked_split.row_indices)
    assert len(locked_test_row_uids) == 20

    # Read full raw dataset to map locked row_uids to their unique record signatures
    split_service = DatasetSplitService(db_session)
    full_df = split_service._load_full_dataframe(
        db_session.query(Dataset).filter(Dataset.id == UUID(dataset_id)).first()
    )
    locked_test_records = full_df[full_df["row_uid"].isin(locked_test_row_uids)]
    locked_record_ids = set(locked_test_records["record_id"].tolist())
    assert len(locked_record_ids) == 20

    # 4. Check DatasetSplitService.get_development_data()
    dev_df = split_service.get_development_data(dataset_id)
    assert len(dev_df) == 80

    dev_row_uids = set(dev_df["row_uid"].tolist())
    dev_record_ids = set(dev_df["record_id"].tolist())

    # Mathematical Proof: Disjoint sets
    assert dev_row_uids.isdisjoint(locked_test_row_uids), "Leakage detected: Locked Test row_uids present in Development data!"
    assert dev_record_ids.isdisjoint(locked_record_ids), "Leakage detected: Locked Test record signatures present in Development data!"

    # 5. Check DatasetSplitService.get_development_preview()
    preview_data = split_service.get_development_preview(dataset_id, limit=25)
    preview_rows = preview_data["preview_rows"]
    for row in preview_rows:
        if "row_uid" in row and row["row_uid"] is not None:
            assert row["row_uid"] not in locked_test_row_uids, "Leakage in preview: Locked Test row_uid returned!"
        assert row["record_id"] not in locked_record_ids, "Leakage in preview: Locked Test record signature returned!"

    # 6. Check API Development Preview endpoint
    api_preview = client.get(f"/api/v1/datasets/{dataset_id}/development-preview", headers=headers)
    assert api_preview.status_code == 200
    for row in api_preview.json()["preview_rows"]:
        if "row_uid" in row and row["row_uid"] is not None:
            assert row["row_uid"] not in locked_test_row_uids
        assert row["record_id"] not in locked_record_ids

    # 7. Check DataProfilingService development profiling
    profiling_service = DataProfilingService(db_session)
    report = profiling_service.generate_report(dataset_id)
    assert report["total_rows"] == 80  # Exactly 80 Development rows, not 100!

def test_split_membership_survives_underlying_data_reordering(db_session):
    """
    Day 4 Verification: Re-ordering Invariance Test
    Proves that dataset_splits membership keyed by immutable row_uid (UUID string),
    rather than positional index, survives arbitrary shuffling/re-ordering of the
    underlying stored data without corrupting the split or leaking test rows.
    """
    storage = get_storage_service()
    project_id = uuid.uuid4()
    dataset_id = uuid.uuid4()

    # 1. Create dataset with explicit row_uids and distinctive signature
    n_rows = 60
    row_uids = [str(uuid.uuid4()) for _ in range(n_rows)]
    df_original = pd.DataFrame({
        "row_uid": row_uids,
        "item_code": [f"ITEM_{i:03d}" for i in range(n_rows)],
        "value": [float(i * 100) for i in range(n_rows)],
        "target": ["Positive" if i % 2 == 0 else "Negative" for i in range(n_rows)],
    })

    csv_bytes = df_original.to_csv(index=False).encode("utf-8")
    saved_path = storage.save_file(project_id, 1, "reorder_data.csv", csv_bytes)

    # 2. Persist project and dataset in database
    proj = Project(
        id=project_id,
        owner_id=uuid.uuid4(),
        project_name="Reordering Invariance Project",
        pipeline_stage="DATA_UPLOADED",
        target_column="target",
    )
    dataset = Dataset(
        id=dataset_id,
        project_id=project_id,
        file_path=saved_path,
        version_number=1,
        row_count=n_rows,
        column_count=4,
        stage="RAW",
        content_hash=hashlib.sha256(csv_bytes).hexdigest(),
    )
    db_session.add(proj)
    db_session.add(dataset)
    db_session.commit()

    # 3. Create outer split on original dataset
    split_service = DatasetSplitService(db_session, storage=storage)
    split_res = split_service.create_outer_split(dataset.id, locked_test_pct=30, seed=123)
    assert split_res["development_rows"] == 42
    assert split_res["locked_test_rows"] == 18

    # Record baseline development data partition
    baseline_dev_df = split_service.get_development_data(dataset.id)
    baseline_dev_uids = set(baseline_dev_df["row_uid"].tolist())
    baseline_dev_items = set(baseline_dev_df["item_code"].tolist())
    assert len(baseline_dev_uids) == 42

    # Record baseline locked test data partition
    baseline_locked_df = split_service.get_locked_test_data(dataset.id)
    baseline_locked_uids = set(baseline_locked_df["row_uid"].tolist())
    baseline_locked_items = set(baseline_locked_df["item_code"].tolist())
    assert len(baseline_locked_uids) == 18

    # 4. SIMULATE UNDERLYING DATA RE-ORDERING (Arbitrary row permutation & reverse order)
    # Shuffle df_original rows so that positional index 0 is no longer row 0
    rng = np.random.default_rng(seed=999)
    permuted_indices = rng.permutation(len(df_original))
    df_reordered = df_original.iloc[permuted_indices].reset_index(drop=True)

    # Overwrite the storage file with the re-ordered dataframe
    reordered_bytes = df_reordered.to_csv(index=False).encode("utf-8")
    storage.save_file(project_id, 1, "reorder_data.csv", reordered_bytes)

    # 5. Call get_development_data() on the physically re-ordered dataset
    post_reorder_dev_df = split_service.get_development_data(dataset.id)
    post_reorder_dev_uids = set(post_reorder_dev_df["row_uid"].tolist())
    post_reorder_dev_items = set(post_reorder_dev_df["item_code"].tolist())

    # PROOF: Development membership is 100% IDENTICAL to baseline despite physical row permutation
    assert post_reorder_dev_uids == baseline_dev_uids, "Split membership failed: row_uid matching broke after re-ordering!"
    assert post_reorder_dev_items == baseline_dev_items, "Feature records corrupted after re-ordering!"
    assert post_reorder_dev_uids.isdisjoint(baseline_locked_uids), "Leakage occurred: Locked test rows leaked into Development after re-ordering!"

    # 6. Call get_locked_test_data() on the physically re-ordered dataset
    post_reorder_locked_df = split_service.get_locked_test_data(dataset.id)
    post_reorder_locked_uids = set(post_reorder_locked_df["row_uid"].tolist())
    post_reorder_locked_items = set(post_reorder_locked_df["item_code"].tolist())

    assert post_reorder_locked_uids == baseline_locked_uids
    assert post_reorder_locked_items == baseline_locked_items
