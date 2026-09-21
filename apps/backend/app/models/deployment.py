import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, ForeignKey, DateTime, Uuid, CheckConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base
from app.config.state_machines import DeploymentState


class Deployment(Base):
    """
    Model Deployments Table (Day 10 / SRS v9 §2).
    
    ARCHITECTURAL NOTE (SRS §2.14 / §2.16 / SRS v9 §2):
    Represents an active or historical production inference endpoint.
    - Independent status column wired to DeploymentState enum.
    - Invariant: A RETIRED deployment is immutable and can NEVER return to DEPLOYED/LIVE or PAUSED.
    """
    __tablename__ = "deployments"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    model_id = Column(
        Uuid(as_uuid=True),
        ForeignKey("trained_models.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    endpoint_path = Column(String(200), nullable=False, unique=True)
    status = Column(String(30), nullable=False, default=DeploymentState.DEPLOYED.value, server_default="DEPLOYED")
    deployed_by = Column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
    deployed_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    log_retention_days = Column(Integer, nullable=False, default=30, server_default="30")

    __table_args__ = (
        CheckConstraint(
            "status IN ('CREATED', 'GATE_PENDING', 'GATE_PASSED', 'GATE_BLOCKED', 'APPROVED', 'DEPLOYED', 'PAUSED', 'RETIRED')",
            name="chk_deployment_status"
        ),
    )

    model = relationship("TrainedModel", back_populates="deployments", foreign_keys=[model_id])
    deployer = relationship("User", foreign_keys=[deployed_by])
    prediction_logs = relationship(
        "PredictionLog",
        back_populates="deployment",
        cascade="all, delete-orphan",
        order_by="PredictionLog.requested_at.desc()"
    )

    def __repr__(self) -> str:
        return f"<Deployment id={self.id} model_id={self.model_id} status={self.status} endpoint={self.endpoint_path}>"
