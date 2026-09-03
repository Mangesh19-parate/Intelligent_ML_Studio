import uuid
from sqlalchemy import Column, String, Uuid
from sqlalchemy.orm import relationship
from app.core.database import Base

class Permission(Base):
    __tablename__ = "permissions"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    permission_key = Column(String(30), unique=True, nullable=False, index=True)

    roles = relationship("Role", secondary="role_permissions", back_populates="permissions")

    def __repr__(self) -> str:
        return f"<Permission {self.permission_key}>"
