from uuid import UUID as PyUUID
from sqlalchemy.orm import Session
from app.models.dataset_split import DatasetSplit
from app.repositories.base import BaseRepository, safe_uuid

class DatasetSplitRepository(BaseRepository[DatasetSplit]):
    def __init__(self, db: Session):
        super().__init__(DatasetSplit, db)

    def get_by_dataset(self, dataset_id: PyUUID | str) -> list[DatasetSplit]:
        parsed_id = safe_uuid(dataset_id)
        if parsed_id is None:
            return []
        return (
            self.db.query(DatasetSplit)
            .filter(DatasetSplit.dataset_id == parsed_id)
            .all()
        )

    def get_by_dataset_and_type(self, dataset_id: PyUUID | str, split_type: str) -> DatasetSplit | None:
        parsed_id = safe_uuid(dataset_id)
        if parsed_id is None:
            return None
        return (
            self.db.query(DatasetSplit)
            .filter(
                DatasetSplit.dataset_id == parsed_id,
                DatasetSplit.split_type == split_type
            )
            .first()
        )

    def has_split(self, dataset_id: PyUUID | str) -> bool:
        parsed_id = safe_uuid(dataset_id)
        if parsed_id is None:
            return False
        return (
            self.db.query(DatasetSplit)
            .filter(DatasetSplit.dataset_id == parsed_id)
            .first()
            is not None
        )

    def create_splits(self, splits: list[DatasetSplit]) -> list[DatasetSplit]:
        self.db.add_all(splits)
        self.db.commit()
        for s in splits:
            self.db.refresh(s)
        return splits
