import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, ForeignKey, DateTime, UniqueConstraint, CheckConstraint, Uuid, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base

class DatasetSplit(Base):
    __tablename__ = "dataset_splits"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    dataset_id = Column(Uuid(as_uuid=True), ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False, index=True)
    split_type = Column(String(20), nullable=False)
    split_seed = Column(Integer, nullable=False)
    row_indices = Column(JSON, nullable=False)
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    __table_args__ = (
        CheckConstraint(
            "split_type IN ('DEVELOPMENT', 'LOCKED_TEST')",
            name="chk_dataset_split_type"
        ),
        UniqueConstraint("dataset_id", "split_type", name="uq_dataset_split_type"),
    )

    dataset = relationship("Dataset", back_populates="splits")

    def __repr__(self) -> str:
        return f"<DatasetSplit dataset_id={self.dataset_id} type={self.split_type} seed={self.split_seed}>"
