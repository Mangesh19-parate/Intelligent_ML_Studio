import uuid
from sqlalchemy import Column, String, Text, Uuid
from sqlalchemy.orm import relationship
from app.core.database import Base

class Role(Base):
    __tablename__ = "roles"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    role_name = Column(String(50), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)

    permissions = relationship("Permission", secondary="role_permissions", back_populates="roles", lazy="joined")
    users = relationship("User", back_populates="role")

    def __repr__(self) -> str:
        return f"<Role {self.role_name}>"
