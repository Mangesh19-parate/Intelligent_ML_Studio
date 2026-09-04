import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, ForeignKey, DateTime, Uuid, Boolean, CheckConstraint, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base

class Experiment(Base):
    """
    Experiments execution tracking table.
    
    ARCHITECTURAL NOTE (SRS §2.5 / §2.9 / §2.12 / §2.17):
    - Day 5 shell table stores core execution tracking for CV feature selection fold attachments.
    - Day 6 ALTER adds task_type (frozen at start), fold_count, and cv_seed.
    - Day 7 ALTER adds selection_metric, selection_direction, selected_model_id,
      locked_test_consumed, and locked_test_consumed_at.
    - Day 8 ALTER adds full lineage columns (experiment_config, dataset_content_hash,
      versions, environment_capture_method, feature_selection_snapshot_id).
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

    # Day 7: Authoritative model selection & Locked Test single consumption
    selection_metric = Column(String(30), nullable=True)
    selection_direction = Column(String(10), nullable=False, default="MAXIMIZE", server_default="MAXIMIZE")
    selected_model_id = Column(
        Uuid(as_uuid=True),
        ForeignKey("trained_models.id", ondelete="SET NULL", use_alter=True, name="fk_experiments_selected_model_id"),
        nullable=True
    )

    locked_test_consumed = Column(Boolean, nullable=False, default=False, server_default="false")
    locked_test_consumed_at = Column(DateTime(timezone=True), nullable=True)

    # Day 8: Reproducibility, Lineage & Environment Capture
    experiment_config = Column(JSON, nullable=True)
    dataset_content_hash = Column(String(64), nullable=True)
    code_version = Column(String(50), nullable=True)
    python_version = Column(String(20), nullable=True)
    sklearn_version = Column(String(20), nullable=True)
    numpy_version = Column(String(20), nullable=True)
    pandas_version = Column(String(20), nullable=True)
    model_library_versions = Column(JSON, nullable=True)
    environment_capture_method = Column(String(20), nullable=True)
    feature_selection_snapshot_id = Column(
        Uuid(as_uuid=True),
        ForeignKey("feature_selection_snapshots.id", ondelete="SET NULL", use_alter=True, name="fk_experiments_fs_snapshot_id"),
        nullable=True
    )
    
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
        CheckConstraint("selection_direction IN ('MAXIMIZE', 'MINIMIZE')", name="chk_experiment_selection_direction"),
        CheckConstraint("environment_capture_method IS NULL OR environment_capture_method IN ('CAPTURED_LIVE', 'BACKFILLED_APPROXIMATE')", name="chk_experiment_env_capture_method"),
    )

    project = relationship("Project", back_populates="experiments")
    feature_selection_fold_results = relationship(
        "FeatureSelectionFoldResult",
        back_populates="experiment",
        cascade="all, delete-orphan",
        order_by="FeatureSelectionFoldResult.fold_index"
    )
    transformation_snapshots = relationship(
        "TransformationSnapshot",
        back_populates="experiment",
        cascade="all, delete-orphan",
        order_by="TransformationSnapshot.created_at",
        foreign_keys="TransformationSnapshot.experiment_id"
    )
    feature_selection_snapshots = relationship(
        "FeatureSelectionSnapshot",
        back_populates="experiment",
        cascade="all, delete-orphan",
        order_by="FeatureSelectionSnapshot.created_at",
        foreign_keys="FeatureSelectionSnapshot.experiment_id"
    )
    trained_models = relationship(
        "TrainedModel",
        back_populates="experiment",
        cascade="all, delete-orphan",
        order_by="TrainedModel.created_at",
        foreign_keys="TrainedModel.experiment_id"
    )
    selected_model = relationship(
        "TrainedModel",
        foreign_keys=[selected_model_id],
        post_update=True
    )
    final_feature_selection_snapshot = relationship(
        "FeatureSelectionSnapshot",
        foreign_keys=[feature_selection_snapshot_id],
        post_update=True
    )

    def __repr__(self) -> str:
        return f"<Experiment id={self.id} project_id={self.project_id} status={self.status} task_type={self.task_type} env_method={self.environment_capture_method}>"

