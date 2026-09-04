from datetime import datetime, timezone
from uuid import UUID as PyUUID
from typing import Any
from sqlalchemy.orm import Session, joinedload
from app.models.experiment import Experiment
from app.models.feature_selection_fold_result import FeatureSelectionFoldResult
from app.models.trained_model import TrainedModel
from app.repositories.base import BaseRepository

class ExperimentRepository(BaseRepository[Experiment]):
    def __init__(self, db: Session):
        super().__init__(Experiment, db)

    def create_experiment(
        self,
        project_id: PyUUID | str,
        task_type: str | None = None,
        fold_count: int | None = None,
        cv_seed: int | None = None,
        status: str = "RUNNING",
    ) -> Experiment:
        if isinstance(project_id, str):
            try:
                project_id = PyUUID(project_id)
            except Exception:
                pass
        exp = Experiment(
            project_id=project_id,
            task_type=task_type,
            fold_count=fold_count,
            cv_seed=cv_seed,
            status=status,
        )
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
            .options(joinedload(Experiment.trained_models))
            .order_by(Experiment.created_at.desc())
            .all()
        )

    def get_with_models(self, experiment_id: PyUUID | str) -> Experiment | None:
        if isinstance(experiment_id, str):
            try:
                experiment_id = PyUUID(experiment_id)
            except Exception:
                pass
        return (
            self.db.query(Experiment)
            .filter(Experiment.id == experiment_id)
            .options(joinedload(Experiment.trained_models))
            .first()
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

    def add_trained_model(
        self,
        experiment_id: PyUUID | str,
        algorithm_name: str,
        hyperparameters: dict[str, Any],
        quick_cv_score: float | None = None,
        status: str = "COMPLETED",
        error_message: str | None = None,
    ) -> TrainedModel:
        if isinstance(experiment_id, str):
            try:
                experiment_id = PyUUID(experiment_id)
            except Exception:
                pass
        model_rec = TrainedModel(
            experiment_id=experiment_id,
            algorithm_name=algorithm_name,
            hyperparameters=hyperparameters,
            quick_cv_score=quick_cv_score,
            status=status,
            error_message=error_message,
        )
        self.db.add(model_rec)
        self.db.commit()
        self.db.refresh(model_rec)
        return model_rec

    def get_trained_models(self, experiment_id: PyUUID | str) -> list[TrainedModel]:
        if isinstance(experiment_id, str):
            try:
                experiment_id = PyUUID(experiment_id)
            except Exception:
                pass
        return (
            self.db.query(TrainedModel)
            .filter(TrainedModel.experiment_id == experiment_id)
            .order_by(TrainedModel.created_at.asc())
            .all()
        )
