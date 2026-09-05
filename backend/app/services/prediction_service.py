import json
import time
import uuid
import hashlib
from uuid import UUID
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.deployment import Deployment
from app.models.trained_model import TrainedModel
from app.models.prediction_log import PredictionLog
from app.schemas.deployment import PredictResponse, PredictExplainResponse
from app.services.model_registry_service import ModelRegistryService
from app.services.explainability_service import ExplainabilityService


class PredictionService:
    """
    Decoupled Fast & Explainable Prediction Service (SRS §2.14 / §2.15 / Day 10).
    
    ARCHITECTURAL INVARIANTS:
    1. Decoupled Fast/Explain split: `predict()` runs lightweight inference without
       SHAP overhead. `predict_with_explanation()` layers on local SHAP explanation
       and logs distinct, separate latency metrics.
    2. In-memory Model Caching: First/cold load verifies SHA-256 artifact checksum.
       Warm-cache hits bypass disk I/O for ultra-fast serving.
    3. Audit Logging: Every inference attempt (including validation errors) is logged
       to `prediction_logs` respecting the configured `payload_mode` ('HASHED' by default).
    4. Strict Validation: Missing or wrong-typed payload features return HTTP 422.
    """

    # In-memory artifact cache: {deployment_id_str: (artifact_checksum, artifact_dict)}
    _model_cache: dict[str, tuple[str, dict[str, Any]]] = {}

    def __init__(self, db: Session):
        self.db = db
        self.registry_service = ModelRegistryService(db)
        self.explainability_service = ExplainabilityService(db)

    @classmethod
    def clear_cache(cls, deployment_id: UUID | str | None = None) -> None:
        """
        Clears the in-memory pipeline cache (either for a specific deployment or globally).
        Used during deployment invalidation or integrity tests.
        """
        if deployment_id is not None:
            cls._model_cache.pop(str(deployment_id), None)
        else:
            cls._model_cache.clear()

    def _load_pipeline(self, deployment: Deployment) -> dict[str, Any]:
        """
        Loads fitted pipeline artifact into memory.
        
        Tradeoff Note:
        Warm-cache hits skip disk I/O and SHA-256 recalculation for sub-millisecond latency.
        Cold loads enforce strict cryptographic SHA-256 integrity verification against
        the database record.
        """
        dep_id_str = str(deployment.id)
        if dep_id_str in self._model_cache:
            return self._model_cache[dep_id_str][1]

        model = self.db.query(TrainedModel).filter(TrainedModel.id == deployment.model_id).first()
        if not model or not model.artifact_path:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Model artifact path is missing or inaccessible.",
            )

        artifact_file = Path(model.artifact_path)
        if not artifact_file.exists():
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Model artifact file not found at '{model.artifact_path}'.",
            )

        # Cryptographic Checksum Verification on cold load
        hasher = hashlib.sha256()
        with open(artifact_file, "rb") as f:
            while chunk := f.read(65536):
                hasher.update(chunk)
        disk_checksum = hasher.hexdigest()

        if model.artifact_checksum and disk_checksum != model.artifact_checksum:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Artifact integrity check failed on cold load: SHA-256 mismatch ({disk_checksum[:12]}... != {model.artifact_checksum[:12]}...).",
            )

        try:
            artifact = joblib.load(artifact_file)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Failed to deserialize model artifact: {str(e)}",
            )

        self._model_cache[dep_id_str] = (model.artifact_checksum or disk_checksum, artifact)
        return artifact

    def validate_schema(self, deployment: Deployment, payload: dict[str, Any]) -> dict[str, str]:
        """
        Validates payload keys and types against the model's locked schema.
        Raises HTTP 422 listing all missing and wrong-typed fields.
        """
        schema = self.registry_service.get_input_schema(deployment.model_id)
        if not schema:
            # If schema is empty, no features were registered
            return {}

        missing_fields = []
        wrong_typed_fields = []

        for field_name, expected_dtype in schema.items():
            if field_name not in payload:
                missing_fields.append(field_name)
                continue

            val = payload[field_name]
            if val is None:
                continue

            # Type checking rules
            if expected_dtype == "NUMERIC":
                # Booleans are subclasses of int in Python, so explicitly disallow bool for NUMERIC
                if isinstance(val, bool) or not isinstance(val, (int, float)):
                    wrong_typed_fields.append(f"'{field_name}' (expected NUMERIC, got {type(val).__name__})")
            elif expected_dtype == "CATEGORICAL":
                if not isinstance(val, (str, int, float, bool)):
                    wrong_typed_fields.append(f"'{field_name}' (expected CATEGORICAL, got {type(val).__name__})")

        if missing_fields or wrong_typed_fields:
            errors = []
            if missing_fields:
                errors.append(f"Missing required fields: {', '.join(missing_fields)}")
            if wrong_typed_fields:
                errors.append(f"Invalid field types: {', '.join(wrong_typed_fields)}")
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="; ".join(errors),
            )

        return schema

    def predict(
        self,
        deployment_id: UUID | str,
        payload: dict[str, Any],
        payload_mode: str = "HASHED",
    ) -> tuple[PredictResponse, Deployment]:
        """
        High-speed decoupled prediction endpoint without SHAP calculation.
        """
        deployment = self.db.query(Deployment).filter(Deployment.id == deployment_id).first()
        if not deployment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Deployment not found",
            )

        if deployment.status != "LIVE":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Deployment is not LIVE (current status: {deployment.status}). Cannot serve predictions.",
            )

        request_id = uuid.uuid4()
        schema_hash = hashlib.sha256(json.dumps(sorted(list(payload.keys()))).encode()).hexdigest()
        start_time = time.perf_counter()

        # Schema Validation with Audit Logging on Error
        try:
            schema = self.validate_schema(deployment, payload)
        except HTTPException as e:
            elapsed_ms = max(1, int((time.perf_counter() - start_time) * 1000))
            self._log_prediction(
                deployment_id=deployment.id,
                request_id=request_id,
                schema_hash=schema_hash,
                payload_mode=payload_mode,
                input_payload=payload if payload_mode in {"FULL", "REDACTED"} else None,
                prediction_output=None,
                latency_ms=elapsed_ms,
                explanation_requested=False,
                explanation_latency_ms=None,
                status="VALIDATION_ERROR",
            )
            raise e

        # Load Pipeline and Execute Inference
        artifact = self._load_pipeline(deployment)
        transformer = artifact.get("transformer")
        selected_indices = artifact.get("selected_indices", [])
        selected_feature_names = artifact.get("selected_feature_names", [])
        feature_names_in = artifact.get("feature_names_in", [])
        estimator = artifact.get("estimator")
        task_type = artifact.get("task_type", "REGRESSION")

        df_single = pd.DataFrame([payload])
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

        # Inference
        pred_raw = estimator.predict(X_instance)[0]
        if isinstance(pred_raw, (np.floating, float)):
            prediction = round(float(pred_raw), 6)
        elif isinstance(pred_raw, (np.integer, int)):
            prediction = int(pred_raw)
        else:
            prediction = str(pred_raw)

        probabilities = None
        if task_type == "CLASSIFICATION" and hasattr(estimator, "predict_proba"):
            proba_raw = estimator.predict_proba(X_instance)[0]
            if hasattr(estimator, "classes_"):
                classes = [str(c) for c in estimator.classes_]
                probabilities = {cls: round(float(p), 6) for cls, p in zip(classes, proba_raw)}
            else:
                probabilities = [round(float(p), 6) for p in proba_raw]

        end_time = time.perf_counter()
        latency_ms = max(1, int((end_time - start_time) * 1000))
        prediction_output = {"prediction": prediction, "probabilities": probabilities}

        # Log Success
        self._log_prediction(
            deployment_id=deployment.id,
            request_id=request_id,
            schema_hash=schema_hash,
            payload_mode=payload_mode,
            input_payload=payload if payload_mode in {"FULL", "REDACTED"} else None,
            prediction_output=prediction_output,
            latency_ms=latency_ms,
            explanation_requested=False,
            explanation_latency_ms=None,
            status="SUCCESS",
        )

        response = PredictResponse(
            prediction=prediction,
            probabilities=probabilities,
            latency_ms=latency_ms,
            request_id=request_id,
        )
        return response, deployment

    def predict_with_explanation(
        self,
        deployment_id: UUID | str,
        payload: dict[str, Any],
        payload_mode: str = "HASHED",
    ) -> PredictExplainResponse:
        """
        Full inference request with separate local SHAP explanation calculation.
        Latency for base prediction and explanation calculation are tracked distinctly.
        """
        # 1. Execute base prediction
        base_response, deployment = self.predict(
            deployment_id=deployment_id,
            payload=payload,
            payload_mode=payload_mode,
        )

        # 2. Execute local SHAP explanation with isolated timer
        exp_start = time.perf_counter()
        shap_res = self.explainability_service.local_shap_explanation(
            model_id=deployment.model_id,
            input_row=payload,
        )
        exp_end = time.perf_counter()
        explanation_latency_ms = max(1, int((exp_end - exp_start) * 1000))

        # 3. Update logged row with explanation details
        log_entry = (
            self.db.query(PredictionLog)
            .filter(PredictionLog.request_id == base_response.request_id)
            .first()
        )
        if log_entry:
            log_entry.explanation_requested = True
            log_entry.explanation_latency_ms = explanation_latency_ms
            self.db.add(log_entry)
            self.db.commit()

        total_latency = base_response.latency_ms + explanation_latency_ms

        return PredictExplainResponse(
            prediction=base_response.prediction,
            probabilities=base_response.probabilities,
            latency_ms=base_response.latency_ms,
            explanation_latency_ms=explanation_latency_ms,
            total_latency_ms=total_latency,
            request_id=base_response.request_id,
            explanation={
                "base_value": shap_res.base_value,
                "contributions": shap_res.contributions,
                "explainer_type": shap_res.explainer_type,
                "sum_contributions_plus_base": shap_res.sum_contributions_plus_base,
            },
        )

    def _log_prediction(
        self,
        deployment_id: UUID,
        request_id: UUID,
        schema_hash: str,
        payload_mode: str,
        input_payload: dict[str, Any] | None,
        prediction_output: dict[str, Any] | None,
        latency_ms: int,
        explanation_requested: bool,
        explanation_latency_ms: int | None,
        status: str,
    ) -> PredictionLog:
        log_row = PredictionLog(
            deployment_id=deployment_id,
            request_id=request_id,
            schema_hash=schema_hash,
            payload_mode=payload_mode,
            input_payload=input_payload,
            prediction_output=prediction_output,
            latency_ms=latency_ms,
            explanation_requested=explanation_requested,
            explanation_latency_ms=explanation_latency_ms,
            status=status,
            requested_at=datetime.now(timezone.utc),
        )
        self.db.add(log_row)
        self.db.commit()
        self.db.refresh(log_row)
        return log_row
