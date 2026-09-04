import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, ForeignKey, DateTime, Uuid, Numeric, Text, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base

class TrainedModel(Base):
    """
    Trained models table (Day 6 first pass).
    
    ARCHITECTURAL NOTE (SRS §2.8):
    - quick_cv_score: TEMPORARY sanity metric (R2 for regression, Accuracy for classification)
      to prove the fit->predict roundtrip works end to end across CV folds.
      Superseded by Day 7's real model_metrics table — do not treat this as the final leaderboard.
    - Full lineage/checksum/readiness columns are added on Day 7/8.
    - Day 6 trains algorithms over cross-validation folds and averages fold quick scores.
    """
    __tablename__ = "trained_models"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    experiment_id = Column(
        Uuid(as_uuid=True),
        ForeignKey("experiments.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    algorithm_name = Column(String(60), nullable=False)
    hyperparameters = Column(JSON, nullable=False, default=dict)
    
    # TEMPORARY sanity metric, superseded by Day 7's real model_metrics table — do not treat this as the leaderboard.
    quick_cv_score = Column(Numeric(10, 5), nullable=True)
    status = Column(String(20), nullable=False, default="COMPLETED", server_default="COMPLETED")
    error_message = Column(Text, nullable=True)
    
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    experiment = relationship("Experiment", back_populates="trained_models")

    def __repr__(self) -> str:
        return f"<TrainedModel id={self.id} algorithm={self.algorithm_name} score={self.quick_cv_score} status={self.status}>"
