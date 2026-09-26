from uuid import UUID as PyUUID
from sqlalchemy.orm import Session
from app.models.transformation_config import TransformationConfig
from app.repositories.base import BaseRepository, safe_uuid

class TransformationRepository(BaseRepository[TransformationConfig]):
    def __init__(self, db: Session):
        super().__init__(TransformationConfig, db)

    def get_by_project(self, project_id: PyUUID | str) -> list[TransformationConfig]:
        parsed_id = safe_uuid(project_id)
        if parsed_id is None:
            return []
        return (
            self.db.query(TransformationConfig)
            .filter(TransformationConfig.project_id == parsed_id)
            .order_by(TransformationConfig.column_name)
            .all()
        )

    def get_by_project_and_column(
        self, project_id: PyUUID | str, column_name: str
    ) -> TransformationConfig | None:
        parsed_id = safe_uuid(project_id)
        if parsed_id is None:
            return None
        return (
            self.db.query(TransformationConfig)
            .filter(
                TransformationConfig.project_id == parsed_id,
                TransformationConfig.column_name == column_name,
            )
            .first()
        )

    def upsert_config(
        self,
        project_id: PyUUID | str,
        column_name: str,
        update_data: dict,
    ) -> TransformationConfig:
        parsed_id = safe_uuid(project_id)
        config = self.get_by_project_and_column(parsed_id, column_name)
        if config:
            for key, val in update_data.items():
                if hasattr(config, key) and val is not None:
                    setattr(config, key, val)
            self.db.add(config)
            self.db.commit()
            self.db.refresh(config)
            return config
        else:
            config = TransformationConfig(
                project_id=parsed_id,
                column_name=column_name,
                **update_data
            )
            self.db.add(config)
            self.db.commit()
            self.db.refresh(config)
            return config
