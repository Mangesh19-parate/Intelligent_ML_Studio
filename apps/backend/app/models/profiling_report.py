import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, ForeignKey, DateTime, Uuid, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base

class ProfilingReport(Base):
    __tablename__ = "profiling_reports"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    dataset_split_id = Column(
        Uuid(as_uuid=True),
        ForeignKey("dataset_splits.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True
    )
    report_json = Column(JSON, nullable=False)
    duplicate_row_count = Column(Integer, nullable=False, default=0)
    generated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    dataset_split = relationship("DatasetSplit", back_populates="profiling_report")

    def __repr__(self) -> str:
        return f"<ProfilingReport id={self.id} dataset_split_id={self.dataset_split_id}>"
