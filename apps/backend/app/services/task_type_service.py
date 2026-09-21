from uuid import UUID
import numpy as np
import pandas as pd
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.models.project import Project
from app.models.dataset import Dataset
from app.models.dataset_column import DatasetColumn
from app.repositories.project_repository import ProjectRepository
from app.repositories.dataset_repository import DatasetRepository
from app.services.dataset_split_service import DatasetSplitService

class TaskTypeDetectionService:
    """
    Stage B Task-Type Detection (Distributional Half per SRS §2.4).
    Operates strictly on the Development partition obtained via DatasetSplitService.get_development_data.
    """

    def __init__(self, db: Session):
        self.db = db
        self.project_repo = ProjectRepository(db)
        self.dataset_repo = DatasetRepository(db)
        self.split_service = DatasetSplitService(db)

    def suggest_task_type(self, dataset_id: UUID | str) -> dict:
        dataset = self.dataset_repo.get_by_id(dataset_id)
        if not dataset:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Dataset not found"
            )

        project = self.project_repo.get_by_id(dataset.project_id)
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found"
            )

        # 1. Retrieve Development partition data ONLY
        dev_df = self.split_service.get_development_data(dataset.id)

        # 2. Determine target column
        target_col_name = project.target_column
        if not target_col_name:
            target_col_record = (
                self.db.query(DatasetColumn)
                .filter(DatasetColumn.dataset_id == dataset.id, DatasetColumn.is_target == True)
                .first()
            )
            if target_col_record:
                target_col_name = target_col_record.column_name

        if not target_col_name or target_col_name not in dev_df.columns:
            return {
                "suggested_task_type": "UNDETERMINED",
                "confidence": "AMBIGUOUS",
                "unique_count": 0,
                "unique_ratio": 0.0,
                "sample_values": [],
                "target_column": target_col_name,
                "message": "Target column is not set or not found in dataset columns."
            }

        target_series = dev_df[target_col_name].dropna()
        row_count = len(target_series)

        if row_count == 0:
            return {
                "suggested_task_type": "UNDETERMINED",
                "confidence": "AMBIGUOUS",
                "unique_count": 0,
                "unique_ratio": 0.0,
                "sample_values": [],
                "target_column": target_col_name,
                "message": "Target column contains only null values in Development partition."
            }

        unique_vals = target_series.unique()
        unique_count = len(unique_vals)
        unique_ratio = unique_count / row_count
        sample_vals = [
            val.item() if hasattr(val, "item") else val
            for val in target_series.head(5).tolist()
        ]

        # Stage B decision procedure (SRS §2.4)
        is_numeric = pd.api.types.is_numeric_dtype(target_series)

        if not is_numeric:
            # Rule 1: Non-numeric target -> CLASSIFICATION
            suggested_task_type = "CLASSIFICATION"
            confidence = "HIGH"
        else:
            # Rule 2: Numeric target
            # Check if values are all integer-like (e.g. 1.0, 2.0 or int dtype)
            try:
                non_integer_values = not bool(np.all(target_series.apply(lambda x: float(x).is_integer())))
            except Exception:
                non_integer_values = True

            # a. unique_count <= 20 AND unique_ratio < 0.05 -> CLASSIFICATION
            # b. unique_count > 20 AND (non-integer values OR unique_ratio >= 0.05) -> REGRESSION
            # c. otherwise -> AMBIGUOUS
            if unique_count <= 20 and unique_ratio < 0.05:
                suggested_task_type = "CLASSIFICATION"
                # Boundary is 0.05. If unique_ratio <= 0.025 (> 2.5% margin), HIGH; else MEDIUM
                if (0.05 - unique_ratio) >= 0.025:
                    confidence = "HIGH"
                else:
                    confidence = "MEDIUM"
            elif unique_count > 20 and (non_integer_values or unique_ratio >= 0.05):
                suggested_task_type = "REGRESSION"
                # If non_integer floats or unique_ratio >= 0.10 (more than 5 percentage points above 0.05), HIGH; else MEDIUM
                if non_integer_values or unique_ratio >= 0.10:
                    confidence = "HIGH"
                else:
                    confidence = "MEDIUM"
            else:
                suggested_task_type = "UNDETERMINED"
                confidence = "AMBIGUOUS"

        # Update project task_type and confidence
        if confidence == "AMBIGUOUS" or suggested_task_type == "UNDETERMINED":
            # Do NOT silently auto-set task_type; keep UNDETERMINED
            project.task_type = "UNDETERMINED"
            project.task_type_confidence = "AMBIGUOUS"
        else:
            project.task_type = suggested_task_type
            project.task_type_confidence = confidence

        self.db.add(project)
        self.db.commit()
        self.db.refresh(project)

        return {
            "suggested_task_type": suggested_task_type,
            "confidence": confidence,
            "unique_count": unique_count,
            "unique_ratio": round(float(unique_ratio), 4),
            "sample_values": sample_vals,
            "target_column": target_col_name,
            "is_ambiguous": confidence == "AMBIGUOUS"
        }
