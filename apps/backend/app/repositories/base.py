from typing import Generic, TypeVar, Type, Any
from uuid import UUID as PyUUID
from sqlalchemy.orm import Session

ModelType = TypeVar("ModelType")


def safe_uuid(val: Any) -> PyUUID | None:
    """Safely converts string or UUID to PyUUID object, returning None on invalid format."""
    if isinstance(val, PyUUID):
        return val
    if isinstance(val, str):
        try:
            return PyUUID(val)
        except (ValueError, TypeError, AttributeError):
            return None
    return None


class BaseRepository(Generic[ModelType]):
    def __init__(self, model: Type[ModelType], db: Session):
        self.model = model
        self.db = db

    def get_by_id(self, id: PyUUID | str) -> ModelType | None:
        parsed_id = safe_uuid(id)
        if parsed_id is None:
            return None
        return self.db.query(self.model).filter(self.model.id == parsed_id).first()

    def get_all(self, skip: int = 0, limit: int = 100) -> list[ModelType]:
        return self.db.query(self.model).offset(skip).limit(limit).all()

    def create(self, obj: ModelType) -> ModelType:
        self.db.add(obj)
        self.db.commit()
        self.db.refresh(obj)
        return obj

    def update(self, obj: ModelType) -> ModelType:
        self.db.commit()
        self.db.refresh(obj)
        return obj

    def delete(self, obj: ModelType) -> None:
        self.db.delete(obj)
        self.db.commit()
