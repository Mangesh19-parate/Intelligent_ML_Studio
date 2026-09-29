from uuid import uuid4
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime
from app.models.base import Base

class WorkerHeartbeat(Base):
    """
    Worker Heartbeat Model (P1-04).
    Tracks active worker processes, versions, and live heartbeats independently of individual tasks.
    """
    __tablename__ = "worker_heartbeats"

    id = Column(String(64), primary_key=True, default=lambda: str(uuid4()))
    worker_id = Column(String(128), unique=True, nullable=False, index=True)
    hostname = Column(String(256), nullable=True)
    version = Column(String(64), nullable=True)
    status = Column(String(32), default="ONLINE", nullable=False)
    started_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    last_seen_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True)
