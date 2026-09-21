import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, ForeignKey, DateTime, Uuid, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base

class FeatureSelectionSnapshot(Base):
    """
    Feature Selection Snapshots Table (Day 8).
    
    ARCHITECTURAL NOTE (SRS §2.7, §2.17):
    Stores the final selected feature list and selection method produced during
    the final refit on the full Development partition (not fold-level selection).
    """
    __tablename__ = "feature_selection_snapshots"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    experiment_id = Column(
        Uuid(as_uuid=True),
        ForeignKey("experiments.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    final_selected_features = Column(JSON, nullable=False)
    final_selection_method = Column(String(30), nullable=False, default="rank_aggregation_ensemble")
    
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    experiment = relationship("Experiment", back_populates="feature_selection_snapshots", foreign_keys=[experiment_id])

    def __repr__(self) -> str:
        return f"<FeatureSelectionSnapshot id={self.id} experiment_id={self.experiment_id} method={self.final_selection_method}>"
