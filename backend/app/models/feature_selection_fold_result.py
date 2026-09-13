import uuid
from sqlalchemy import Column, String, Integer, Boolean, ForeignKey, UniqueConstraint, Uuid, JSON
from sqlalchemy.orm import relationship
from app.core.database import Base

class FeatureSelectionFoldResult(Base):
    """
    Per-fold feature selection execution and provenance record (P0.5 / SRS §2.17 / §4.2).
    
    ARCHITECTURAL INVARIANTS:
    - Stores fold-level selected features and technique scores (raw, rank, rank_score, status, status_reason).
    - Stores explicit fold-level leakage-safety provenance:
      * permutation_source (validation_fold)
      * locked_test_accessed (strictly False)
      * train_row_hash, validation_row_hash, test_row_hash
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
    selector = Column(String(100), nullable=True, default="RankAggregationSelector")
    permutation_source = Column(String(64), nullable=True, default="validation_fold")
    locked_test_accessed = Column(Boolean, nullable=False, default=False, server_default="false")
    train_row_hash = Column(String(64), nullable=True)
    validation_row_hash = Column(String(64), nullable=True)
    test_row_hash = Column(String(64), nullable=True)

    __table_args__ = (
        UniqueConstraint("experiment_id", "fold_index", name="uq_fs_fold_results_exp_fold"),
    )

    experiment = relationship("Experiment", back_populates="feature_selection_fold_results")

    def __repr__(self) -> str:
        return f"<FeatureSelectionFoldResult exp={self.experiment_id} fold={self.fold_index}>"
