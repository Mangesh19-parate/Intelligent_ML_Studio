from uuid import UUID as PyUUID
from sqlalchemy.orm import Session
from app.models.dataset_split import DatasetSplit
from app.repositories.base import BaseRepository

class DatasetSplitRepository(BaseRepository[DatasetSplit]):
    def __init__(self, db: Session):
        super().__init__(DatasetSplit, db)

    def get_by_dataset(self, dataset_id: PyUUID | str) -> list[DatasetSplit]:
        if isinstance(dataset_id, str):
            try:
                dataset_id = PyUUID(dataset_id)
            except Exception:
                pass
        return (
            self.db.query(DatasetSplit)
            .filter(DatasetSplit.dataset_id == dataset_id)
            .all()
        )

    def get_by_dataset_and_type(self, dataset_id: PyUUID | str, split_type: str) -> DatasetSplit | None:
        if isinstance(dataset_id, str):
            try:
                dataset_id = PyUUID(dataset_id)
            except Exception:
                pass
        return (
            self.db.query(DatasetSplit)
            .filter(
                DatasetSplit.dataset_id == dataset_id,
                DatasetSplit.split_type == split_type
            )
            .first()
        )

    def has_split(self, dataset_id: PyUUID | str) -> bool:
        if isinstance(dataset_id, str):
            try:
                dataset_id = PyUUID(dataset_id)
            except Exception:
                pass
        return (
            self.db.query(DatasetSplit)
            .filter(DatasetSplit.dataset_id == dataset_id)
            .first()
            is not None
        )

    def create_splits(self, splits: list[DatasetSplit]) -> list[DatasetSplit]:
        self.db.add_all(splits)
        self.db.commit()
        for s in splits:
            self.db.refresh(s)
        return splits
