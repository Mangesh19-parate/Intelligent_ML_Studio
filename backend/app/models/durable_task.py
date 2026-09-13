import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, Text, DateTime, ForeignKey, JSON, Uuid
from sqlalchemy.orm import relationship

from app.core.database import Base


class DurableTask(Base):
    """
    Persistent backing store for asynchronous durable tasks (P0.1).
    Guarantees that task state, worker assignment, timestamps, and idempotency
    survive worker restarts and server reboots.
    """
    __tablename__ = "durable_tasks"

    id = Column(String(64), primary_key=True, default=lambda: f"task-{uuid.uuid4()}")
    experiment_id = Column(
        Uuid(as_uuid=True),
        ForeignKey("experiments.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    state = Column(String(32), nullable=False, default="QUEUED", index=True)
    idempotency_key = Column(String(128), unique=True, nullable=True, index=True)
    retry_count = Column(Integer, nullable=False, default=0)
    max_retries = Column(Integer, nullable=False, default=3)
    timeout_seconds = Column(Integer, nullable=False, default=600)
    worker_id = Column(String(128), nullable=True)
    
    queued_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    started_at = Column(DateTime(timezone=True), nullable=True)
    finished_at = Column(DateTime(timezone=True), nullable=True)
    failure_reason = Column(Text, nullable=True)
    result_summary = Column(JSON, nullable=True)

    experiment = relationship("Experiment", backref="durable_tasks")

    def __repr__(self) -> str:
        return f"<DurableTask id={self.id} exp={self.experiment_id} state={self.state}>"
