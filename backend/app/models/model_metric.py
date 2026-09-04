import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, ForeignKey, DateTime, Uuid, Numeric, JSON, Integer, CheckConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base

class ModelMetric(Base):
    """
    Model Metrics Table (Day 7).
    
    Stores evaluation metrics across dataset splits:
    - 'TRAIN': Training split evaluation (either per CV fold or final full-Development refit)
    - 'VALIDATION': Validation split evaluation per CV fold
    - 'CV_MEAN': Average validation metric across all CV folds
    - 'LOCKED_TEST': Evaluated once for the winning model only
    - 'TEST_REUSED_DIAGNOSTIC': Re-evaluations for diagnostic/debugging only
    """
    __tablename__ = "model_metrics"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    model_id = Column(
        Uuid(as_uuid=True),
        ForeignKey("trained_models.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    metric_name = Column(String(40), nullable=False)
    split = Column(String(30), nullable=False)
    metric_value = Column(Numeric(10, 5), nullable=True)
    metric_json = Column(JSON, nullable=True)
    fold_index = Column(Integer, nullable=True)

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    __table_args__ = (
        CheckConstraint(
            "split IN ('TRAIN', 'VALIDATION', 'CV_MEAN', 'LOCKED_TEST', 'TEST_REUSED_DIAGNOSTIC')",
            name="chk_model_metric_split"
        ),
    )

    model = relationship("TrainedModel", back_populates="metrics")

    def __repr__(self) -> str:
        return f"<ModelMetric id={self.id} model_id={self.model_id} metric={self.metric_name} split={self.split} value={self.metric_value}>"
