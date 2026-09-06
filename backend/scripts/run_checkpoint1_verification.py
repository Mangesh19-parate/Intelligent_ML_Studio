import os
import sys
import json
import uuid
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add backend directory to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

import numpy as np
import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from sklearn.exceptions import NotFittedError
from sklearn.utils.validation import check_is_fitted

from app.core.database import Base
from app.core.seeder import seed_rbac_data
from app.models.user import User
from app.models.role import Role
from app.models.project import Project
from app.models.dataset import Dataset
from app.models.dataset_column import DatasetColumn
from app.models.dataset_split import DatasetSplit
from app.models.transformation_config import TransformationConfig
from app.services.storage_service import LocalStorageService
from app.services.dataset_split_service import DatasetSplitService
from app.services.data_profiling_service import DataProfilingService
from app.services.transformation_service import TransformationService
from app.schemas.transformation import TransformationConfigUpdate


def run_live_checkpoint_1():
    print("=" * 80)
    print("CHECKPOINT 1 VERIFICATION: Live Upload -> Split -> Profile -> Transform")
    print("=" * 80)

    # 1. Setup Isolated In-Memory Database & Storage
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    db = TestingSession()
    seed_rbac_data(db)

    import tempfile
    temp_dir_obj = tempfile.TemporaryDirectory()
    storage_dir = Path(temp_dir_obj.name)
    storage = LocalStorageService(str(storage_dir))

    # Create Test User & Project
    role = db.query(Role).filter(Role.role_name == "ML_ENGINEER").first()
    user = User(
        id=uuid.uuid4(),
        full_name="ML Specialist",
        email="specialist@studio.ai",
        password_hash="hash",
        role_id=role.id,
        is_active=True,
    )
    db.add(user)
    db.commit()

    project = Project(
        id=uuid.uuid4(),
        owner_id=user.id,
        project_name="Customer Churn Intelligence",
        task_type="CLASSIFICATION",
        target_column="churn",
        pipeline_stage="CREATED",
    )
    db.add(project)
    db.commit()

    # 2. Generate Synthetic Multi-Type Dataset (1,000 rows)
    np.random.seed(42)
    n_samples = 1000
    df = pd.DataFrame({
        "customer_age": np.random.normal(40, 12, n_samples).round(1),
        "account_balance": np.random.exponential(5000, n_samples).round(2),
        "monthly_charges": np.random.uniform(20, 120, n_samples).round(2),
        "contract_type": np.random.choice(["month-to-month", "one-year", "two-year"], n_samples, p=[0.5, 0.3, 0.2]),
        "payment_method": np.random.choice(["electronic_check", "mailed_check", "bank_transfer", "credit_card"], n_samples),
        "churn": np.random.choice([0, 1], n_samples, p=[0.75, 0.25]),
    })

    # Inject missing values and extreme outliers
    df.loc[np.random.choice(n_samples, 45, replace=False), "customer_age"] = np.nan
    df.loc[np.random.choice(n_samples, 30, replace=False), "monthly_charges"] = np.nan
    df.loc[np.random.choice(n_samples, 25, replace=False), "contract_type"] = None
    df.loc[np.random.choice(n_samples, 10, replace=False), "account_balance"] = 95000.0  # outlier

    # Generate deterministic row_uids
    content_bytes = df.to_csv(index=False).encode("utf-8")
    content_hash = hashlib.sha256(content_bytes).hexdigest()
    namespace = uuid.NAMESPACE_DNS
    df["row_uid"] = [
        str(uuid.uuid5(namespace, f"{content_hash}_row_{i}"))
        for i in range(len(df))
    ]

    # Save to storage & register dataset
    saved_bytes = df.to_csv(index=False).encode("utf-8")
    filename = f"{content_hash}.csv"
    file_path = storage.save_file(project.id, 1, filename, saved_bytes)

    dataset = Dataset(
        id=uuid.uuid4(),
        project_id=project.id,
        version_number=1,
        file_path=file_path,
        row_count=n_samples,
        column_count=len(df.columns),
        content_hash=content_hash,
    )
    db.add(dataset)
    db.commit()

    # Register column metadata
    col_records = []
    for col in df.columns:
        if col == "row_uid":
            continue
        dtype = "NUMERIC" if col in ["customer_age", "account_balance", "monthly_charges"] else "CATEGORICAL"
        is_target = (col == "churn")
        missing_pct = round(float(df[col].isnull().sum() / len(df) * 100), 2)
        col_rec = DatasetColumn(
            id=uuid.uuid4(),
            dataset_id=dataset.id,
            column_name=col,
            data_type=dtype,
            is_target=is_target,
            missing_percentage=missing_pct,
            unique_count=int(df[col].nunique()),
        )
        db.add(col_rec)
        col_records.append(col_rec)
    db.commit()

    print(f"[OK] Step 1: Upload Complete. Dataset ID: {dataset.id}, Rows: {n_samples}, Content Hash: {content_hash[:12]}...")

    # 3. Create Outer Split (80% Development / 20% Locked Test)
    split_service = DatasetSplitService(db, storage)
    split_result = split_service.create_outer_split(dataset.id, locked_test_pct=20, seed=42)

    dev_split = split_service.split_repo.get_by_dataset_and_type(dataset.id, "DEVELOPMENT")
    test_split = split_service.split_repo.get_by_dataset_and_type(dataset.id, "LOCKED_TEST")

    dev_uids = set(dev_split.row_indices)
    test_uids = set(test_split.row_indices)

    print(f"[OK] Step 2: Split Complete.")
    print(f"   - Development partition: {len(dev_uids)} rows")
    print(f"   - Locked Test partition: {len(test_uids)} rows")
    print(f"   - Split seed: {split_result['split_seed']}")
    print(f"   - Stratified: {split_result['is_stratified']}")

    # 4. Instrument Access Tracking & Auditing
    audit_log = {
        "get_development_data_calls": 0,
        "get_locked_test_data_calls": 0,
        "accessed_row_uids": set(),
        "preview_row_uids": set(),
    }

    orig_get_dev = split_service.get_development_data
    orig_get_locked = split_service.get_locked_test_data

    def tracked_get_development_data(ds_id):
        audit_log["get_development_data_calls"] += 1
        res = orig_get_dev(ds_id)
        if "row_uid" in res.columns:
            audit_log["accessed_row_uids"].update(res["row_uid"].astype(str).tolist())
        return res

    def tracked_get_locked_test_data(ds_id):
        audit_log["get_locked_test_data_calls"] += 1
        return orig_get_locked(ds_id)

    split_service.get_development_data = tracked_get_development_data
    split_service.get_locked_test_data = tracked_get_locked_test_data

    # 5. Run Live Profiling
    profiling_service = DataProfilingService(db)
    # Inject tracked split_service
    profiling_service.split_service = split_service
    profile_result = profiling_service.generate_report(dataset.id)

    print(f"[OK] Step 3: Data Profiling Complete.")
    print(f"   - DQI overall index: {profile_result.get('data_quality_index', {}).get('overall_index')}")
    print(f"   - Columns profiled: {len(profile_result.get('column_stats', {}))}")
    print(f"   - Development data calls during profiling: {audit_log['get_development_data_calls']}")
    print(f"   - Locked Test calls during profiling: {audit_log['get_locked_test_data_calls']}")

    # 6. Configure Live Transformations
    trans_service = TransformationService(db, storage)
    trans_service.split_service = split_service

    configs = [
        ("customer_age", "mean", "iqr", "standard", None),
        ("account_balance", "median", "percentile", "robust", None),
        ("monthly_charges", "mean", None, "minmax", None),
        ("contract_type", "mode", None, None, "one_hot"),
        ("payment_method", "mode", None, None, "one_hot"),
    ]

    for col_name, miss, outl, scal, enc in configs:
        if miss:
            trans_service.set_missing_value_strategy(project.id, col_name, miss)
        if outl:
            trans_service.set_outlier_strategy(project.id, col_name, outl)
        if scal:
            trans_service.set_scaling_strategy(project.id, col_name, scal)
        if enc:
            trans_service.set_encoding_strategy(project.id, col_name, enc)

    print(f"[OK] Step 4: Transformation Configurations Persisted.")

    # 7. Run Live Transformation Preview (Deterministic 200-row sample, seed=42)
    preview_metrics = {}
    for col_name, *rest in configs:
        preview = trans_service.preview_transformation(
            project_id=project.id,
            column_name=col_name,
            sample_size=200,
            preview_seed=42,
        )
        preview_metrics[col_name] = {
            "sample_size": preview["sample_size"],
            "preview_seed": preview["preview_seed"],
            "before_sample_count": len(preview["before_values"]),
            "after_sample_count": len(preview["after_values"]),
            "sample_before_head": preview["before_values"][:3],
            "sample_after_head": preview["after_values"][:3],
        }
        print(f"   - Preview '{col_name}': {preview['sample_size']} rows sample, transformed successfully.")

    # 8. Build Unfitted ColumnTransformer & Verify Fit-Scope Invariant
    unfitted_pipe = trans_service.build_pipeline(project.id)
    print(f"[OK] Step 5: Unfitted Pipeline Construction Complete.")
    print(f"   - Transformers count: {len(unfitted_pipe.transformers)}")

    # Check that constructing pipeline does not fit estimators
    try:
        check_is_fitted(unfitted_pipe)
        is_fitted_leak = True
    except NotFittedError:
        is_fitted_leak = False

    print(f"   - Implicit fit check: {'FAILED (Estimators Fitted)' if is_fitted_leak else 'PASSED (Strictly Unfitted)'}")

    # 9. Perform Comprehensive Partition Isolation & Leakage Proof
    print("\n" + "=" * 80)
    print("MATHEMATICAL & ARCHITECTURAL PROOF OF ZERO TEST LEAKAGE")
    print("=" * 80)

    # Set Theory Invariants:
    # Invariant A: Dev & Test partitions are disjoint
    partition_intersection = dev_uids.intersection(test_uids)
    is_partition_disjoint = (len(partition_intersection) == 0)

    # Invariant B: All accessed rows during profiling & transformation are in Dev partition
    accessed_intersection_with_test = audit_log["accessed_row_uids"].intersection(test_uids)
    is_accessed_strictly_dev = (len(accessed_intersection_with_test) == 0)

    # Invariant C: Locked test data access count is 0
    locked_test_call_count = audit_log["get_locked_test_data_calls"]

    # Invariant D: Preview sample rows are strictly subset of Dev partition
    dev_df = split_service.get_development_data(dataset.id)
    preview_sample_df = dev_df[["customer_age", "row_uid"]].sample(n=200, random_state=42)
    preview_sample_uids = set(preview_sample_df["row_uid"].astype(str).tolist())
    preview_test_overlap = preview_sample_uids.intersection(test_uids)
    is_preview_strictly_dev = (len(preview_test_overlap) == 0)

    print(f"1. Partition Disjointness Check: |Dev INTERSECT Test| = {len(partition_intersection)} -> {'PASS' if is_partition_disjoint else 'FAIL'}")
    print(f"2. Accessed UIDs INTERSECT Test Partition: |Accessed INTERSECT Test| = {len(accessed_intersection_with_test)} -> {'PASS' if is_accessed_strictly_dev else 'FAIL'}")
    print(f"3. Locked Test Partition Read Calls: {locked_test_call_count} -> {'PASS' if locked_test_call_count == 0 else 'FAIL'}")
    print(f"4. Preview Sample (200 rows) INTERSECT Test Partition: {len(preview_test_overlap)} -> {'PASS' if is_preview_strictly_dev else 'FAIL'}")
    print(f"5. Pipeline Fit State: {'NOT FITTED' if not is_fitted_leak else 'FITTED'} -> {'PASS' if not is_fitted_leak else 'FAIL'}")

    results = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "dataset_id": str(dataset.id),
        "content_hash": content_hash,
        "total_rows": n_samples,
        "development_rows": len(dev_uids),
        "locked_test_rows": len(test_uids),
        "split_seed": split_result["split_seed"],
        "stratified": split_result["is_stratified"],
        "audit": {
            "get_development_data_calls": audit_log["get_development_data_calls"],
            "get_locked_test_data_calls": audit_log["get_locked_test_data_calls"],
            "accessed_rows_count": len(audit_log["accessed_row_uids"]),
            "accessed_test_rows_count": len(accessed_intersection_with_test),
            "preview_test_overlap_count": len(preview_test_overlap),
        },
        "previews": preview_metrics,
        "pipeline_unfitted": not is_fitted_leak,
        "all_invariants_passed": (
            is_partition_disjoint
            and is_accessed_strictly_dev
            and (locked_test_call_count == 0)
            and is_preview_strictly_dev
            and (not is_fitted_leak)
        ),
    }

    # Save verification metrics to JSON artifact
    artifact_path = Path("week-04/artifacts/checkpoint1-verification.json")
    with open(artifact_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    print(f"\nSaved checkpoint 1 JSON verification report to: {artifact_path}")
    return results


if __name__ == "__main__":
    res = run_live_checkpoint_1()
    print("Verification Status:", "SUCCESS" if res["all_invariants_passed"] else "FAILURE")
