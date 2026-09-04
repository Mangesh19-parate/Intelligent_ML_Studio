from datetime import datetime, timezone
from uuid import UUID as PyUUID
from sqlalchemy.orm import Session
from app.models.experiment import Experiment
from app.models.feature_selection_fold_result import FeatureSelectionFoldResult
from app.repositories.base import BaseRepository

class ExperimentRepository(BaseRepository[Experiment]):
    def __init__(self, db: Session):
        super().__init__(Experiment, db)

    def create_experiment(self, project_id: PyUUID | str, status: str = "RUNNING") -> Experiment:
        if isinstance(project_id, str):
            try:
                project_id = PyUUID(project_id)
            except Exception:
                pass
        exp = Experiment(project_id=project_id, status=status)
        self.db.add(exp)
        self.db.commit()
        self.db.refresh(exp)
        return exp

    def get_by_project(self, project_id: PyUUID | str) -> list[Experiment]:
        if isinstance(project_id, str):
            try:
                project_id = PyUUID(project_id)
            except Exception:
                pass
        return (
            self.db.query(Experiment)
            .filter(Experiment.project_id == project_id)
            .order_by(Experiment.created_at.desc())
            .all()
        )

    def update_status(
        self,
        experiment_id: PyUUID | str,
        status: str,
        completed_at: datetime | None = None,
    ) -> Experiment | None:
        if isinstance(experiment_id, str):
            try:
                experiment_id = PyUUID(experiment_id)
            except Exception:
                pass
        exp = self.get_by_id(experiment_id)
        if exp:
            exp.status = status
            if completed_at is not None:
                exp.completed_at = completed_at
            elif status in ["COMPLETED", "FAILED"] and exp.completed_at is None:
                exp.completed_at = datetime.now(timezone.utc)
            self.db.add(exp)
            self.db.commit()
            self.db.refresh(exp)
        return exp

    def add_fold_result(
        self,
        experiment_id: PyUUID | str,
        fold_index: int,
        selected_features: list[str],
        technique_scores: dict,
    ) -> FeatureSelectionFoldResult:
        if isinstance(experiment_id, str):
            try:
                experiment_id = PyUUID(experiment_id)
            except Exception:
                pass
        fold_res = FeatureSelectionFoldResult(
            experiment_id=experiment_id,
            fold_index=fold_index,
            selected_features=selected_features,
            technique_scores=technique_scores,
        )
        self.db.add(fold_res)
        self.db.commit()
        self.db.refresh(fold_res)
        return fold_res

    def get_fold_results(self, experiment_id: PyUUID | str) -> list[FeatureSelectionFoldResult]:
        if isinstance(experiment_id, str):
            try:
                experiment_id = PyUUID(experiment_id)
            except Exception:
                pass
        return (
            self.db.query(FeatureSelectionFoldResult)
            .filter(FeatureSelectionFoldResult.experiment_id == experiment_id)
            .order_by(FeatureSelectionFoldResult.fold_index.asc())
            .all()
        )
