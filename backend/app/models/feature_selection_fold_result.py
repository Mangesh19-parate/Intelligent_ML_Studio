import uuid
from sqlalchemy import Column, Integer, ForeignKey, UniqueConstraint, Uuid, JSON
from sqlalchemy.orm import relationship
from app.core.database import Base

class FeatureSelectionFoldResult(Base):
    """
    Per-fold feature selection execution record (SRS §2.17 / §4.2).
    
    ARCHITECTURAL INVARIANTS:
    - Stores fold-level selected features and technique scores (raw, rank, rank_score, status, status_reason).
    - Unique constraint on (experiment_id, fold_index).
    - Fold index validated in application code against [0, fold_count).
    """
    __tablename__ = "feature_selection_fold_results"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    experiment_id = Column(
        Uuid(as_uuid=True),
        ForeignKey("experiments.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    fold_index = Column(Integer, nullable=False)
    selected_features = Column(JSON, nullable=False)
    technique_scores = Column(JSON, nullable=False)

    __table_args__ = (
        UniqueConstraint("experiment_id", "fold_index", name="uq_fs_fold_results_exp_fold"),
    )

    experiment = relationship("Experiment", back_populates="feature_selection_fold_results")

    def __repr__(self) -> str:
        return f"<FeatureSelectionFoldResult exp={self.experiment_id} fold={self.fold_index}>"
