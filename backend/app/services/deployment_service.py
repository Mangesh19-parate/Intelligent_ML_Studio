import uuid
import hashlib
from pathlib import Path
from datetime import datetime, timezone
from uuid import UUID
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.deployment import Deployment
from app.models.trained_model import TrainedModel
from app.config.state_machines import (
    DeploymentState,
    validate_transition,
    InvalidStateTransitionError,
)
from app.services.deployment_gate_service import DeploymentGateService


class DeploymentService:
    """
    Model Deployment Lifecycle Service (Day 10 / SRS v9 §2).
    
    ARCHITECTURAL NOTE (SRS §2.14 / §2.16 / SRS v9 §2):
    - Enforces gate-controlled deployment.
    - Lifecycle state machine: CREATED -> GATE_PENDING -> GATE_PASSED -> APPROVED -> DEPLOYED <-> PAUSED -> RETIRED.
    - Invariant: A RETIRED deployment is immutable and cannot be transitioned back to DEPLOYED or PAUSED.
    """

    def __init__(self, db: Session):
        self.db = db
        self.gate_service = DeploymentGateService(db)

    def deploy(self, model_id: UUID | str, user_id: UUID | str | None = None) -> Deployment:
        """
        Validates deployment gate conditions. If all 6 pass, provisions a DEPLOYED
        endpoint at `/api/v1/predict/{deployment_id}`.
        
        Raises HTTP 422 if gate fails, listing all unmet conditions and distinguishing
        'UNVERIFIABLE' from 'FAIL'.
        """
        model = self.db.query(TrainedModel).filter(TrainedModel.id == model_id).first()
        if not model:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Trained model not found",
            )

        # Check latest gate record
        gate = self.gate_service.get_latest_gate(model.id)
        if not gate or not gate.gate_passed:
            gate_check = gate or self.gate_service.check_gate(model.id)
            failed_conditions = []
            if not gate_check.locked_test_evaluated:
                failed_conditions.append("locked_test_evaluated")
            if not gate_check.schema_locked:
                failed_conditions.append("schema_locked")
            if not gate_check.artifact_verified:
                failed_conditions.append("artifact_verified")
            if not gate_check.lineage_complete:
                failed_conditions.append("lineage_complete")
            if gate_check.performance_threshold_passed != "PASS":
                status_label = gate_check.performance_threshold_passed or "UNVERIFIABLE"
                failed_conditions.append(f"performance_threshold_passed: {status_label}")
            if not gate_check.user_approved:
                failed_conditions.append("user_approved")

            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Deployment gate check failed. Unmet conditions: {', '.join(failed_conditions)}",
            )

        # Confirm artifact exists and checksum is verified on disk
        if not model.artifact_path or not Path(model.artifact_path).exists():
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Model artifact file missing from disk. Deployment rejected.",
            )

        hasher = hashlib.sha256()
        with open(model.artifact_path, "rb") as f:
            while chunk := f.read(65536):
                hasher.update(chunk)
        if model.artifact_checksum and hasher.hexdigest() != model.artifact_checksum:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Model artifact checksum mismatch on disk. Deployment rejected due to failed artifact integrity.",
            )

        deployment_id = uuid.uuid4()
        endpoint_path = f"/api/v1/predict/{deployment_id}"

        deployed_by_uuid = None
        if user_id:
            try:
                deployed_by_uuid = UUID(str(user_id))
            except Exception:
                pass

        deployment = Deployment(
            id=deployment_id,
            model_id=model.id,
            endpoint_path=endpoint_path,
            status=DeploymentState.DEPLOYED.value,
            deployed_by=deployed_by_uuid,
            deployed_at=datetime.now(timezone.utc),
            log_retention_days=30,
        )
        self.db.add(deployment)
        self.db.commit()
        self.db.refresh(deployment)
        return deployment

    def pause(self, deployment_id: UUID | str) -> Deployment:
        """
        Pauses an active deployment.
        """
        return self.update_status(deployment_id, DeploymentState.PAUSED.value)

    def retire(self, deployment_id: UUID | str) -> Deployment:
        """
        Permanently retires a deployment. Cannot be un-retired.
        """
        return self.update_status(deployment_id, DeploymentState.RETIRED.value)

    def update_status(self, deployment_id: UUID | str, target_status: str) -> Deployment:
        """
        Transitions deployment status respecting the centralized state machine rules:
        - DEPLOYED -> PAUSED
        - PAUSED -> DEPLOYED
        - DEPLOYED -> RETIRED
        - PAUSED -> RETIRED
        - RETIRED -> (ANY) is strictly rejected
        """
        status_norm = target_status.upper().strip()
        if status_norm == "LIVE":
            status_norm = DeploymentState.DEPLOYED.value

        try:
            target_state = DeploymentState(status_norm)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid target status '{target_status}'. Allowed values: DEPLOYED, PAUSED, RETIRED.",
            )

        deployment = self.db.query(Deployment).filter(Deployment.id == deployment_id).first()
        if not deployment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Deployment not found",
            )

        current_state_str = deployment.status
        if current_state_str == "LIVE":
            current_state_str = DeploymentState.DEPLOYED.value
        current_state = DeploymentState(current_state_str)

        try:
            validate_transition(current_state, target_state)
        except InvalidStateTransitionError as e:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=str(e),
            )

        deployment.status = target_state.value
        self.db.add(deployment)
        self.db.commit()
        self.db.refresh(deployment)
        return deployment

    def get_by_id(self, deployment_id: UUID | str) -> Deployment | None:
        return self.db.query(Deployment).filter(Deployment.id == deployment_id).first()
