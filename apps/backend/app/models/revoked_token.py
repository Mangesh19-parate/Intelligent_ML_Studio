import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, Uuid
from app.core.database import Base


class RevokedToken(Base):
    """
    Tracks consumed or revoked refresh tokens for cryptographic rotation and reuse detection (P1.3).
    If a previously consumed token is presented again, it triggers an immediate security alert and rejection.
    """
    __tablename__ = "revoked_tokens"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    token_hash = Column(String(64), unique=True, nullable=False, index=True)
    user_id = Column(Uuid(as_uuid=True), nullable=False, index=True)
    revoked_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    def __repr__(self) -> str:
        return f"<RevokedToken hash={self.token_hash[:8]}... user={self.user_id}>"
