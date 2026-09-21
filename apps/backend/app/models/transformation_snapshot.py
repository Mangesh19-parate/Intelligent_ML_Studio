import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, ForeignKey, DateTime, Uuid, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base

class TransformationSnapshot(Base):
    """
    Transformation Snapshots Table (Day 8).
    
    ARCHITECTURAL NOTE (SRS §2.6, §2.17):
    A full frozen deep copy of transformation_configs for this project at the exact
    moment the experiment is created. Never a live reference, completely immutable.
    """
    __tablename__ = "transformation_snapshots"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    experiment_id = Column(
        Uuid(as_uuid=True),
        ForeignKey("experiments.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    config_json = Column(JSON, nullable=False)
    
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    experiment = relationship("Experiment", back_populates="transformation_snapshots", foreign_keys=[experiment_id])

    def __repr__(self) -> str:
        return f"<TransformationSnapshot id={self.id} experiment_id={self.experiment_id}>"
