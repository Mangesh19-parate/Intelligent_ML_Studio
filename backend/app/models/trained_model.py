import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, ForeignKey, DateTime, Uuid, Numeric, Text, JSON, CheckConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base

class TrainedModel(Base):
    """
    Trained models table (Day 7 updated).
    
    ARCHITECTURAL NOTE (SRS §2.8 / §2.9 / §2.10):
    - fit_diagnosis: 'GOOD_FIT', 'POTENTIAL_OVERFIT', 'POTENTIAL_UNDERFIT_WEAK_SIGNAL', 'INSUFFICIENT_DATA'
    - model_selection_score: composite convenience indicator (never used for leaderboard sorting)
    - metrics: relationship to ModelMetric table
    - Day 8 adds artifact checksum and snapshots.
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
    
    # TEMPORARY sanity metric from Day 6 (retained for backward compat, populated from CV mean primary metric)
    quick_cv_score = Column(Numeric(10, 5), nullable=True)
    
    # Day 7: Fit diagnosis and composite model selection score
    fit_diagnosis = Column(String(30), nullable=True)
    model_selection_score = Column(Numeric(5, 2), nullable=True)

    # Day 8: Model artifact serialization & snapshot links
    artifact_path = Column(Text, nullable=True)
    artifact_checksum = Column(String(64), nullable=True)
    preprocessing_snapshot_id = Column(
        Uuid(as_uuid=True),
        ForeignKey("transformation_snapshots.id", ondelete="SET NULL"),
        nullable=True
    )
    feature_selection_snapshot_id = Column(
        Uuid(as_uuid=True),
        ForeignKey("feature_selection_snapshots.id", ondelete="SET NULL"),
        nullable=True
    )
    
    status = Column(String(20), nullable=False, default="COMPLETED", server_default="COMPLETED")
    error_message = Column(Text, nullable=True)
    
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    __table_args__ = (
        CheckConstraint(
            "fit_diagnosis IS NULL OR fit_diagnosis IN ('GOOD_FIT', 'POTENTIAL_OVERFIT', 'POTENTIAL_UNDERFIT_WEAK_SIGNAL', 'INSUFFICIENT_DATA')",
            name="chk_trained_model_fit_diagnosis"
        ),
    )

    experiment = relationship(
        "Experiment",
        back_populates="trained_models",
        foreign_keys=[experiment_id]
    )
    preprocessing_snapshot = relationship(
        "TransformationSnapshot",
        foreign_keys=[preprocessing_snapshot_id]
    )
    feature_selection_snapshot = relationship(
        "FeatureSelectionSnapshot",
        foreign_keys=[feature_selection_snapshot_id]
    )
    metrics = relationship(
        "ModelMetric",
        back_populates="model",
        cascade="all, delete-orphan",
        order_by="ModelMetric.created_at"
    )
    explainability_summary = relationship(
        "ExplainabilitySummary",
        back_populates="model",
        uselist=False,
        cascade="all, delete-orphan"
    )
    deployment_gates = relationship(
        "DeploymentGate",
        back_populates="model",
        cascade="all, delete-orphan",
        order_by="DeploymentGate.evaluated_at.desc()"
    )
    deployments = relationship(
        "Deployment",
        back_populates="model",
        cascade="all, delete-orphan",
        order_by="Deployment.deployed_at.desc()"
    )

    def __repr__(self) -> str:
        return f"<TrainedModel id={self.id} algorithm={self.algorithm_name} score={self.quick_cv_score} fit={self.fit_diagnosis} checksum={self.artifact_checksum}>"

