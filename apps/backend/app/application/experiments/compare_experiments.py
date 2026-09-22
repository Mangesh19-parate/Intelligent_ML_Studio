"""
Application Use Case: Compare Experiments.
Aggregates model performance, validation metrics, and governance flags across experiments.
"""

from uuid import UUID
from typing import Any
from sqlalchemy.orm import Session
from app.repositories.experiment_repository import ExperimentRepository


def compare_experiments_use_case(
    db: Session,
    experiment_ids: list[UUID | str],
) -> list[dict[str, Any]]:
    """
    Returns comparative metric summaries across multiple experiments.
    """
    exp_repo = ExperimentRepository(db)
    comparison = []

    for exp_id in experiment_ids:
        exp = exp_repo.get_with_models(exp_id)
        if not exp:
            continue

        models_data = []
        for model in exp.trained_models:
            metrics_dict = {}
            for m in model.metrics:
                key = f"{m.metric_name}_{m.split.lower()}" if m.split else m.metric_name
                metrics_dict[key] = m.metric_value

            models_data.append({
                "model_id": str(model.id),
                "algorithm_name": model.algorithm_name,
                "status": model.status,
                "model_selection_score": model.model_selection_score,
                "quick_cv_score": model.quick_cv_score,
                "fit_diagnosis": model.fit_diagnosis,
                "decision_threshold": model.decision_threshold,
                "metrics": metrics_dict,
            })

        comparison.append({
            "experiment_id": str(exp.id),
            "project_id": str(exp.project_id),
            "status": exp.status,
            "task_type": exp.task_type,
            "selection_metric": exp.selection_metric,
            "selected_model_id": str(exp.selected_model_id) if exp.selected_model_id else None,
            "models": models_data,
        })

    return comparison
