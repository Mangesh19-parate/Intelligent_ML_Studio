import io
import os
import hashlib
import uuid
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID
from typing import Any

import joblib
import numpy as np
import pandas as pd
import shap
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.trained_model import TrainedModel
from app.models.explainability_summary import ExplainabilitySummary
from app.models.experiment import Experiment
from app.models.dataset import Dataset
from app.repositories.experiment_repository import ExperimentRepository
from app.repositories.dataset_repository import DatasetRepository
from app.services.dataset_split_service import DatasetSplitService
from app.schemas.explainability import (
    GlobalExplainabilityResponse,
    LocalExplainabilityResponse,
)


class ExplainabilityService:
    """
    Model Explainability Service (Day 9).
    
    ARCHITECTURAL INVARIANTS (SRS §2.18 / §2.19):
    - Explanations can ONLY run against a `trained_models` row with a non-null
      `artifact_path` (the winning model of a completed experiment).
    - Requests for any non-winning model return a descriptive HTTP 422 error.
    - All background samples and development test fixtures come strictly from
      `DatasetSplitService.get_development_data()`. Locked Test partition rows
      must NEVER be accessed.
    - Artifact SHA-256 checksums are verified before every load to prevent
      explaining tampered or corrupted pipelines.
    - Global summaries are cached at the schema level (`explainability_summaries.model_id` UNIQUE).
    - Local explanation accepts an arbitrary input row and does not care whether it
      came from Development data or a live prediction request (Day 10's responsibility).
    """

    def __init__(self, db: Session):
        self.db = db
        self.exp_repo = ExperimentRepository(db)
        self.dataset_repo = DatasetRepository(db)
        self.split_service = DatasetSplitService(db)

    def _load_artifact(self, model_id: UUID | str) -> tuple[dict[str, Any], TrainedModel]:
        """
        Loads the fitted pipeline artifact for a given model ID with strict integrity verification.
        
        Raises HTTP 422 if:
        1. Model has no persisted artifact (non-winning candidate).
        2. Artifact file is missing from disk.
        3. Artifact SHA-256 checksum does not match the database record.
        """
        model = self.db.query(TrainedModel).filter(TrainedModel.id == model_id).first()
        if not model:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Trained model not found",
            )

        if not model.artifact_path:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="This model has no persisted artifact — explainability is only available for the winning model of a completed experiment",
            )

        artifact_file = Path(model.artifact_path)
        if not artifact_file.exists():
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Model artifact file not found at '{model.artifact_path}'",
            )

        # Recompute SHA-256 Checksum on disk to verify integrity against database record
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
                detail=f"Failed to deserialize model artifact: {str(e)}",
            )

        return artifact, model

    def _select_explainer(
        self,
        algorithm_name: str,
        fitted_pipeline: dict[str, Any],
        background_data: np.ndarray | None = None,
    ) -> tuple[Any, str]:
        """
        Factory to select the exact SHAP explainer architecture for the fixed algorithm set.
        
        Supported Mappings:
        - RandomForestRegressor, RandomForestClassifier, GradientBoostingRegressor, GradientBoostingClassifier -> shap.TreeExplainer
        - LinearRegression, Ridge, LogisticRegression -> shap.LinearExplainer
        """
        estimator = fitted_pipeline.get("estimator")
        if estimator is None:
            raise ValueError("Fitted pipeline artifact does not contain an estimator object.")

        tree_algorithms = {
            "RandomForestRegressor",
            "RandomForestClassifier",
            "GradientBoostingRegressor",
            "GradientBoostingClassifier",
        }
        linear_algorithms = {
            "LinearRegression",
            "Ridge",
            "LogisticRegression",
        }

        if algorithm_name in tree_algorithms:
            explainer = shap.TreeExplainer(estimator)
            return explainer, "TREE"

        elif algorithm_name in linear_algorithms:
            if background_data is None:
                raise ValueError(f"LinearExplainer for '{algorithm_name}' requires background reference data.")
            masker = shap.maskers.Independent(background_data)
            explainer = shap.LinearExplainer(estimator, masker=masker)
            return explainer, "LINEAR"

        else:
            raise ValueError(
                f"Unsupported algorithm '{algorithm_name}' for explainability. Only fixed 3+3 studio algorithms are supported."
            )

    def _get_background_sample_selected(
        self,
        model: TrainedModel,
        artifact: dict[str, Any],
        background_sample_size: int = 200,
        seed: int = 42,
    ) -> tuple[np.ndarray, list[str], int]:
        """
        Extracts background reference sample from the Development partition only,
        and applies the fitted pipeline's transformer and feature selection.
        """
        experiment = self.db.query(Experiment).filter(Experiment.id == model.experiment_id).first()
        if not experiment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Parent experiment for trained model not found",
            )

        dataset = (
            self.db.query(Dataset)
            .filter(Dataset.project_id == experiment.project_id)
            .order_by(Dataset.version_number.desc())
            .first()
        )
        if not dataset:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Dataset for experiment project not found",
            )

        # STRICT LEAKAGE RULE: Always retrieve Development partition data ONLY
        df_dev = self.split_service.get_development_data(dataset.id)

        feature_names_in = artifact.get("feature_names_in", [])
        transformer = artifact.get("transformer")
        selected_indices = artifact.get("selected_indices", [])
        selected_feature_names = artifact.get("selected_feature_names", [])

        # Filter candidate columns (strictly exclude system row_uid)
        valid_cols = [col for col in feature_names_in if col in df_dev.columns and col != "row_uid"]
        df_dev_features = df_dev[valid_cols]

        # Draw deterministic seeded sample
        n_available = len(df_dev_features)
        sample_n = min(n_available, background_sample_size)
        rng = np.random.RandomState(seed)
        sample_indices = rng.choice(n_available, size=sample_n, replace=False)
        df_sample = df_dev_features.iloc[sample_indices]

        # Apply transformation steps
        X_trans = transformer.transform(df_sample)
        if hasattr(X_trans, "toarray"):
            X_trans = X_trans.toarray()

        # Apply feature selection indices
        if selected_indices:
            X_selected = X_trans[:, selected_indices]
        else:
            X_selected = X_trans

        return X_selected, selected_feature_names, sample_n

    def global_shap_summary(
        self,
        model_id: UUID | str,
        background_sample_size: int = 200,
    ) -> GlobalExplainabilityResponse:
        """
        Computes or retrieves cached global SHAP summary (mean absolute SHAP per feature).
        
        Enforces schema-level caching: if a record exists in `explainability_summaries`,
        returns it immediately without loading artifact or recomputing SHAP.
        """
        # 1. Schema-level Cache Lookup
        cached_summary = (
            self.db.query(ExplainabilitySummary)
            .filter(ExplainabilitySummary.model_id == model_id)
            .first()
        )
        if cached_summary:
            return GlobalExplainabilityResponse(
                id=cached_summary.id,
                model_id=cached_summary.model_id,
                shap_values=cached_summary.shap_values,
                background_sample_size=cached_summary.background_sample_size,
                explainer_type=cached_summary.explainer_type,
                generated_at=cached_summary.generated_at,
                is_cached=True,
            )

        # 2. Load Artifact (with SHA-256 verification)
        artifact, model = self._load_artifact(model_id)

        # 3. Draw seeded Development background sample and transform into estimator feature space
        X_background, selected_feature_names, effective_sample_size = self._get_background_sample_selected(
            model=model,
            artifact=artifact,
            background_sample_size=background_sample_size,
            seed=42,
        )

        # 3b. Size Guardrail Check (Day 5 Policy Cap: 250 features)
        if X_background.shape[1] > 250:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"SHAP Explainability blocked: feature dimension ({X_background.shape[1]} features) exceeds the maximum policy cap of 250 features (risk of memory budget breach)."
            )

        # 4. Instantiate explainer
        explainer, explainer_type = self._select_explainer(
            algorithm_name=model.algorithm_name,
            fitted_pipeline=artifact,
            background_data=X_background,
        )

        # 5. Compute SHAP values
        exp_obj = explainer(X_background)
        raw_values = exp_obj.values if hasattr(exp_obj, "values") else exp_obj

        # Handle binary classification 3D shape (n_samples, n_features, 2) -> positive class
        if isinstance(raw_values, np.ndarray) and raw_values.ndim == 3 and raw_values.shape[2] == 2:
            shap_matrix = raw_values[:, :, 1]
        elif isinstance(raw_values, list) and len(raw_values) == 2:
            shap_matrix = raw_values[1]
        else:
            shap_matrix = np.asarray(raw_values)

        # Compute Mean Absolute SHAP per feature
        mean_abs_shap = np.mean(np.abs(shap_matrix), axis=0)

        shap_dict = {}
        for idx, feat in enumerate(selected_feature_names):
            val = float(mean_abs_shap[idx]) if idx < len(mean_abs_shap) else 0.0
            shap_dict[feat] = round(val, 6)

        # Sort features descending by mean absolute SHAP
        shap_dict = dict(sorted(shap_dict.items(), key=lambda item: item[1], reverse=True))

        # 6. Persist to explainability_summaries table
        summary_record = ExplainabilitySummary(
            id=uuid.uuid4(),
            model_id=model.id,
            shap_values=shap_dict,
            background_sample_size=effective_sample_size,
            explainer_type=explainer_type,
            generated_at=datetime.now(timezone.utc),
        )
        self.db.add(summary_record)
        self.db.commit()
        self.db.refresh(summary_record)

        return GlobalExplainabilityResponse(
            id=summary_record.id,
            model_id=summary_record.model_id,
            shap_values=summary_record.shap_values,
            background_sample_size=summary_record.background_sample_size,
            explainer_type=summary_record.explainer_type,
            generated_at=summary_record.generated_at,
            is_cached=False,
        )

    def local_shap_explanation(
        self,
        model_id: UUID | str,
        input_row: dict[str, Any],
    ) -> LocalExplainabilityResponse:
        """
        Computes instance-level local SHAP contribution values and base/expected value.
        
        NOTE: This method accepts an arbitrary input row and does not care whether it
        came from Development data or a live external prediction request — that data-source
        policy is Day 10's responsibility to enforce at the API boundary, not this method's.
        """
        # 1. Load Artifact with Checksum Verification
        artifact, model = self._load_artifact(model_id)

        feature_names_in = artifact.get("feature_names_in", [])
        transformer = artifact.get("transformer")
        selected_indices = artifact.get("selected_indices", [])
        selected_feature_names = artifact.get("selected_feature_names", [])
        estimator = artifact.get("estimator")
        task_type = artifact.get("task_type", "REGRESSION")

        # 2. Transform Single Input Row
        df_single = pd.DataFrame([input_row])
        # Ensure all expected feature columns are present
        for col in feature_names_in:
            if col not in df_single.columns:
                df_single[col] = np.nan
        df_single = df_single[feature_names_in]

        X_trans = transformer.transform(df_single)
        if hasattr(X_trans, "toarray"):
            X_trans = X_trans.toarray()

        if selected_indices:
            X_instance = X_trans[:, selected_indices]
        else:
            X_instance = X_trans

        # 3. Retrieve background sample if linear explainer needs it
        background_data = None
        if model.algorithm_name in {"LinearRegression", "Ridge", "LogisticRegression"}:
            background_data, _, _ = self._get_background_sample_selected(
                model=model,
                artifact=artifact,
                background_sample_size=100,
                seed=42,
            )

        # 4. Instantiate explainer
        explainer, explainer_type = self._select_explainer(
            algorithm_name=model.algorithm_name,
            fitted_pipeline=artifact,
            background_data=background_data,
        )

        # 5. Compute instance SHAP explanation
        exp_obj = explainer(X_instance)
        raw_values = exp_obj.values if hasattr(exp_obj, "values") else exp_obj
        raw_base = exp_obj.base_values if hasattr(exp_obj, "base_values") else getattr(explainer, "expected_value", 0.0)

        # Extract scalar base value and contribution vector
        if isinstance(raw_values, np.ndarray) and raw_values.ndim == 3 and raw_values.shape[2] == 2:
            # Binary classification TreeExplainer (n_instances, n_features, 2)
            contrib_vector = raw_values[0, :, 1]
            base_value = float(raw_base[0, 1] if hasattr(raw_base, "__getitem__") and getattr(raw_base, "ndim", 1) > 1 else raw_base[1])
            if hasattr(estimator, "predict_proba"):
                prediction = float(estimator.predict_proba(X_instance)[0, 1])
            else:
                prediction = None
        elif isinstance(raw_values, list) and len(raw_values) == 2:
            contrib_vector = raw_values[1][0]
            base_value = float(raw_base[1] if hasattr(raw_base, "__getitem__") else raw_base)
            if hasattr(estimator, "predict_proba"):
                prediction = float(estimator.predict_proba(X_instance)[0, 1])
            else:
                prediction = None
        else:
            # Regression or Linear Binary Classification (log-odds space)
            contrib_vector = raw_values[0]
            if isinstance(raw_base, (np.ndarray, list)):
                base_value = float(raw_base[0]) if len(raw_base) > 0 else 0.0
            else:
                base_value = float(raw_base)

            if task_type == "REGRESSION" and hasattr(estimator, "predict"):
                prediction = float(estimator.predict(X_instance)[0])
            elif task_type == "CLASSIFICATION" and hasattr(estimator, "decision_function"):
                prediction = float(estimator.decision_function(X_instance)[0])
            elif hasattr(estimator, "predict"):
                prediction = float(estimator.predict(X_instance)[0])
            else:
                prediction = None

        contributions = {}
        for idx, feat in enumerate(selected_feature_names):
            val = float(contrib_vector[idx]) if idx < len(contrib_vector) else 0.0
            contributions[feat] = round(val, 6)

        sum_contributions_plus_base = round(sum(contributions.values()) + base_value, 6)

        return LocalExplainabilityResponse(
            model_id=model.id,
            base_value=round(base_value, 6),
            contributions=contributions,
            prediction=round(prediction, 6) if prediction is not None else None,
            sum_contributions_plus_base=sum_contributions_plus_base,
            explainer_type=explainer_type,
        )
