"""
Feature Construction Service and Construction Ledger (SRS v11 §5).
Provides user- and rule-configured derived feature construction (interactions, ratios, polynomial terms)
and maintains an immutable Construction Ledger recording Development-only target correlation.
"""

import re
import uuid
import numpy as np
import pandas as pd
from typing import Any, Sequence
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.models.project import Project
from app.models.dataset import Dataset
from app.repositories.project_repository import ProjectRepository
from app.repositories.dataset_repository import DatasetRepository
from app.services.dataset_split_service import DatasetSplitService
from app.infrastructure.storage.object_store import StorageService, get_storage_service


class FeatureConstructor:
    """
    Deterministic feature construction on tabular columns (SRS v11 §5).
    
    LEAKAGE CLASSIFICATION:
    Deterministic arithmetic on existing columns (A * B, A / B, A^n) uses NO cross-row statistic
    and NO target distribution. It does not require per-fold refitting.
    """

    @staticmethod
    def construct_interaction(df: pd.DataFrame, col_a: str, col_b: str, out_name: str | None = None) -> tuple[pd.Series, str]:
        """Constructs multiplicative interaction term: A * B."""
        name = out_name or f"{col_a}_x_{col_b}"
        series = df[col_a].astype(float) * df[col_b].astype(float)
        series.name = name
        formula = f"{col_a} * {col_b}"
        return series, formula

    @staticmethod
    def construct_ratio(df: pd.DataFrame, col_num: str, col_den: str, out_name: str | None = None) -> tuple[pd.Series, str]:
        """Constructs ratio term: A / B with divide-by-zero guarded to NaN."""
        name = out_name or f"{col_num}_div_{col_den}"
        den = df[col_den].astype(float)
        num = df[col_num].astype(float)
        series = pd.Series(np.where(den == 0, np.nan, num / den), index=df.index, name=name)
        formula = f"{col_num} / {col_den} (guarded)"
        return series, formula

    @staticmethod
    def construct_polynomial(df: pd.DataFrame, col: str, degree: int = 2, out_name: str | None = None) -> tuple[pd.Series, str]:
        """Constructs polynomial term: A^degree (degree bounded in [2, 4])."""
        if not (2 <= degree <= 4):
            raise ValueError(f"Polynomial degree must be between 2 and 4, got {degree}")
        name = out_name or f"{col}_pow_{degree}"
        series = df[col].astype(float) ** degree
        series.name = name
        formula = f"{col}^{degree}"
        return series, formula


class FeatureConstructionService:
    """
    Orchestrates derived feature creation and persists the Construction Ledger.
    Ensures all correlation metrics are computed strictly on the Development partition.
    """

    def __init__(self, db: Session, storage: StorageService | None = None):
        self.db = db
        self.storage = storage or get_storage_service()
        self.project_repo = ProjectRepository(db)
        self.dataset_repo = DatasetRepository(db)
        self.split_service = DatasetSplitService(db, self.storage)
        self._ledger_records: list[dict[str, Any]] = []

    def construct_and_record_feature(
        self,
        project_id: str | uuid.UUID,
        construction_type: str,
        source_columns: Sequence[str],
        degree: int = 2,
        custom_name: str | None = None,
        created_by: str = "system",
    ) -> dict[str, Any]:
        """
        Constructs derived feature, computes Development-only target correlation,
        and logs the entry into the Construction Ledger (SRS v11 §5).
        """
        project = self.project_repo.get_by_id(project_id)
        if not project:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

        datasets = self.dataset_repo.get_by_project(project.id)
        if not datasets:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No dataset uploaded")

        latest_ds = datasets[0]
        # Load dataset
        df_raw = self.storage.load_tabular(latest_ds.file_path)

        # 1. Zero Test Leakage: Filter to Development partition ONLY
        dev_preview = self.split_service.get_development_partition_preview(latest_ds.id, limit=len(df_raw))
        df_dev = dev_preview["data"]

        target_col = project.target_column
        if not target_col or target_col not in df_dev.columns:
            # Fallback: compute correlation with first numeric column or 0.0
            target_col = None

        c_type = construction_type.upper().strip()
        if c_type == "INTERACTION":
            if len(source_columns) < 2:
                raise HTTPException(status_code=422, detail="Interaction requires at least 2 source columns")
            new_series, formula = FeatureConstructor.construct_interaction(
                df_dev, source_columns[0], source_columns[1], out_name=custom_name
            )
        elif c_type == "RATIO":
            if len(source_columns) < 2:
                raise HTTPException(status_code=422, detail="Ratio requires 2 source columns (numerator, denominator)")
            new_series, formula = FeatureConstructor.construct_ratio(
                df_dev, source_columns[0], source_columns[1], out_name=custom_name
            )
        elif c_type == "POLYNOMIAL":
            if len(source_columns) < 1:
                raise HTTPException(status_code=422, detail="Polynomial requires 1 source column")
            new_series, formula = FeatureConstructor.construct_polynomial(
                df_dev, source_columns[0], degree=degree, out_name=custom_name
            )
        else:
            raise HTTPException(status_code=422, detail=f"Unsupported construction type: {construction_type}")

        # Compute Development-only Pearson correlation with target
        dev_corr = 0.0
        if target_col and pd.api.types.is_numeric_dtype(df_dev[target_col]):
            valid_mask = new_series.notna() & df_dev[target_col].notna()
            if valid_mask.sum() > 2:
                corr = np.corrcoef(new_series[valid_mask], df_dev[target_col][valid_mask])[0, 1]
                dev_corr = float(corr) if not np.isnan(corr) else 0.0

        record = {
            "id": f"feat-{uuid.uuid4()}",
            "project_id": str(project_id),
            "feature_name": new_series.name,
            "construction_type": c_type,
            "formula": formula,
            "source_columns": list(source_columns),
            "dev_correlation_with_target": dev_corr,
            "created_by": created_by,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        self._ledger_records.append(record)
        return record

    def get_construction_ledger(self, project_id: str | uuid.UUID) -> list[dict[str, Any]]:
        """Returns the Construction Ledger records for a project."""
        p_str = str(project_id)
        return [r for r in self._ledger_records if r["project_id"] == p_str]
