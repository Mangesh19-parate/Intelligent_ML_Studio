import uuid
from datetime import datetime, timezone
from uuid import UUID
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.deployment import Deployment
from app.models.trained_model import TrainedModel
from app.services.deployment_gate_service import DeploymentGateService


class DeploymentService:
    """
    Model Deployment Lifecycle Service (Day 10).
    
    ARCHITECTURAL NOTE (SRS §2.14 / §2.16):
    - Enforces gate-controlled deployment.
    - Lifecycle state machine: LIVE -> PAUSED -> RETIRED.
    - Invariant: A RETIRED deployment is immutable and cannot be transitioned back to LIVE or PAUSED.
    """

    def __init__(self, db: Session):
        self.db = db
        self.gate_service = DeploymentGateService(db)

    def deploy(self, model_id: UUID | str, user_id: UUID | str | None = None) -> Deployment:
        """
        Validates deployment gate conditions. If all 6 pass, provisions a LIVE deployment
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
        gate = (
            self.db.query(self.gate_service.gate_service_model if hasattr(self.gate_service, 'gate_service_model') else TrainedModel)
            and self.gate_service.get_latest_gate(model.id)
        )

        if not gate or not gate.gate_passed:
            failed_conditions = []
            if not gate or not gate.locked_test_evaluated:
                failed_conditions.append("locked_test_evaluated")
            if not gate or not gate.schema_locked:
                failed_conditions.append("schema_locked")
            if not gate or not gate.artifact_verified:
                failed_conditions.append("artifact_verified")
            if not gate or not gate.lineage_complete:
                failed_conditions.append("lineage_complete")
            if not gate or gate.performance_threshold_passed != "PASS":
                status_label = gate.performance_threshold_passed if gate else "UNVERIFIABLE"
                failed_conditions.append(f"performance_threshold_passed: {status_label}")
            if not gate or not gate.user_approved:
                failed_conditions.append("user_approved")

            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Deployment gate check failed. Unmet conditions: {', '.join(failed_conditions)}",
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
            status="LIVE",
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
        deployment = self.db.query(Deployment).filter(Deployment.id == deployment_id).first()
        if not deployment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Deployment not found",
            )

        if deployment.status == "RETIRED":
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Cannot pause a RETIRED deployment. Retired deployments are immutable.",
            )

        deployment.status = "PAUSED"
        self.db.add(deployment)
        self.db.commit()
        self.db.refresh(deployment)
        return deployment

    def retire(self, deployment_id: UUID | str) -> Deployment:
        """
        Permanently retires a deployment. Cannot be un-retired.
        """
        deployment = self.db.query(Deployment).filter(Deployment.id == deployment_id).first()
        if not deployment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Deployment not found",
            )

        deployment.status = "RETIRED"
        self.db.add(deployment)
        self.db.commit()
        self.db.refresh(deployment)
        return deployment

    def update_status(self, deployment_id: UUID | str, target_status: str) -> Deployment:
        """
        Transitions deployment status respecting the state machine rules:
        - LIVE -> PAUSED
        - PAUSED -> LIVE
        - LIVE -> RETIRED
        - PAUSED -> RETIRED
        - RETIRED -> (ANY) is strictly rejected
        """
        status_norm = target_status.upper().strip()
        if status_norm not in {"LIVE", "PAUSED", "RETIRED"}:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid target status '{target_status}'. Allowed values: LIVE, PAUSED, RETIRED.",
            )

        deployment = self.db.query(Deployment).filter(Deployment.id == deployment_id).first()
        if not deployment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Deployment not found",
            )

        if deployment.status == "RETIRED":
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="A RETIRED deployment can never transition back to LIVE or PAUSED. Create a new deployment instead.",
            )

        deployment.status = status_norm
        self.db.add(deployment)
        self.db.commit()
        self.db.refresh(deployment)
        return deployment

    def get_by_id(self, deployment_id: UUID | str) -> Deployment | None:
        return self.db.query(Deployment).filter(Deployment.id == deployment_id).first()
