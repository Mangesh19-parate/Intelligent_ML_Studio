import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

import json
import hashlib
from uuid import uuid4
import numpy as np
import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from app.core.database import Base, get_db
from app.core.seeder import seed_rbac_data
from app.core.config import settings
from app.models.role import Role
from app.models.user import User
from app.models.project import Project
from app.models.dataset import Dataset
from app.models.dataset_column import DatasetColumn
from app.models.dataset_split import DatasetSplit
from app.models.transformation_config import TransformationConfig
from app.models.transformation_snapshot import TransformationSnapshot
from app.models.feature_selection_snapshot import FeatureSelectionSnapshot
from app.models.experiment import Experiment
from app.models.trained_model import TrainedModel
from app.services.experiment_service import ExperimentService
from app.services.dataset_split_service import DatasetSplitService
from app.services.environment_capture_service import EnvironmentCaptureService
from scripts.backfill_pre_day8_lineage import backfill_experiments
from app.main import app

def run_demo():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    db = TestingSession()
    seed_rbac_data(db)

    role = db.query(Role).first()
    user = User(
        id=uuid4(),
        full_name="Lead ML Engineer",
        email="lead_mle@mlstudio.io",
        password_hash="fakehash123",
        role_id=role.id,
        is_active=True,
    )
    db.add(user)
    db.commit()

    project = Project(
        id=uuid4(),
        owner_id=user.id,
        project_name="Customer Churn Lineage Demo",
        task_type="CLASSIFICATION",
        target_column="churn",
        pipeline_stage="SPLIT",
    )
    db.add(project)
    db.commit()

    # Synthetic classification data
    np.random.seed(42)
    n = 150
    df = pd.DataFrame({
        "age": np.random.uniform(18, 70, n),
        "tenure_months": np.random.uniform(1, 60, n),
        "monthly_spend": np.random.uniform(20, 200, n),
        "contract_type": np.random.choice(["MONTHLY", "ANNUAL", "TWO_YEAR"], n),
        "churn": np.random.choice([0, 1], n, p=[0.7, 0.3]),
    })
    csv_bytes = df.to_csv(index=False).encode("utf-8")
    content_hash = hashlib.sha256(csv_bytes).hexdigest()

    from app.services.storage_service import get_storage_service
    storage = get_storage_service()
    saved_path = storage.save_file(project.id, 1, "demo_churn.csv", csv_bytes)

    dataset = Dataset(
        id=uuid4(),
        project_id=project.id,
        version_number=1,
        file_path=saved_path,
        row_count=n,
        column_count=5,
        content_hash=content_hash,
    )
    db.add(dataset)
    db.commit()

    for col in df.columns:
        db.add(
            DatasetColumn(
                id=uuid4(),
                dataset_id=dataset.id,
                column_name=col,
                data_type="NUMERIC" if col != "contract_type" else "CATEGORICAL",
                unique_count=len(df[col].unique()),
                missing_percentage=0.0,
                is_target=(col == "churn"),
            )
        )

    dev_split = DatasetSplit(
        id=uuid4(),
        dataset_id=dataset.id,
        split_type="DEVELOPMENT",
        split_seed=42,
        row_indices=list(range(120)),
    )
    test_split = DatasetSplit(
        id=uuid4(),
        dataset_id=dataset.id,
        split_type="LOCKED_TEST",
        split_seed=42,
        row_indices=list(range(120, 150)),
    )
    db.add_all([dev_split, test_split])

    t1 = TransformationConfig(
        id=uuid4(), project_id=project.id, column_name="monthly_spend", scaling_strategy="STANDARD", is_active=True
    )
    t2 = TransformationConfig(
        id=uuid4(), project_id=project.id, column_name="contract_type", encoding_strategy="ONE_HOT", is_active=True
    )
    db.add_all([t1, t2])
    db.commit()

    service = ExperimentService(db)
    exp_res = service.run_experiment(
        project_id=project.id,
        algorithms=["LogisticRegression", "RandomForestClassifier", "GradientBoostingClassifier"],
        folds=3,
        seed=42,
        selection_metric="f1_macro",
        selection_direction="MAXIMIZE",
        auto_finalize=True,
    )

    lineage = service.get_experiment_lineage(exp_res["experiment_id"])
    print("=== COMPLETE GET /experiments/{id}/lineage JSON RESPONSE ===")
    print(json.dumps(lineage, indent=2))

if __name__ == "__main__":
    run_demo()
