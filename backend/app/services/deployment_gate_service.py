import hashlib
from uuid import UUID
from pathlib import Path
from datetime import datetime, timezone
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.trained_model import TrainedModel
from app.models.experiment import Experiment
from app.models.model_metric import ModelMetric
from app.models.deployment_gate import DeploymentGate
from app.services.model_registry_service import ModelRegistryService


class DeploymentGateService:
    """
    Model Deployment Gate Service (Day 10).
    
    ARCHITECTURAL NOTE (SRS §2.14 / §2.16):
    Strict pre-deployment gatekeeper verifying 6 conditions:
    1. locked_test_evaluated: Model has evaluated LOCKED_TEST metrics (never diagnostic)
    2. schema_locked: Expected input feature schema resolved and non-empty
    3. artifact_verified: SHA-256 disk checksum matches current artifact
    4. lineage_complete: Config, snapshots, and environment metadata non-null
    5. performance_threshold_passed: Tri-state ('PASS', 'FAIL', 'UNVERIFIABLE')
    6. user_approved: Explicit sign-off by privileged user (DEPLOY permission)
    
    Every check creates a persistent audit row in `deployment_gates`.
    """

    def __init__(self, db: Session):
        self.db = db
        self.registry_service = ModelRegistryService(db)

    def check_gate(self, model_id: UUID | str, user_approved: bool = False) -> DeploymentGate:
        """
        Computes all six gate conditions explicitly, persists an immutable DeploymentGate
        record to the database, and returns it.
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

        # 1. Condition: locked_test_evaluated
        # Must have a ModelMetric row with split == 'LOCKED_TEST' (never 'TEST_REUSED_DIAGNOSTIC')
        locked_metric_rows = self.db.query(ModelMetric).filter(
            ModelMetric.model_id == model.id,
            ModelMetric.split == "LOCKED_TEST",
        ).all()
        locked_test_evaluated = len(locked_metric_rows) > 0

        # 2. Condition: schema_locked
        # get_input_schema returns a non-empty mapping
        schema = self.registry_service.get_input_schema(model.id)
        schema_locked = bool(schema and len(schema) > 0)

        # 3. Condition: artifact_verified
        # Live disk check: artifact exists and SHA-256 checksum matches right now
        artifact_verified = False
        if model.artifact_path and model.artifact_checksum:
            artifact_file = Path(model.artifact_path)
            if artifact_file.exists():
                hasher = hashlib.sha256()
                with open(artifact_file, "rb") as f:
                    while chunk := f.read(65536):
                        hasher.update(chunk)
                disk_checksum = hasher.hexdigest()
                artifact_verified = (disk_checksum == model.artifact_checksum)

        # 4. Condition: lineage_complete
        # Experiment config, snapshots, and environment metadata non-null
        has_config = experiment.experiment_config is not None
        has_trans_snapshot = bool(
            model.preprocessing_snapshot_id
            or (experiment.transformation_snapshots and len(experiment.transformation_snapshots) > 0)
            or (isinstance(experiment.experiment_config, dict) and experiment.experiment_config.get("preprocessing", {}).get("snapshot_id"))
        )
        has_fs_snapshot = bool(
            model.feature_selection_snapshot_id
            or experiment.feature_selection_snapshot_id
            or (experiment.feature_selection_snapshots and len(experiment.feature_selection_snapshots) > 0)
        )
        has_env_fields = bool(
            experiment.code_version
            and experiment.python_version
            and experiment.sklearn_version
            and experiment.numpy_version
            and experiment.pandas_version
            and experiment.environment_capture_method
        )
        lineage_complete = bool(has_config and has_trans_snapshot and has_fs_snapshot and has_env_fields)

        # 5. Condition: performance_threshold_passed (Tri-state: 'PASS', 'FAIL', 'UNVERIFIABLE')
        if not getattr(experiment, "deployment_threshold_frozen_at_creation", False):
            performance_threshold_passed = "UNVERIFIABLE"
        elif not experiment.experiment_config or not isinstance(experiment.experiment_config, dict):
            performance_threshold_passed = "UNVERIFIABLE"
        else:
            thresh_config = experiment.experiment_config.get("deployment_threshold", {})
            min_val = thresh_config.get("min_value") if isinstance(thresh_config, dict) else None
            
            if min_val is None:
                performance_threshold_passed = "UNVERIFIABLE"
            else:
                target_metric = (thresh_config.get("metric") or experiment.selection_metric or "").strip().lower()
                matched_metric = next(
                    (m for m in locked_metric_rows if m.metric_name.strip().lower() == target_metric),
                    None
                )
                if not matched_metric:
                    sel_metric = (experiment.selection_metric or "").strip().lower()
                    matched_metric = next(
                        (m for m in locked_metric_rows if m.metric_name.strip().lower() == sel_metric),
                        None
                    )

                if not matched_metric or matched_metric.metric_value is None:
                    performance_threshold_passed = "FAIL"
                else:
                    val = float(matched_metric.metric_value)
                    direction = (experiment.selection_direction or "MAXIMIZE").upper()
                    if direction == "MINIMIZE":
                        performance_threshold_passed = "PASS" if val <= float(min_val) else "FAIL"
                    else:
                        performance_threshold_passed = "PASS" if val >= float(min_val) else "FAIL"

        # 6. User Approval & Overall Gate status
        gate_passed = bool(
            locked_test_evaluated
            and schema_locked
            and artifact_verified
            and lineage_complete
            and (performance_threshold_passed == "PASS")
            and user_approved
        )

        gate_record = DeploymentGate(
            model_id=model.id,
            locked_test_evaluated=locked_test_evaluated,
            schema_locked=schema_locked,
            artifact_verified=artifact_verified,
            lineage_complete=lineage_complete,
            performance_threshold_passed=performance_threshold_passed,
            user_approved=user_approved,
            gate_passed=gate_passed,
            evaluated_at=datetime.now(timezone.utc),
        )
        self.db.add(gate_record)
        self.db.commit()
        self.db.refresh(gate_record)
        return gate_record

    def get_latest_gate(self, model_id: UUID | str) -> DeploymentGate | None:
        """
        Retrieves the latest persisted deployment gate check for a model,
        or performs a new check if none exists.
        """
        latest = (
            self.db.query(DeploymentGate)
            .filter(DeploymentGate.model_id == model_id)
            .order_by(DeploymentGate.evaluated_at.desc())
            .first()
        )
        if not latest:
            latest = self.check_gate(model_id, user_approved=False)
        return latest

    def approve(self, model_id: UUID | str, approved_by_user_id: UUID | str) -> DeploymentGate:
        """
        Re-computes gate checks fresh against the current system state,
        sets user_approved = true, persists a new DeploymentGate audit row,
        and returns the record.
        """
        return self.check_gate(model_id=model_id, user_approved=True)
