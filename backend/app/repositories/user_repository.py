from uuid import UUID as PyUUID
from sqlalchemy.orm import Session
from app.models.user import User
from app.models.role import Role
from app.models.permission import Permission
from app.repositories.base import BaseRepository

class UserRepository(BaseRepository[User]):
    def __init__(self, db: Session):
        super().__init__(User, db)

    def get_by_email(self, email: str) -> User | None:
        return self.db.query(User).filter(User.email == email.lower().strip()).first()

    def get_role_by_name(self, role_name: str) -> Role | None:
        return self.db.query(Role).filter(Role.role_name == role_name).first()

    def get_role_by_id(self, role_id: PyUUID | str) -> Role | None:
        if isinstance(role_id, str):
            try:
                role_id = PyUUID(role_id)
            except Exception:
                pass
        return self.db.query(Role).filter(Role.id == role_id).first()

    def get_all_roles(self) -> list[Role]:
        return self.db.query(Role).all()

    def get_permission_by_key(self, permission_key: str) -> Permission | None:
        return self.db.query(Permission).filter(Permission.permission_key == permission_key).first()

    def get_all_permissions(self) -> list[Permission]:
        return self.db.query(Permission).all()
