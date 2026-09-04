import secrets
from uuid import UUID
from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import require_permission
from app.models.user import User
from app.repositories.project_repository import ProjectRepository
from app.repositories.experiment_repository import ExperimentRepository
from app.schemas.experiment import (
    ExperimentCreateRequest,
    ExperimentResponse,
    ExperimentCreateResponse,
    TrainedModelResponse,
)
from app.schemas.model_metric import SelectionRecordResponse, ModelMetricResponse
from app.services.experiment_service import ExperimentService

router = APIRouter(tags=["Model Training Experiments"])

@router.post(
    "/projects/{id}/experiments",
    response_model=ExperimentCreateResponse,
    status_code=status.HTTP_200_OK,
    summary="Kick off a Leakage-Safe Model Training Experiment with CV Comparison (TRAIN permission required)",
)
def create_experiment(
    id: UUID,
    payload: ExperimentCreateRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(require_permission("TRAIN")),
    db: Session = Depends(get_db),
):
    project_repo = ProjectRepository(db)
    exp_repo = ExperimentRepository(db)
    service = ExperimentService(db)

    project = project_repo.get_by_id(id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )

    if not project.target_column:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Project has no target column selected. Please configure target column first."
        )

    if project.task_type not in ["REGRESSION", "CLASSIFICATION"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Project task type must be either 'REGRESSION' or 'CLASSIFICATION' before training."
        )

    # Validate algorithms synchronously so unknown/mismatched algorithms reject immediately with 422
    canonical_algs = service.validate_algorithms(project.task_type, payload.algorithms)

    eff_metric, eff_direction = service.normalize_selection_metric(
        payload.selection_metric, project.task_type, payload.selection_direction
    )

    cv_seed = payload.seed if payload.seed is not None else secrets.randbelow(1_000_000)

    # Create Experiment shell record in RUNNING status
    experiment = exp_repo.create_experiment(
        project_id=project.id,
        task_type=project.task_type,
        fold_count=payload.folds,
        cv_seed=cv_seed,
        selection_metric=eff_metric,
        selection_direction=eff_direction,
        status="RUNNING",
    )

    # Kick off background execution
    background_tasks.add_task(
        ExperimentService.run_experiment_background,
        project_id=project.id,
        experiment_id=experiment.id,
        algorithms=canonical_algs,
        folds=payload.folds,
        seed=cv_seed,
        selection_metric=eff_metric,
        selection_direction=eff_direction,
    )

    return ExperimentCreateResponse(
        experiment_id=experiment.id,
        status="RUNNING",
        task_type=project.task_type,
        fold_count=payload.folds,
        cv_seed=cv_seed,
        selection_metric=eff_metric,
        selection_direction=eff_direction,
        message="Model training experiment started in background.",
    )


@router.get(
    "/experiments/{id}",
    response_model=ExperimentResponse,
    status_code=status.HTTP_200_OK,
    summary="Get status and trained models of an experiment (READ permission required)",
)
def get_experiment(
    id: UUID,
    current_user: User = Depends(require_permission("READ")),
    db: Session = Depends(get_db),
):
    exp_repo = ExperimentRepository(db)
    experiment = exp_repo.get_with_models(id)
    if not experiment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Experiment not found"
        )

    models_res = [
        TrainedModelResponse(
            id=m.id,
            experiment_id=m.experiment_id,
            algorithm_name=m.algorithm_name,
            hyperparameters=m.hyperparameters or {},
            quick_cv_score=float(m.quick_cv_score) if m.quick_cv_score is not None else None,
            fit_diagnosis=m.fit_diagnosis,
            model_selection_score=float(m.model_selection_score) if m.model_selection_score is not None else None,
            status=m.status,
            error_message=m.error_message,
            created_at=m.created_at,
            metrics=[
                ModelMetricResponse(
                    id=metric.id,
                    model_id=metric.model_id,
                    metric_name=metric.metric_name,
                    split=metric.split,
                    metric_value=float(metric.metric_value) if metric.metric_value is not None else None,
                    metric_json=metric.metric_json,
                    fold_index=metric.fold_index,
                    created_at=metric.created_at,
                )
                for metric in m.metrics
            ],
        )
        for m in experiment.trained_models
    ]

    return ExperimentResponse(
        id=experiment.id,
        project_id=experiment.project_id,
        status=experiment.status,
        task_type=experiment.task_type,
        fold_count=experiment.fold_count,
        cv_seed=experiment.cv_seed,
        selection_metric=experiment.selection_metric,
        selection_direction=experiment.selection_direction,
        selected_model_id=experiment.selected_model_id,
        locked_test_consumed=experiment.locked_test_consumed,
        locked_test_consumed_at=experiment.locked_test_consumed_at,
        created_at=experiment.created_at,
        completed_at=experiment.completed_at,
        trained_models=models_res,
    )


@router.get(
    "/experiments/{id}/selection",
    response_model=SelectionRecordResponse,
    status_code=status.HTTP_200_OK,
    summary="Get authoritative model selection record for an experiment (READ permission required)",
)
def get_experiment_selection(
    id: UUID,
    current_user: User = Depends(require_permission("READ")),
    db: Session = Depends(get_db),
):
    exp_repo = ExperimentRepository(db)
    experiment = exp_repo.get_by_id(id)
    if not experiment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Experiment not found"
        )

    task_type = experiment.task_type or "REGRESSION"
    sel_metric = experiment.selection_metric or ("rmse" if task_type == "REGRESSION" else "f1_macro")
    sel_dir = experiment.selection_direction or ("MINIMIZE" if sel_metric in ["rmse", "mae", "mse"] else "MAXIMIZE")

    return SelectionRecordResponse(
        experiment_id=experiment.id,
        project_id=experiment.project_id,
        selection_metric=sel_metric,
        selection_direction=sel_dir,
        selected_model_id=experiment.selected_model_id,
        locked_test_consumed=experiment.locked_test_consumed,
        locked_test_consumed_at=experiment.locked_test_consumed_at,
    )


@router.post(
    "/experiments/{id}/finalize",
    status_code=status.HTTP_200_OK,
    summary="Finalize experiment, refit winner on full Development partition, and run single Locked Test evaluation (TRAIN permission required)",
)
def finalize_experiment_endpoint(
    id: UUID,
    current_user: User = Depends(require_permission("TRAIN")),
    db: Session = Depends(get_db),
):
    service = ExperimentService(db)
    return service.finalize_experiment(id)


@router.post(
    "/experiments/{id}/diagnostic-rerun",
    status_code=status.HTTP_200_OK,
    summary="Run diagnostic test rerun for debugging only (TRAIN permission required). Labeled as TEST_REUSED_DIAGNOSTIC.",
)
def diagnostic_rerun_endpoint(
    id: UUID,
    current_user: User = Depends(require_permission("TRAIN")),
    db: Session = Depends(get_db),
):
    service = ExperimentService(db)
    return service.rerun_locked_test_diagnostic(id)


@router.get(
    "/projects/{id}/experiments",
    response_model=list[ExperimentResponse],
    status_code=status.HTTP_200_OK,
    summary="List all experiments for a project (READ permission required)",
)
def list_project_experiments(
    id: UUID,
    current_user: User = Depends(require_permission("READ")),
    db: Session = Depends(get_db),
):
    exp_repo = ExperimentRepository(db)
    experiments = exp_repo.get_by_project(id)

    response_list = []
    for exp in experiments:
        models_res = [
            TrainedModelResponse(
                id=m.id,
                experiment_id=m.experiment_id,
                algorithm_name=m.algorithm_name,
                hyperparameters=m.hyperparameters or {},
                quick_cv_score=float(m.quick_cv_score) if m.quick_cv_score is not None else None,
                fit_diagnosis=m.fit_diagnosis,
                model_selection_score=float(m.model_selection_score) if m.model_selection_score is not None else None,
                status=m.status,
                error_message=m.error_message,
                created_at=m.created_at,
                metrics=[
                    ModelMetricResponse(
                        id=metric.id,
                        model_id=metric.model_id,
                        metric_name=metric.metric_name,
                        split=metric.split,
                        metric_value=float(metric.metric_value) if metric.metric_value is not None else None,
                        metric_json=metric.metric_json,
                        fold_index=metric.fold_index,
                        created_at=metric.created_at,
                    )
                    for metric in m.metrics
                ],
            )
            for m in exp.trained_models
        ]
        response_list.append(
            ExperimentResponse(
                id=exp.id,
                project_id=exp.project_id,
                status=exp.status,
                task_type=exp.task_type,
                fold_count=exp.fold_count,
                cv_seed=exp.cv_seed,
                selection_metric=exp.selection_metric,
                selection_direction=exp.selection_direction,
                selected_model_id=exp.selected_model_id,
                locked_test_consumed=exp.locked_test_consumed,
                locked_test_consumed_at=exp.locked_test_consumed_at,
                created_at=exp.created_at,
                completed_at=exp.completed_at,
                trained_models=models_res,
            )
        )

    return response_list

