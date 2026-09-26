from uuid import UUID as PyUUID
from sqlalchemy.orm import Session
from app.models.project import Project
from app.repositories.base import BaseRepository, safe_uuid

from app.core.pagination import paginate_keyset

class ProjectRepository(BaseRepository[Project]):
    def __init__(self, db: Session):
        super().__init__(Project, db)

    def get_by_owner(self, owner_id: PyUUID | str, skip: int = 0, limit: int = 100) -> list[Project]:
        parsed_id = safe_uuid(owner_id)
        if parsed_id is None:
            return []
        return (
            self.db.query(Project)
            .filter(Project.owner_id == parsed_id)
            .order_by(Project.created_at.desc(), Project.id.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_by_owner_keyset(
        self,
        owner_id: PyUUID | str,
        cursor: str | None = None,
        limit: int = 50,
    ) -> tuple[list[Project], str | None, bool]:
        parsed_id = safe_uuid(owner_id)
        if parsed_id is None:
            return [], None, False
        q = self.db.query(Project).filter(Project.owner_id == parsed_id)
        return paginate_keyset(q, Project, cursor=cursor, limit=limit)

    def get_all_ordered(self, skip: int = 0, limit: int = 100) -> list[Project]:
        return (
            self.db.query(Project)
            .order_by(Project.created_at.desc(), Project.id.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_all_ordered_keyset(
        self,
        cursor: str | None = None,
        limit: int = 50,
    ) -> tuple[list[Project], str | None, bool]:
        q = self.db.query(Project)
        return paginate_keyset(q, Project, cursor=cursor, limit=limit)
