import io
import secrets
from pathlib import Path
from uuid import UUID
from datetime import datetime, timezone
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.dataset import Dataset
from app.models.dataset_column import DatasetColumn
from app.models.dataset_split import DatasetSplit
from app.models.project import Project
from app.repositories.dataset_repository import DatasetRepository
from app.repositories.dataset_split_repository import DatasetSplitRepository
from app.repositories.project_repository import ProjectRepository
from app.services.storage_service import StorageService, get_storage_service

class DatasetSplitService:
    """
    Service responsible for creating and retrieving the outer split (Development / Locked Test partition).
    
    ARCHITECTURAL INVARIANT (SRS §2.2, §2.17):
    - The outer split is created once per dataset version.
    - Locked Test partition rows are strictly isolated and NEVER accessed by profiling,
      feature engineering, or model training services (Days 3-6).
    - `get_development_data` is the ONLY authorized method downstream services may call.
    - `get_locked_test_data` is reserved exclusively for the Day 7 final evaluation step.
    """

    def __init__(self, db: Session, storage: StorageService | None = None):
        self.db = db
        self.storage = storage or get_storage_service()
        self.dataset_repo = DatasetRepository(db)
        self.split_repo = DatasetSplitRepository(db)
        self.project_repo = ProjectRepository(db)

    def _load_full_dataframe(self, dataset: Dataset) -> pd.DataFrame:
        file_bytes = self.storage.get_file_bytes(dataset.file_path)
        suffix = Path(dataset.file_path).suffix.lower()
        stream = io.BytesIO(file_bytes)

        if suffix in [".csv", ".txt"]:
            try:
                df = pd.read_csv(stream)
            except Exception:
                stream.seek(0)
                df = pd.read_csv(stream, sep=None, engine="python")
        elif suffix in [".xlsx", ".xls"]:
            df = pd.read_excel(stream)
        elif suffix == ".json":
            df = pd.read_json(stream)
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported file format '{suffix}' for dataset parsing."
            )

        if "row_uid" not in df.columns:
            import uuid as py_uuid
            if dataset.content_hash:
                namespace = py_uuid.NAMESPACE_DNS
                df["row_uid"] = [
                    str(py_uuid.uuid5(namespace, f"{dataset.content_hash}_row_{i}"))
                    for i in range(len(df))
                ]
            else:
                df["row_uid"] = [str(py_uuid.uuid4()) for _ in range(len(df))]

        return df

    def create_outer_split(
        self,
        dataset_id: UUID | str,
        locked_test_pct: int = 20,
        seed: int | None = None
    ) -> dict:
        """
        Creates the Development and Locked Test partitions for a given dataset version.
        Enforces:
        - Exact seed recording for deterministic reproducibility.
        - Stratification when structural dtype / cardinality of target column indicates suitability.
        - Single execution per dataset version (idempotency guard).
        - Project pipeline stage update to 'SPLIT'.
        """
        if not (1 <= locked_test_pct <= 99):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="locked_test_pct must be between 1 and 99 percent."
            )

        # 1. Verify dataset exists
        dataset = self.dataset_repo.get_by_id(dataset_id)
        if not dataset:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Dataset not found"
            )

        # 2. Check if outer split already exists for this dataset
        if self.split_repo.has_split(dataset.id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Outer split already exists for this dataset version. Splits are immutable once created."
            )

        total_rows = dataset.row_count
        if total_rows < 2:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Dataset must contain at least 2 rows to perform an outer split."
            )

        # 3. Determine seed (generate securely if not provided)
        effective_seed = seed if seed is not None else secrets.randbelow(2_147_483_647)

        # 4. Determine stratification feasibility based purely on Stage A structural metadata
        is_stratified = False
        target_column_record = (
            self.db.query(DatasetColumn)
            .filter(DatasetColumn.dataset_id == dataset.id, DatasetColumn.is_target == True)
            .first()
        )

        df = self._load_full_dataframe(dataset)
        total_rows = len(df)
        if "row_uid" in df.columns:
            row_items = df["row_uid"].to_numpy()
        else:
            row_items = np.arange(total_rows)

        test_size = locked_test_pct / 100.0

        if target_column_record and target_column_record.column_name in df.columns:
            # Check structural metadata: non-numeric OR low unique count relative to rows
            is_categorical_type = target_column_record.data_type in ["CATEGORICAL", "MIXED"]
            is_low_cardinality = (
                target_column_record.unique_count <= 20 or
                (total_rows > 0 and (target_column_record.unique_count / total_rows) <= 0.05)
            )

            if is_categorical_type or is_low_cardinality:
                # Load the target column to attempt stratified partition
                try:
                    target_series = df[target_column_record.column_name]
                    
                    # Stratification requires at least 2 samples per class
                    value_counts = target_series.value_counts(dropna=False)
                    if (value_counts >= 2).all() and len(value_counts) > 1:
                        dev_idx, test_idx = train_test_split(
                            row_items,
                            test_size=test_size,
                            random_state=effective_seed,
                            stratify=target_series
                        )
                        is_stratified = True
                    else:
                        # Fallback to standard random split if class counts are insufficient
                        dev_idx, test_idx = train_test_split(
                            row_items,
                            test_size=test_size,
                            random_state=effective_seed
                        )
                except Exception:
                    # In case of any stratification failure, fallback to plain random split
                    dev_idx, test_idx = train_test_split(
                        row_items,
                        test_size=test_size,
                        random_state=effective_seed
                    )
            else:
                dev_idx, test_idx = train_test_split(
                    row_items,
                    test_size=test_size,
                    random_state=effective_seed
                )
        else:
            dev_idx, test_idx = train_test_split(
                row_items,
                test_size=test_size,
                random_state=effective_seed
            )

        # 5. Persist partitions (row_uid strings or positional indices)
        dev_indices_list = dev_idx.tolist()
        test_indices_list = test_idx.tolist()
        now = datetime.now(timezone.utc)

        dev_split = DatasetSplit(
            dataset_id=dataset.id,
            split_type="DEVELOPMENT",
            split_seed=effective_seed,
            row_indices=dev_indices_list,
            created_at=now
        )
        test_split = DatasetSplit(
            dataset_id=dataset.id,
            split_type="LOCKED_TEST",
            split_seed=effective_seed,
            row_indices=test_indices_list,
            created_at=now
        )

        self.split_repo.create_splits([dev_split, test_split])

        # 6. Update project pipeline stage to 'SPLIT'
        project = self.project_repo.get_by_id(dataset.project_id)
        if project:
            project.pipeline_stage = "SPLIT"
            self.db.add(project)
            self.db.commit()

        # 7. Return summary ONLY (never return row indices or raw data)
        return {
            "dataset_id": dataset.id,
            "development_rows": len(dev_indices_list),
            "locked_test_rows": len(test_indices_list),
            "locked_test_pct": locked_test_pct,
            "split_seed": effective_seed,
            "is_stratified": is_stratified,
            "created_at": now
        }

    def get_split_summary(self, dataset_id: UUID | str) -> dict | None:
        """
        Returns the outer split summary for a dataset version, or None if no split exists.
        """
        splits = self.split_repo.get_by_dataset(dataset_id)
        if not splits or len(splits) < 2:
            return None

        dev_split = next((s for s in splits if s.split_type == "DEVELOPMENT"), None)
        test_split = next((s for s in splits if s.split_type == "LOCKED_TEST"), None)
        if not dev_split or not test_split:
            return None

        dev_count = len(dev_split.row_indices)
        test_count = len(test_split.row_indices)
        total = dev_count + test_count
        pct = round((test_count / total) * 100) if total > 0 else 0

        # Check if stratification was applied by inspecting target column metadata
        dataset = self.dataset_repo.get_by_id(dataset_id)
        is_stratified = False
        if dataset:
            target_column_record = (
                self.db.query(DatasetColumn)
                .filter(DatasetColumn.dataset_id == dataset.id, DatasetColumn.is_target == True)
                .first()
            )
            if target_column_record:
                is_categorical = target_column_record.data_type in ["CATEGORICAL", "MIXED"]
                is_low_card = (
                    target_column_record.unique_count <= 20 or
                    (total > 0 and (target_column_record.unique_count / total) <= 0.05)
                )
                is_stratified = is_categorical or is_low_card

        return {
            "dataset_id": dev_split.dataset_id,
            "development_rows": dev_count,
            "locked_test_rows": test_count,
            "locked_test_pct": pct,
            "split_seed": dev_split.split_seed,
            "is_stratified": is_stratified,
            "created_at": dev_split.created_at
        }

    def get_development_data(self, dataset_id: UUID | str) -> pd.DataFrame:
        """
        ARCHITECTURAL INVARIANT:
        THIS is the ONLY method any future service (profiling, transformation,
        feature engineering, training - Days 3 to 6) is allowed to call to get data.
        
        Loads the dataset file, filters strictly to DEVELOPMENT row identities,
        and returns a pandas DataFrame.
        """
        dataset = self.dataset_repo.get_by_id(dataset_id)
        if not dataset:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Dataset not found"
            )

        dev_split = self.split_repo.get_by_dataset_and_type(dataset.id, "DEVELOPMENT")
        if not dev_split:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No outer split exists for this dataset. Please create an outer split before requesting development data."
            )

        df = self._load_full_dataframe(dataset)
        dev_indices = dev_split.row_indices
        if dev_indices and isinstance(dev_indices[0], str) and "row_uid" in df.columns:
            return df[df["row_uid"].isin(dev_indices)].reset_index(drop=True)
        return df.iloc[dev_indices].reset_index(drop=True)

    def get_locked_test_data(self, dataset_id: UUID | str) -> pd.DataFrame:
        """
        ARCHITECTURAL INVARIANT (Day 7 Evaluation ONLY):
        This method exists ONLY for internal use by the future single-evaluation step (Day 7).
        It is STRICTLY FORBIDDEN to expose this method through any API endpoint or invoke it
        during Days 2 through 6.
        """
        dataset = self.dataset_repo.get_by_id(dataset_id)
        if not dataset:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Dataset not found"
            )

        test_split = self.split_repo.get_by_dataset_and_type(dataset.id, "LOCKED_TEST")
        if not test_split:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No outer split exists for this dataset."
            )

        df = self._load_full_dataframe(dataset)
        test_indices = test_split.row_indices
        if test_indices and isinstance(test_indices[0], str) and "row_uid" in df.columns:
            return df[df["row_uid"].isin(test_indices)].reset_index(drop=True)
        return df.iloc[test_indices].reset_index(drop=True)

    def get_development_preview(self, dataset_id: UUID | str, limit: int = 10) -> dict:
        """
        Returns the first ~10 rows of the DEVELOPMENT partition only for UI data preview.
        Structurally incapable of returning Locked Test rows.
        """
        dev_df = self.get_development_data(dataset_id)
        preview_df = dev_df.head(limit)
        
        # Replace NaN / NaT values with None for JSON serialization
        clean_records = preview_df.replace({np.nan: None}).to_dict(orient="records")

        return {
            "dataset_id": dataset_id,
            "total_development_rows": len(dev_df),
            "preview_rows": clean_records,
            "columns": list(dev_df.columns)
        }
