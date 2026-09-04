import uuid
from sqlalchemy import Column, String, Boolean, ForeignKey, Numeric, UniqueConstraint, Uuid
from sqlalchemy.orm import relationship
from app.core.database import Base

class FeatureImportanceScore(Base):
    """
    Aggregated feature importance scores (SRS §2.7 / §4.2).
    
    ARCHITECTURAL NOTE:
    - LIVE, editable-threshold table for UI rendering.
    - Stores averaged rank scores across folds of the latest run.
    - is_selected is updated dynamically based on user threshold adjustments.
    """
    __tablename__ = "feature_importance_scores"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(
        Uuid(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    column_name = Column(String(150), nullable=False)
    avg_rank_score = Column(Numeric(6, 4), nullable=False)
    is_selected = Column(Boolean, nullable=False, default=True, server_default="true")

    __table_args__ = (
        UniqueConstraint("project_id", "column_name", name="uq_feature_importance_project_col"),
    )

    project = relationship("Project", back_populates="feature_importance_scores")

    def __repr__(self) -> str:
        return f"<FeatureImportanceScore {self.column_name}: {self.avg_rank_score} selected={self.is_selected}>"
