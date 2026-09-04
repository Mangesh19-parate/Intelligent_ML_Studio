from datetime import datetime, timezone
from uuid import UUID as PyUUID
from typing import Any
from sqlalchemy.orm import Session, joinedload
from app.models.experiment import Experiment
from app.models.feature_selection_fold_result import FeatureSelectionFoldResult
from app.models.trained_model import TrainedModel
from app.models.model_metric import ModelMetric
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
        selection_metric: str | None = None,
        selection_direction: str = "MAXIMIZE",
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
            selection_metric=selection_metric,
            selection_direction=selection_direction,
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
            .options(
                joinedload(Experiment.trained_models).joinedload(TrainedModel.metrics)
            )
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
            .options(
                joinedload(Experiment.trained_models).joinedload(TrainedModel.metrics)
            )
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

    def update_selection(
        self,
        experiment_id: PyUUID | str,
        selected_model_id: PyUUID | str,
        selection_metric: str | None = None,
        selection_direction: str | None = None,
    ) -> Experiment | None:
        if isinstance(experiment_id, str):
            try:
                experiment_id = PyUUID(experiment_id)
            except Exception:
                pass
        if isinstance(selected_model_id, str):
            try:
                selected_model_id = PyUUID(selected_model_id)
            except Exception:
                pass
        exp = self.get_by_id(experiment_id)
        if exp:
            exp.selected_model_id = selected_model_id
            if selection_metric is not None:
                exp.selection_metric = selection_metric
            if selection_direction is not None:
                exp.selection_direction = selection_direction
            self.db.add(exp)
            self.db.commit()
            self.db.refresh(exp)
        return exp

    def mark_locked_test_consumed(
        self,
        experiment_id: PyUUID | str,
        consumed_at: datetime | None = None,
    ) -> Experiment | None:
        if isinstance(experiment_id, str):
            try:
                experiment_id = PyUUID(experiment_id)
            except Exception:
                pass
        exp = self.get_by_id(experiment_id)
        if exp:
            exp.locked_test_consumed = True
            exp.locked_test_consumed_at = consumed_at or datetime.now(timezone.utc)
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
        fit_diagnosis: str | None = None,
        model_selection_score: float | None = None,
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
            fit_diagnosis=fit_diagnosis,
            model_selection_score=model_selection_score,
            status=status,
            error_message=error_message,
        )
        self.db.add(model_rec)
        self.db.commit()
        self.db.refresh(model_rec)
        return model_rec

    def update_trained_model_fit(
        self,
        model_id: PyUUID | str,
        fit_diagnosis: str | None,
        model_selection_score: float | None,
        quick_cv_score: float | None = None,
    ) -> TrainedModel | None:
        if isinstance(model_id, str):
            try:
                model_id = PyUUID(model_id)
            except Exception:
                pass
        m = self.db.query(TrainedModel).filter(TrainedModel.id == model_id).first()
        if m:
            m.fit_diagnosis = fit_diagnosis
            m.model_selection_score = model_selection_score
            if quick_cv_score is not None:
                m.quick_cv_score = quick_cv_score
            self.db.add(m)
            self.db.commit()
            self.db.refresh(m)
        return m

    def get_trained_models(self, experiment_id: PyUUID | str) -> list[TrainedModel]:
        if isinstance(experiment_id, str):
            try:
                experiment_id = PyUUID(experiment_id)
            except Exception:
                pass
        return (
            self.db.query(TrainedModel)
            .filter(TrainedModel.experiment_id == experiment_id)
            .options(joinedload(TrainedModel.metrics))
            .order_by(TrainedModel.created_at.asc())
            .all()
        )

    def add_model_metric(
        self,
        model_id: PyUUID | str,
        metric_name: str,
        split: str,
        metric_value: float | None = None,
        metric_json: dict | list | None = None,
        fold_index: int | None = None,
    ) -> ModelMetric:
        if isinstance(model_id, str):
            try:
                model_id = PyUUID(model_id)
            except Exception:
                pass
        metric = ModelMetric(
            model_id=model_id,
            metric_name=metric_name,
            split=split,
            metric_value=metric_value,
            metric_json=metric_json,
            fold_index=fold_index,
        )
        self.db.add(metric)
        self.db.commit()
        self.db.refresh(metric)
        return metric

    def add_model_metrics_batch(self, metrics: list[ModelMetric]) -> list[ModelMetric]:
        self.db.add_all(metrics)
        self.db.commit()
        return metrics

    def get_model_metrics(
        self,
        model_id: PyUUID | str,
        split: str | None = None,
    ) -> list[ModelMetric]:
        if isinstance(model_id, str):
            try:
                model_id = PyUUID(model_id)
            except Exception:
                pass
        q = self.db.query(ModelMetric).filter(ModelMetric.model_id == model_id)
        if split:
            q = q.filter(ModelMetric.split == split)
        return q.order_by(ModelMetric.created_at.asc()).all()

