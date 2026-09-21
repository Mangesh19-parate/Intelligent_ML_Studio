import uuid
from sqlalchemy import Column, String, Integer, ForeignKey, Boolean, Numeric, CheckConstraint, Uuid
from sqlalchemy.orm import relationship
from app.core.database import Base

class DatasetColumn(Base):
    __tablename__ = "dataset_columns"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    dataset_id = Column(Uuid(as_uuid=True), ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False, index=True)
    column_name = Column(String(150), nullable=False)
    data_type = Column(String(30), nullable=False)
    unique_count = Column(Integer, nullable=False, default=0)
    missing_percentage = Column(Numeric(5, 2), nullable=False, default=0.00)
    is_target = Column(Boolean, nullable=False, default=False)

    __table_args__ = (
        CheckConstraint(
            "data_type IN ('NUMERIC', 'CATEGORICAL', 'DATETIME', 'MIXED')",
            name="chk_column_data_type"
        ),
    )

    dataset = relationship("Dataset", back_populates="columns")

    def __repr__(self) -> str:
        return f"<DatasetColumn {self.column_name} ({self.data_type})>"
