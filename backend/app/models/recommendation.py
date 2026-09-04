import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, ForeignKey, DateTime, Uuid, CheckConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base

class Recommendation(Base):
    __tablename__ = "recommendations"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(
        Uuid(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    finding = Column(Text, nullable=False)
    evidence = Column(Text, nullable=False)
    recommended_action = Column(Text, nullable=False)
    risk_note = Column(Text, nullable=False)
    confidence = Column(String(10), nullable=False)
    status = Column(String(20), nullable=False, default="SUGGESTED", server_default="SUGGESTED")
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    __table_args__ = (
        CheckConstraint(
            "confidence IN ('HIGH', 'MEDIUM', 'LOW')",
            name="chk_recommendation_confidence"
        ),
    )

    project = relationship("Project", back_populates="recommendations")

    def __repr__(self) -> str:
        return f"<Recommendation id={self.id} project_id={self.project_id} confidence={self.confidence}>"
