import uuid
from sqlalchemy import Column, String, Boolean, ForeignKey, Uuid
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.models.base import TimestampMixin

class User(Base, TimestampMixin):
    __tablename__ = "users"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    full_name = Column(String(150), nullable=False)
    email = Column(String(150), unique=True, nullable=False, index=True)
    password_hash = Column(String, nullable=False)
    role_id = Column(Uuid(as_uuid=True), ForeignKey("roles.id", ondelete="RESTRICT"), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

    role = relationship("Role", back_populates="users", lazy="joined")
    projects = relationship("Project", back_populates="owner", cascade="all, delete-orphan")
    datasets = relationship("Dataset", back_populates="uploader")
    permission_overrides = relationship(
        "UserPermissionOverride",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="joined"
    )

    def __repr__(self) -> str:
        return f"<User {self.email}>"
