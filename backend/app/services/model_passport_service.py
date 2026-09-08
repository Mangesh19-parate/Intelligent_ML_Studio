from uuid import UUID
from datetime import datetime
from typing import Any
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.trained_model import TrainedModel
from app.models.experiment import Experiment
from app.models.project import Project
from app.models.dataset import Dataset
from app.models.transformation_snapshot import TransformationSnapshot
from app.models.feature_selection_snapshot import FeatureSelectionSnapshot
from app.models.model_metric import ModelMetric
from app.models.explainability_summary import ExplainabilitySummary
from app.models.deployment_gate import DeploymentGate
from app.models.deployment import Deployment
from app.schemas.model_passport import (
    ModelPassportResponse,
    PassportProjectInfo,
    PassportDatasetInfo,
    PassportExperimentInfo,
    PassportPreprocessingInfo,
    PassportFeatureSelectionInfo,
    PassportMetricItem,
    PassportExplainabilityInfo,
    PassportGovernanceInfo,
)


class ModelPassportService:
    """
    Model Technical Passport Service (SRS v9 §13).
    
    ARCHITECTURAL MANDATE:
    - Strict SELECT + render only: Direct read from already-persisted database rows.
    - Zero recomputations: Never recomputes metrics, never fits models, never loads
      disk artifacts (zero joblib/pickle IO during passport generation).
    - Immutable technical governance audit certificate.
    """

    def __init__(self, db: Session):
        self.db = db

    def get_passport(self, model_id: UUID | str) -> ModelPassportResponse:
        """
        Assembles and returns the immutable Model Passport by querying stored records.
        """
        # 1. Query TrainedModel (Direct SELECT)
        model = self.db.query(TrainedModel).filter(TrainedModel.id == model_id).first()
        if not model:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Trained model with id '{model_id}' not found",
            )

        # 2. Query Experiment & Project (Direct SELECT)
        experiment = self.db.query(Experiment).filter(Experiment.id == model.experiment_id).first()
        if not experiment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Parent experiment '{model.experiment_id}' not found",
            )

        project = self.db.query(Project).filter(Project.id == experiment.project_id).first()
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Parent project '{experiment.project_id}' not found",
            )

        # 3. Query Latest Dataset (Direct SELECT)
        dataset = (
            self.db.query(Dataset)
            .filter(Dataset.project_id == project.id)
            .order_by(Dataset.version_number.desc())
            .first()
        )

        dataset_info = None
        if dataset:
            dataset_info = PassportDatasetInfo(
                id=dataset.id,
                version_number=dataset.version_number,
                row_count=dataset.row_count,
                column_count=dataset.column_count,
                stage=dataset.stage,
                content_hash=dataset.content_hash,
            )

        # 4. Preprocessing Snapshot (Direct SELECT)
        preprocessing_info = None
        tf_snapshot = None
        if model.preprocessing_snapshot_id:
            tf_snapshot = self.db.query(TransformationSnapshot).filter(
                TransformationSnapshot.id == model.preprocessing_snapshot_id
            ).first()

        if not tf_snapshot:
            tf_snapshot = (
                self.db.query(TransformationSnapshot)
                .filter(TransformationSnapshot.experiment_id == experiment.id)
                .order_by(TransformationSnapshot.created_at.desc())
                .first()
            )

        if tf_snapshot:
            preprocessing_info = PassportPreprocessingInfo(
                snapshot_id=tf_snapshot.id,
                config_json=tf_snapshot.config_json,
                created_at=tf_snapshot.created_at,
            )

        # 5. Feature Selection Snapshot (Direct SELECT)
        feature_selection_info = None
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

        if fs_snapshot:
            features = fs_snapshot.final_selected_features or []
            feature_selection_info = PassportFeatureSelectionInfo(
                snapshot_id=fs_snapshot.id,
                final_selection_method=fs_snapshot.final_selection_method,
                final_selected_features=features if isinstance(features, list) else [],
                feature_count=len(features) if isinstance(features, list) else 0,
                created_at=fs_snapshot.created_at,
            )

        # 6. Query Stored Model Metrics (Direct SELECT)
        metrics_rows = (
            self.db.query(ModelMetric)
            .filter(ModelMetric.model_id == model.id)
            .order_by(ModelMetric.split, ModelMetric.metric_name, ModelMetric.fold_index)
            .all()
        )

        metric_items: list[PassportMetricItem] = []
        metrics_by_split: dict[str, dict[str, float]] = {}

        for m in metrics_rows:
            val = float(m.metric_value) if m.metric_value is not None else None
            metric_items.append(
                PassportMetricItem(
                    split=m.split,
                    metric_name=m.metric_name,
                    metric_value=val,
                    metric_json=m.metric_json,
                    fold_index=m.fold_index,
                    created_at=m.created_at,
                )
            )
            if val is not None:
                if m.split not in metrics_by_split:
                    metrics_by_split[m.split] = {}
                metrics_by_split[m.split][m.metric_name] = val

        # Calculate Generalization Gap from already-stored metrics
        generalization_gap = None
        train_metrics = metrics_by_split.get("TRAIN", {})
        val_metrics = metrics_by_split.get("CV_MEAN") or metrics_by_split.get("VALIDATION", {})
        prim_metric = experiment.selection_metric

        if prim_metric and prim_metric in train_metrics and prim_metric in val_metrics:
            train_val = train_metrics[prim_metric]
            val_val = val_metrics[prim_metric]
            if experiment.selection_direction == "MINIMIZE":
                generalization_gap = round(val_val - train_val, 5)
            else:
                generalization_gap = round(train_val - val_val, 5)

        # 7. Query Stored Explainability Summary (Direct SELECT)
        explainability_info = None
        exp_summary = (
            self.db.query(ExplainabilitySummary)
            .filter(ExplainabilitySummary.model_id == model.id)
            .first()
        )
        if exp_summary:
            top_feats = []
            vals = exp_summary.shap_values
            if isinstance(vals, dict):
                if "feature_importances" in vals and isinstance(vals["feature_importances"], list):
                    top_feats = vals["feature_importances"][:10]
                elif "mean_abs_shap" in vals and isinstance(vals["mean_abs_shap"], dict):
                    sorted_feats = sorted(
                        vals["mean_abs_shap"].items(),
                        key=lambda x: x[1] if isinstance(x[1], (int, float)) else 0,
                        reverse=True
                    )
                    top_feats = [{"feature": f, "mean_abs_shap": round(float(s), 5)} for f, s in sorted_feats[:10]]
                else:
                    sorted_feats = sorted(
                        vals.items(),
                        key=lambda x: x[1] if isinstance(x[1], (int, float)) else 0,
                        reverse=True
                    )
                    top_feats = [{"feature": f, "mean_abs_shap": round(float(s), 5)} for f, s in sorted_feats[:10]]
            elif isinstance(vals, list):
                top_feats = vals[:10]

            explainability_info = PassportExplainabilityInfo(
                has_summary=True,
                summary_id=exp_summary.id,
                top_features=top_feats,
                background_sample_size=exp_summary.background_sample_size,
                computed_at=exp_summary.generated_at,
            )

        # 8. Query Stored Deployment Gate & Deployment (Direct SELECT)
        latest_gate = (
            self.db.query(DeploymentGate)
            .filter(DeploymentGate.model_id == model.id)
            .order_by(DeploymentGate.evaluated_at.desc())
            .first()
        )

        active_deployment = (
            self.db.query(Deployment)
            .filter(Deployment.model_id == model.id)
            .order_by(Deployment.deployed_at.desc())
            .first()
        )

        gate_checks_list: list[dict[str, Any]] = []
        if latest_gate:
            gate_checks_list = [
                {"check": "locked_test_evaluated", "passed": bool(latest_gate.locked_test_evaluated)},
                {"check": "schema_locked", "passed": bool(latest_gate.schema_locked)},
                {"check": "artifact_verified", "passed": bool(latest_gate.artifact_verified)},
                {"check": "lineage_complete", "passed": bool(latest_gate.lineage_complete)},
                {"check": "performance_threshold_passed", "passed": latest_gate.performance_threshold_passed == "PASS"},
                {"check": "user_approved", "passed": bool(latest_gate.user_approved)},
            ]

        is_deployed = active_deployment is not None and active_deployment.status in ["DEPLOYED", "LIVE"]
        governance_info = PassportGovernanceInfo(
            gate_evaluated=latest_gate is not None,
            gate_is_passing=bool(latest_gate.gate_passed) if latest_gate else False,
            gate_user_approved=bool(latest_gate.user_approved) if latest_gate else False,
            gate_approved_by_user_id=None,
            gate_approved_at=latest_gate.evaluated_at if latest_gate else None,
            gate_checks=gate_checks_list,
            is_deployed=is_deployed,
            deployment_id=active_deployment.id if active_deployment else None,
            deployment_status=active_deployment.status if active_deployment else None,
            endpoint_url=active_deployment.endpoint_path if active_deployment else None,
            deployed_at=active_deployment.deployed_at if active_deployment else None,
        )

        # 9. Assemble and return ModelPassportResponse
        is_champion = (
            experiment.selected_model_id == model.id
            or (model.model_selection_score is not None and float(model.model_selection_score) >= 99.0)
        )

        return ModelPassportResponse(
            model_id=model.id,
            algorithm_name=model.algorithm_name,
            hyperparameters=model.hyperparameters or {},
            status=model.status,
            is_selected_champion=is_champion,
            model_selection_score=float(model.model_selection_score) if model.model_selection_score is not None else None,
            fit_diagnosis=model.fit_diagnosis,
            decision_threshold=float(model.decision_threshold) if model.decision_threshold is not None else 0.5,
            artifact_path=model.artifact_path,
            artifact_checksum=model.artifact_checksum,
            created_at=model.created_at,
            project=PassportProjectInfo(
                id=project.id,
                project_name=project.project_name,
                task_type=project.task_type,
                target_column=project.target_column,
                created_at=project.created_at,
            ),
            experiment=PassportExperimentInfo(
                id=experiment.id,
                task_type=experiment.task_type,
                fold_count=experiment.fold_count,
                cv_seed=experiment.cv_seed,
                selection_metric=experiment.selection_metric,
                selection_direction=experiment.selection_direction,
                locked_test_consumed=experiment.locked_test_consumed,
                locked_test_consumed_at=experiment.locked_test_consumed_at,
                code_version=experiment.code_version,
                dataset_content_hash=experiment.dataset_content_hash,
                python_version=experiment.python_version,
                sklearn_version=experiment.sklearn_version,
                numpy_version=experiment.numpy_version,
                pandas_version=experiment.pandas_version,
                model_library_versions=experiment.model_library_versions,
                environment_capture_method=experiment.environment_capture_method,
                created_at=experiment.created_at,
                completed_at=experiment.completed_at,
            ),
            dataset=dataset_info,
            preprocessing=preprocessing_info,
            feature_selection=feature_selection_info,
            metrics=metric_items,
            metrics_summary_by_split=metrics_by_split,
            generalization_gap=generalization_gap,
            explainability=explainability_info,
            governance=governance_info,
        )
