import io
import hashlib
from pathlib import Path
from uuid import UUID
from decimal import Decimal
from fastapi import UploadFile, HTTPException, status
import pandas as pd
from sqlalchemy.orm import Session

from app.models.dataset import Dataset
from app.models.dataset_column import DatasetColumn
from app.models.project import Project
from app.models.user import User
from app.repositories.dataset_repository import DatasetRepository
from app.repositories.project_repository import ProjectRepository
from app.services.storage_service import StorageService, get_storage_service

class DatasetService:
    """
    Dataset management and structural schema detection service.
    
    INVARIANT ENFORCEMENT:
    Per Day 1 architectural constraints, schema detection is STRUCTURAL ONLY:
    - Computes row/column counts
    - Infers basic dtypes (NUMERIC, CATEGORICAL, DATETIME, MIXED)
    - Computes unique_count and missing_percentage purely from null count and nunique
    - Explicitly NO correlation analysis, NO distribution shape, NO profiling, NO health scoring, NO task suggestion.
    """

    def __init__(self, db: Session, storage: StorageService | None = None):
        self.db = db
        self.storage = storage or get_storage_service()
        self.dataset_repo = DatasetRepository(db)
        self.project_repo = ProjectRepository(db)

    def _parse_dataframe_from_bytes(self, filename: str, content: bytes) -> pd.DataFrame:
        suffix = Path(filename).suffix.lower()
        stream = io.BytesIO(content)

        try:
            if suffix in [".csv", ".txt"]:
                # Try standard parsing with pandas
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
                    detail=f"Unsupported file format '{suffix}'. Allowed formats: .csv, .xlsx, .json"
                )
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Structural validation error: Failed to parse tabular dataset. Details: {str(e)}"
            )

        if df.empty or len(df.columns) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Dataset is empty or has zero columns."
            )

        return df

    def _infer_column_dtype(self, series: pd.Series) -> str:
        """
        Infers structural data type: NUMERIC, CATEGORICAL, DATETIME, MIXED.
        Strictly structural — no semantic or target-dependent profiling.
        """
        non_null_series = series.dropna()
        if len(non_null_series) == 0:
            return "CATEGORICAL"

        # Check for boolean type
        if pd.api.types.is_bool_dtype(series):
            return "CATEGORICAL"

        # Check for numeric type
        if pd.api.types.is_numeric_dtype(series):
            return "NUMERIC"

        # Check for datetime type
        if pd.api.types.is_datetime64_any_dtype(series):
            return "DATETIME"

        # Attempt datetime conversion for object/string columns if they look like timestamps
        if pd.api.types.is_string_dtype(series) or pd.api.types.is_object_dtype(series):
            # Sample up to 50 items to check if all parse as datetime
            sample = non_null_series.head(50)
            try:
                converted = pd.to_datetime(sample, errors="raise")
                # If sample parsed cleanly, verify entire series or classify as DATETIME
                return "DATETIME"
            except Exception:
                pass

            # Check for mixed python types in object columns
            type_set = {type(v) for v in non_null_series.head(100)}
            if len(type_set) > 1:
                return "MIXED"

            return "CATEGORICAL"

        return "CATEGORICAL"

    def upload(
        self,
        project_id: UUID | str,
        filename: str,
        content: bytes,
        uploaded_by_id: UUID | str | None = None
    ) -> Dataset:
        # 1. Verify project exists
        project = self.project_repo.get_by_id(project_id)
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found"
            )

        # 2. Validate structural parseability
        df = self._parse_dataframe_from_bytes(filename, content)
        row_count, column_count = df.shape

        # 3. Determine next version number for project
        next_version = self.dataset_repo.get_next_version_number(project.id)

        # 4. Compute content hash (SHA-256) for file integrity
        content_hash = hashlib.sha256(content).hexdigest()

        # 5. Save file via StorageService
        saved_file_path = self.storage.save_file(
            project_id=project.id,
            version=next_version,
            filename=filename,
            content=content
        )

        # 6. Create Dataset record
        dataset = Dataset(
            project_id=project.id,
            file_path=saved_file_path,
            version_number=next_version,
            row_count=row_count,
            column_count=column_count,
            stage="RAW",
            content_hash=content_hash,
            uploaded_by=uploaded_by_id,
        )
        created_dataset = self.dataset_repo.create(dataset)
        return created_dataset

    def detect_structural_schema(self, dataset_id: UUID | str) -> list[DatasetColumn]:
        """
        Reads stored dataset and populates dataset_columns with structural dtypes,
        unique counts, and missing percentages.
        """
        dataset = self.dataset_repo.get_by_id(dataset_id)
        if not dataset:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Dataset not found"
            )

        project = self.project_repo.get_by_id(dataset.project_id)
        target_column_name = project.target_column.strip().lower() if project and project.target_column else None

        # Read dataset bytes from storage
        file_bytes = self.storage.get_file_bytes(dataset.file_path)
        df = self._parse_dataframe_from_bytes(Path(dataset.file_path).name, file_bytes)

        total_rows = len(df)
        columns_to_create: list[DatasetColumn] = []

        for col_name in df.columns:
            series = df[col_name]
            null_count = int(series.isna().sum())
            unique_count = int(series.nunique(dropna=True))
            missing_pct = round(Decimal((null_count / total_rows) * 100), 2) if total_rows > 0 else Decimal("0.00")
            
            inferred_dtype = self._infer_column_dtype(series)
            is_target = bool(target_column_name and str(col_name).strip().lower() == target_column_name)

            column_record = DatasetColumn(
                dataset_id=dataset.id,
                column_name=str(col_name),
                data_type=inferred_dtype,
                unique_count=unique_count,
                missing_percentage=missing_pct,
                is_target=is_target,
            )
            columns_to_create.append(column_record)

        created_columns = self.dataset_repo.create_columns_bulk(columns_to_create)
        return created_columns

    def get_datasets_for_project(self, project_id: UUID | str) -> list[Dataset]:
        return self.dataset_repo.get_by_project(project_id)

    def get_columns_for_dataset(self, dataset_id: UUID | str) -> list[DatasetColumn]:
        return self.dataset_repo.get_columns_by_dataset(dataset_id)
