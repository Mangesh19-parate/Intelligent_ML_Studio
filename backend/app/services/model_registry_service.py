import io
import os
import pickle
import hashlib
from uuid import UUID
from pathlib import Path
from typing import Any
import joblib
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.trained_model import TrainedModel
from app.models.experiment import Experiment
from app.models.dataset import Dataset
from app.models.dataset_column import DatasetColumn
from app.models.feature_selection_snapshot import FeatureSelectionSnapshot


class ModelRegistryService:
    """
    Model Registry Service (Day 10).
    
    ARCHITECTURAL NOTE (SRS §2.14 / §2.16):
    - get_input_schema: Derives the expected schema from the model's feature_selection_snapshot
      cross-referenced against dataset_columns. This authoritative schema is used by
      schema_locked gate checks and live prediction payload validation.
    - download: Checksum-verified artifact loader with on-the-fly re-serialization
      in requested format ('pkl' or 'joblib').
    """

    def __init__(self, db: Session):
        self.db = db

    def get_input_schema(self, model_id: UUID | str) -> dict[str, str]:
        """
        Derives expected input schema `{feature_name: dtype}` from the model's
        `feature_selection_snapshots.final_selected_features` cross-referenced
        against `dataset_columns` for each selected feature's structural dtype.
        """
        model = self.db.query(TrainedModel).filter(TrainedModel.id == model_id).first()
        if not model:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Trained model not found",
            )

        experiment = self.db.query(Experiment).filter(Experiment.id == model.experiment_id).first()
        if not experiment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Parent experiment not found",
            )

        # 1. Locate FeatureSelectionSnapshot
        fs_snapshot = None
        if model.feature_selection_snapshot_id:
            fs_snapshot = self.db.query(FeatureSelectionSnapshot).filter(
                FeatureSelectionSnapshot.id == model.feature_selection_snapshot_id
            ).first()
        
        if not fs_snapshot and experiment.feature_selection_snapshot_id:
            fs_snapshot = self.db.query(FeatureSelectionSnapshot).filter(
                FeatureSelectionSnapshot.id == experiment.feature_selection_snapshot_id
            ).first()

        if not fs_snapshot:
            fs_snapshot = (
                self.db.query(FeatureSelectionSnapshot)
                .filter(FeatureSelectionSnapshot.experiment_id == experiment.id)
                .order_by(FeatureSelectionSnapshot.created_at.desc())
                .first()
            )

        if not fs_snapshot or not fs_snapshot.final_selected_features:
            return {}

        selected_features = fs_snapshot.final_selected_features
        if not isinstance(selected_features, list) or len(selected_features) == 0:
            return {}

        # 2. Lookup Dataset Columns
        dataset = (
            self.db.query(Dataset)
            .filter(Dataset.project_id == experiment.project_id)
            .order_by(Dataset.version_number.desc())
            .first()
        )
        if not dataset:
            return {str(f): "NUMERIC" for f in selected_features}

        dataset_cols = (
            self.db.query(DatasetColumn)
            .filter(DatasetColumn.dataset_id == dataset.id)
            .all()
        )
        col_type_map = {col.column_name: col.data_type for col in dataset_cols}

        schema: dict[str, str] = {}
        for feat in selected_features:
            feat_str = str(feat)
            schema[feat_str] = col_type_map.get(feat_str, "NUMERIC")

        return schema

    def download(self, model_id: UUID | str, format: str = "joblib") -> tuple[io.BytesIO, str, str]:
        """
        Loads the fitted pipeline artifact with strict SHA-256 integrity verification,
        and re-serializes in requested format ('pkl' or 'joblib').
        
        Returns:
            (file_stream, filename, media_type)
        """
        fmt_normalized = format.lower().strip()
        if fmt_normalized not in {"pkl", "joblib", "pickle"}:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid format '{format}'. Allowed formats are 'pkl' and 'joblib'.",
            )

        model = self.db.query(TrainedModel).filter(TrainedModel.id == model_id).first()
        if not model:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Trained model not found",
            )

        if not model.artifact_path:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="This model has no persisted artifact — download is only available for the winning model of a completed experiment",
            )

        artifact_file = Path(model.artifact_path)
        if not artifact_file.exists():
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Model artifact file not found at '{model.artifact_path}'",
            )

        # Cryptographic Checksum Re-verification
        hasher = hashlib.sha256()
        with open(artifact_file, "rb") as f:
            while chunk := f.read(65536):
                hasher.update(chunk)
        disk_checksum = hasher.hexdigest()

        if model.artifact_checksum and disk_checksum != model.artifact_checksum:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Artifact integrity check failed: SHA-256 checksum mismatch. Disk hash ({disk_checksum[:12]}...) != DB record ({model.artifact_checksum[:12]}...).",
            )

        try:
            artifact = joblib.load(artifact_file)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Failed to load model artifact: {str(e)}",
            )

        buffer = io.BytesIO()
        safe_alg_name = "".join(c for c in model.algorithm_name if c.isalnum() or c in ("_", "-"))
        short_id = str(model.id)[:8]

        if fmt_normalized in {"pkl", "pickle"}:
            pickle.dump(artifact, buffer)
            buffer.seek(0)
            filename = f"model_{safe_alg_name}_{short_id}.pkl"
            media_type = "application/octet-stream"
        else:
            joblib.dump(artifact, buffer)
            buffer.seek(0)
            filename = f"model_{safe_alg_name}_{short_id}.joblib"
            media_type = "application/octet-stream"

        return buffer, filename, media_type
