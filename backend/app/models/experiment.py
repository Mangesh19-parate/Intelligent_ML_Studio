import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, ForeignKey, DateTime, Uuid, CheckConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base

class Experiment(Base):
    """
    Experiments execution tracking table.
    
    ARCHITECTURAL NOTE (SRS §2.5 / §2.17):
    - Day 5 shell table stores core execution tracking for CV feature selection fold attachments.
    - Day 6 ALTER adds task_type (frozen at start), fold_count, and cv_seed.
    - Day 8 will ALTER this table to add full lineage columns (experiment_config, dataset_content_hash, etc.).
    """
    __tablename__ = "experiments"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(
        Uuid(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    status = Column(
        String(20),
        nullable=False,
        default="RUNNING",
        server_default="RUNNING"
    )
    task_type = Column(String(30), nullable=True)
    fold_count = Column(Integer, nullable=True)
    cv_seed = Column(Integer, nullable=True)
    
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    completed_at = Column(
        DateTime(timezone=True),
        nullable=True
    )

    __table_args__ = (
        CheckConstraint("status IN ('RUNNING', 'COMPLETED', 'FAILED')", name="chk_experiment_status"),
    )

    project = relationship("Project", back_populates="experiments")
    feature_selection_fold_results = relationship(
        "FeatureSelectionFoldResult",
        back_populates="experiment",
        cascade="all, delete-orphan",
        order_by="FeatureSelectionFoldResult.fold_index"
    )
    trained_models = relationship(
        "TrainedModel",
        back_populates="experiment",
        cascade="all, delete-orphan",
        order_by="TrainedModel.created_at"
    )

    def __repr__(self) -> str:
        return f"<Experiment id={self.id} project_id={self.project_id} status={self.status} task_type={self.task_type}>"
