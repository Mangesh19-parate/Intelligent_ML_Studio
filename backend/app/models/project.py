import uuid
from sqlalchemy import Column, String, ForeignKey, CheckConstraint, Numeric, Uuid
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.models.base import TimestampMixin

class Project(Base, TimestampMixin):
    __tablename__ = "projects"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owner_id = Column(Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    project_name = Column(String(200), nullable=False)
    task_type = Column(
        String(30),
        nullable=False,
        default="UNDETERMINED",
        server_default="UNDETERMINED"
    )
    target_column = Column(String(150), nullable=True)
    pipeline_stage = Column(String(40), nullable=False, default="DATA", server_default="DATA")
    data_quality_index = Column(Numeric(5, 2), nullable=True)
    task_type_confidence = Column(String(20), nullable=True)

    __table_args__ = (
        CheckConstraint(
            "task_type IN ('REGRESSION', 'CLASSIFICATION', 'UNDETERMINED')",
            name="chk_project_task_type"
        ),
    )

    owner = relationship("User", back_populates="projects")
    datasets = relationship("Dataset", back_populates="project", cascade="all, delete-orphan", order_by="desc(Dataset.version_number)")
    recommendations = relationship("Recommendation", back_populates="project", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Project {self.project_name} ({self.task_type})>"
