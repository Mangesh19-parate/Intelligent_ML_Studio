import uuid
from sqlalchemy import Column, String, Boolean, ForeignKey, Uuid, UniqueConstraint
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.models.base import TimestampMixin


class UserPermissionOverride(Base, TimestampMixin):
    """
    Per-user permission override table.
    Allows explicitly granting (is_granted=True) or revoking (is_granted=False)
    a specific permission key for a given user, overriding role defaults.
    """
    __tablename__ = "user_permission_overrides"
    __table_args__ = (
        UniqueConstraint("user_id", "permission_key", name="uq_user_permission_override"),
    )

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    permission_key = Column(String(50), nullable=False, index=True)
    is_granted = Column(Boolean, nullable=False, default=True)

    user = relationship("User", back_populates="permission_overrides")

    def __repr__(self) -> str:
        status_str = "GRANT" if self.is_granted else "REVOKE"
        return f"<UserPermissionOverride user={self.user_id} perm={self.permission_key} ({status_str})>"
