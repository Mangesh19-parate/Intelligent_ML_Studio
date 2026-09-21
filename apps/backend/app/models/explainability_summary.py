import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, ForeignKey, DateTime, Uuid, Integer, JSON, CheckConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base

class ExplainabilitySummary(Base):
    """
    Explainability Summaries Table (Day 9).
    
    ARCHITECTURAL NOTE (SRS §2.18 / §2.19):
    - Caches global SHAP explanation for the winning model of an experiment.
    - model_id is UNIQUE with a foreign key to trained_models.id, enforcing
      caching at the schema level rather than application-only logic.
    - explainer_type must be in ('TREE', 'LINEAR', 'KERNEL').
    """
    __tablename__ = "explainability_summaries"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    model_id = Column(
        Uuid(as_uuid=True),
        ForeignKey("trained_models.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True
    )
    shap_values = Column(JSON, nullable=False)
    background_sample_size = Column(Integer, nullable=False)
    explainer_type = Column(String(20), nullable=False)
    generated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    __table_args__ = (
        CheckConstraint(
            "explainer_type IN ('TREE', 'LINEAR', 'KERNEL')",
            name="chk_explainability_summary_explainer_type"
        ),
    )

    model = relationship("TrainedModel", back_populates="explainability_summary", foreign_keys=[model_id])

    def __repr__(self) -> str:
        return f"<ExplainabilitySummary id={self.id} model_id={self.model_id} explainer={self.explainer_type}>"
