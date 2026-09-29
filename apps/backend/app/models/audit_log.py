from uuid import uuid4
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, JSON
from app.models.base import Base

class AuditLog(Base):
    """
    Dedicated Security Audit Log table (P1-05).
    Persists immutable security and system events: PASSWORD_RESET, PERMISSION_OVERRIDE, etc.
    """
    __tablename__ = "audit_logs"

    id = Column(String(64), primary_key=True, default=lambda: str(uuid4()))
    event_type = Column(String(64), nullable=False, index=True)
    actor_id = Column(String(64), nullable=True, index=True)
    target_user_id = Column(String(64), nullable=True, index=True)
    ip_address = Column(String(64), nullable=True)
    user_agent = Column(String(256), nullable=True)
    status = Column(String(32), default="SUCCESS", nullable=False)
    summary = Column(String(512), nullable=False)
    details = Column(JSON, default=dict, nullable=True)
    timestamp = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True)
