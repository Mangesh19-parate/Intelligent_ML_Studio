from uuid import UUID as PyUUID
from sqlalchemy import func
from sqlalchemy.orm import Session
from app.models.dataset import Dataset
from app.models.dataset_column import DatasetColumn
from app.repositories.base import BaseRepository

class DatasetRepository(BaseRepository[Dataset]):
    def __init__(self, db: Session):
        super().__init__(Dataset, db)

    def get_next_version_number(self, project_id: PyUUID | str) -> int:
        if isinstance(project_id, str):
            try:
                project_id = PyUUID(project_id)
            except Exception:
                pass
        max_ver = (
            self.db.query(func.max(Dataset.version_number))
            .filter(Dataset.project_id == project_id)
            .scalar()
        )
        return (max_ver or 0) + 1

    def get_by_project(self, project_id: PyUUID | str) -> list[Dataset]:
        if isinstance(project_id, str):
            try:
                project_id = PyUUID(project_id)
            except Exception:
                pass
        return (
            self.db.query(Dataset)
            .filter(Dataset.project_id == project_id)
            .order_by(Dataset.version_number.desc())
            .all()
        )

    def get_columns_by_dataset(self, dataset_id: PyUUID | str) -> list[DatasetColumn]:
        if isinstance(dataset_id, str):
            try:
                dataset_id = PyUUID(dataset_id)
            except Exception:
                pass
        return (
            self.db.query(DatasetColumn)
            .filter(DatasetColumn.dataset_id == dataset_id)
            .order_by(DatasetColumn.column_name)
            .all()
        )

    def create_columns_bulk(self, columns: list[DatasetColumn]) -> list[DatasetColumn]:
        self.db.add_all(columns)
        self.db.commit()
        return columns
