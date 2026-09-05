import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, ForeignKey, DateTime, Uuid, Boolean, JSON, CheckConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


class PredictionLog(Base):
    """
    Prediction Logs Table (SRS §2.15 / Day 10).
    
    ARCHITECTURAL NOTE:
    Stores audit and observability data for all inference requests.
    - payload_mode:
      - 'OFF': No payload or hashing
      - 'HASHED': (Default) Input payload is NULL; schema_hash captures input format
      - 'REDACTED': Sanitized payload stored
      - 'FULL': Full raw input payload stored
    - status: 'SUCCESS', 'VALIDATION_ERROR', 'SERVER_ERROR' (Failed validation requests are audit-logged)
    - Decoupled latencies: latency_ms (base prediction) vs explanation_latency_ms (SHAP calculation)
    """
    __tablename__ = "prediction_logs"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    deployment_id = Column(
        Uuid(as_uuid=True),
        ForeignKey("deployments.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    request_id = Column(Uuid(as_uuid=True), nullable=False, default=uuid.uuid4, index=True)
    schema_hash = Column(String(64), nullable=False)
    payload_mode = Column(String(20), nullable=False, default="HASHED", server_default="HASHED")
    input_payload = Column(JSON, nullable=True)
    prediction_output = Column(JSON, nullable=True)
    latency_ms = Column(Integer, nullable=False)
    explanation_requested = Column(Boolean, nullable=False, default=False, server_default="false")
    explanation_latency_ms = Column(Integer, nullable=True)
    status = Column(String(20), nullable=False, default="SUCCESS", server_default="SUCCESS")
    requested_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True
    )

    __table_args__ = (
        CheckConstraint(
            "payload_mode IN ('OFF', 'HASHED', 'REDACTED', 'FULL')",
            name="chk_prediction_log_payload_mode"
        ),
        CheckConstraint(
            "status IN ('SUCCESS', 'VALIDATION_ERROR', 'SERVER_ERROR')",
            name="chk_prediction_log_status"
        ),
    )

    deployment = relationship("Deployment", back_populates="prediction_logs", foreign_keys=[deployment_id])

    def __repr__(self) -> str:
        return f"<PredictionLog id={self.id} deployment_id={self.deployment_id} status={self.status} latency={self.latency_ms}ms explain={self.explanation_requested}>"
