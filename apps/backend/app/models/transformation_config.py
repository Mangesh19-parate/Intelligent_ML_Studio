import uuid
from sqlalchemy import Column, String, Boolean, ForeignKey, UniqueConstraint, Uuid
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.models.base import TimestampMixin

class TransformationConfig(Base, TimestampMixin):
    """
    Live, editable configuration for feature transformations per column.
    
    ARCHITECTURAL INVARIANT (SRS §2.6 / §4.2):
    - Stores declared transformation strategies only (strings), never learned parameters
      (e.g., fitted means, quantiles, vocabularies).
    - Distinct from frozen transformation_snapshots (Day 8).
    - Unique constraint on (project_id, column_name): one active config per column.
    """
    __tablename__ = "transformation_configs"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(
        Uuid(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    column_name = Column(String(150), nullable=False)
    missing_value_strategy = Column(String(30), nullable=True)
    encoding_strategy = Column(String(30), nullable=True)
    scaling_strategy = Column(String(30), nullable=True)
    outlier_strategy = Column(String(30), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True, server_default="true")

    __table_args__ = (
        UniqueConstraint("project_id", "column_name", name="uq_transformation_project_column"),
    )

    project = relationship("Project", back_populates="transformation_configs")

    def __repr__(self) -> str:
        return f"<TransformationConfig {self.column_name} (proj={self.project_id})>"
