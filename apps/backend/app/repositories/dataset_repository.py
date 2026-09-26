from uuid import UUID as PyUUID
from sqlalchemy import func
from sqlalchemy.orm import Session
from app.models.dataset import Dataset
from app.models.dataset_column import DatasetColumn
from app.repositories.base import BaseRepository, safe_uuid

class DatasetRepository(BaseRepository[Dataset]):
    def __init__(self, db: Session):
        super().__init__(Dataset, db)

    def get_next_version_number(self, project_id: PyUUID | str) -> int:
        parsed_id = safe_uuid(project_id)
        max_ver = (
            self.db.query(func.max(Dataset.version_number))
            .filter(Dataset.project_id == parsed_id)
            .scalar()
        )
        return (max_ver or 0) + 1

    def get_by_project(self, project_id: PyUUID | str) -> list[Dataset]:
        parsed_id = safe_uuid(project_id)
        if parsed_id is None:
            return []
        return (
            self.db.query(Dataset)
            .filter(Dataset.project_id == parsed_id)
            .order_by(Dataset.version_number.desc())
            .all()
        )

    def get_by_project_and_hash(self, project_id: PyUUID | str, content_hash: str) -> Dataset | None:
        parsed_id = safe_uuid(project_id)
        if parsed_id is None:
            return None
        return (
            self.db.query(Dataset)
            .filter(Dataset.project_id == parsed_id, Dataset.content_hash == content_hash)
            .first()
        )

    def get_columns_by_dataset(self, dataset_id: PyUUID | str) -> list[DatasetColumn]:
        parsed_id = safe_uuid(dataset_id)
        if parsed_id is None:
            return []
        return (
            self.db.query(DatasetColumn)
            .filter(DatasetColumn.dataset_id == parsed_id)
            .order_by(DatasetColumn.column_name)
            .all()
        )

    def create_columns_bulk(self, columns: list[DatasetColumn]) -> list[DatasetColumn]:
        self.db.add_all(columns)
        self.db.commit()
        return columns
