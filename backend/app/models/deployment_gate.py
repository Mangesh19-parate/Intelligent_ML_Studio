import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, ForeignKey, DateTime, Uuid, Boolean, CheckConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


class DeploymentGate(Base):
    """
    Model Deployment Gate Table (Day 10).
    
    ARCHITECTURAL NOTE (SRS §2.14 / §2.16):
    Tracks comprehensive pre-deployment verification results across 6 explicit conditions:
    1. locked_test_evaluated: evaluation on locked test split completed
    2. schema_locked: dynamic input feature schema resolved
    3. artifact_verified: SHA-256 integrity checksum rechecked on disk
    4. lineage_complete: all snapshots and environment variables captured
    5. performance_threshold_passed: tri-state ('PASS', 'FAIL', 'UNVERIFIABLE')
    6. user_approved: explicit sign-off by privileged user (DEPLOY permission)
    
    Audit Invariant: Every gate check computes a new immutable audit record.
    """
    __tablename__ = "deployment_gates"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    model_id = Column(
        Uuid(as_uuid=True),
        ForeignKey("trained_models.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    locked_test_evaluated = Column(Boolean, nullable=False)
    schema_locked = Column(Boolean, nullable=False)
    artifact_verified = Column(Boolean, nullable=False)
    lineage_complete = Column(Boolean, nullable=False)
    performance_threshold_passed = Column(String(15), nullable=False)
    user_approved = Column(Boolean, nullable=False, default=False, server_default="false")
    gate_passed = Column(Boolean, nullable=False)
    evaluated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    __table_args__ = (
        CheckConstraint(
            "performance_threshold_passed IN ('PASS', 'FAIL', 'UNVERIFIABLE')",
            name="chk_deployment_gate_perf_threshold"
        ),
    )

    model = relationship("TrainedModel", back_populates="deployment_gates", foreign_keys=[model_id])

    def __repr__(self) -> str:
        return f"<DeploymentGate id={self.id} model_id={self.model_id} gate_passed={self.gate_passed} perf={self.performance_threshold_passed}>"
