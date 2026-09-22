"""
Application Use Case: Create Experiment.
Validates business invariants and records experiment metadata with immutable snapshots.
"""

from uuid import UUID
from typing import Any
from sqlalchemy.orm import Session
from app.domain.experiment.policies import validate_cv_folds, validate_metric_direction
from app.repositories.experiment_repository import ExperimentRepository
from app.repositories.project_repository import ProjectRepository
from app.core.versioning import get_code_version, get_environment_metadata
from app.models.experiment import Experiment


def create_experiment_use_case(
    db: Session,
    project_id: UUID | str,
    task_type: str | None = None,
    fold_count: int = 5,
    cv_seed: int = 42,
    selection_metric: str | None = None,
    selection_direction: str | None = None,
    experiment_config: dict[str, Any] | None = None,
    created_by: UUID | str | None = None,
) -> Experiment:
    """
    Executes experiment creation use case:
    1. Validates project existence.
    2. Enforces cross-validation fold invariants and metric optimization direction.
    3. Captures frozen environment metadata & code hash.
    4. Persists new Experiment entity.
    """
    proj_repo = ProjectRepository(db)
    project = proj_repo.get_by_id(project_id)
    if not project:
        raise ValueError(f"Project with ID '{project_id}' does not exist.")

    # Domain invariants validation
    validated_folds = validate_cv_folds(fold_count)
    default_metric = selection_metric or ("macro_f1" if (task_type or "CLASSIFICATION").upper() == "CLASSIFICATION" else "rmse")
    validated_direction = validate_metric_direction(default_metric, selection_direction)

    env_meta = get_environment_metadata()
    code_version = get_code_version()

    exp_repo = ExperimentRepository(db)
    experiment = exp_repo.create_experiment(
        project_id=project_id,
        task_type=task_type or "CLASSIFICATION",
        fold_count=validated_folds,
        cv_seed=cv_seed,
        selection_metric=default_metric,
        selection_direction=validated_direction,
        status="CREATED",
        experiment_config=experiment_config or {},
        dataset_content_hash=getattr(project, "dataset_content_hash", None),
        code_version=code_version,
        python_version=env_meta.get("python_version"),
        sklearn_version=env_meta.get("sklearn_version"),
        numpy_version=env_meta.get("numpy_version"),
        pandas_version=env_meta.get("pandas_version"),
        model_library_versions=env_meta.get("model_library_versions"),
        environment_capture_method=env_meta.get("environment_capture_method"),
    )
    return experiment
