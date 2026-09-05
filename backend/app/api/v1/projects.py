from uuid import UUID
from fastapi import APIRouter, Depends, status, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.dependencies import require_permission
from app.models.user import User
from app.schemas.project import ProjectCreate, ProjectUpdate, ProjectResponse
from app.schemas.model_metric import LeaderboardResponse
from app.services.project_service import ProjectService

router = APIRouter(prefix="/projects", tags=["Projects"])


@router.post(
    "",
    response_model=ProjectResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new ML project"
)
def create_project(
    payload: ProjectCreate,
    current_user: User = Depends(require_permission("EDIT_DATA")),
    db: Session = Depends(get_db),
):
    service = ProjectService(db)
    return service.create_project(payload, current_user)

@router.get(
    "",
    response_model=list[ProjectResponse],
    status_code=status.HTTP_200_OK,
    summary="List user projects (or all projects if user has MANAGE_USERS permission)"
)
def list_projects(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    current_user: User = Depends(require_permission("READ")),
    db: Session = Depends(get_db),
):
    service = ProjectService(db)
    return service.list_projects(current_user, skip=skip, limit=limit)

@router.get(
    "/{id}",
    response_model=ProjectResponse,
    status_code=status.HTTP_200_OK,
    summary="Get project by ID"
)
def get_project(
    id: UUID,
    current_user: User = Depends(require_permission("READ")),
    db: Session = Depends(get_db),
):
    service = ProjectService(db)
    return service.get_project_by_id(id, current_user)

@router.put(
    "/{id}",
    response_model=ProjectResponse,
    status_code=status.HTTP_200_OK,
    summary="Update project details"
)
def update_project(
    id: UUID,
    payload: ProjectUpdate,
    current_user: User = Depends(require_permission("EDIT_DATA")),
    db: Session = Depends(get_db),
):
    service = ProjectService(db)
    return service.update_project(id, payload, current_user)

@router.delete(
    "/{id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a project"
)
def delete_project(
    id: UUID,
    current_user: User = Depends(require_permission("EDIT_DATA")),
    db: Session = Depends(get_db),
):
    service = ProjectService(db)
    service.delete_project(id, current_user)

@router.get(
    "/{id}/recommendations",
    response_model=list[dict],
    status_code=status.HTTP_200_OK,
    summary="List generated diagnostics recommendations for a project"
)
def get_project_recommendations(
    id: UUID,
    current_user: User = Depends(require_permission("READ")),
    db: Session = Depends(get_db),
):
    service = ProjectService(db)
    project = service.get_project_by_id(id, current_user)

    from app.models.recommendation import Recommendation
    recs = (
        db.query(Recommendation)
        .filter(Recommendation.project_id == project.id)
        .order_by(Recommendation.created_at.desc())
        .all()
    )
    return [
        {
            "id": str(r.id),
            "project_id": str(r.project_id),
            "finding": r.finding,
            "evidence": r.evidence,
            "recommended_action": r.recommended_action,
            "risk_note": r.risk_note,
            "confidence": r.confidence,
            "status": r.status,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in recs
    ]

@router.put(
    "/{id}/task-type",
    response_model=ProjectResponse,
    status_code=status.HTTP_200_OK,
    summary="Confirm or override task type for a project"
)
def update_project_task_type(
    id: UUID,
    payload: dict,
    current_user: User = Depends(require_permission("EDIT_DATA")),
    db: Session = Depends(get_db),
):
    service = ProjectService(db)
    project = service.get_project_by_id(id, current_user)

    chosen_task_type = payload.get("task_type")
    if chosen_task_type not in ["REGRESSION", "CLASSIFICATION"]:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="task_type must be either 'REGRESSION' or 'CLASSIFICATION'."
        )

    project_model = service.project_repo.get_by_id(project.id)
    project_model.task_type = chosen_task_type
    project_model.task_type_confidence = "MANUAL"
    db.add(project_model)
    db.commit()
    db.refresh(project_model)
    return ProjectResponse.model_validate(project_model)


@router.get(
    "/{id}/leaderboard",
    response_model=LeaderboardResponse,
    status_code=status.HTTP_200_OK,
    summary="Get leaderboard for project's latest experiment, sorted by primary selection metric (READ permission required)"
)
def get_project_leaderboard(
    id: UUID,
    experiment_id: UUID | None = Query(default=None),
    current_user: User = Depends(require_permission("READ")),
    db: Session = Depends(get_db),
):
    from fastapi import HTTPException
    from app.repositories.experiment_repository import ExperimentRepository
    from app.schemas.model_metric import LeaderboardResponse, LeaderboardEntryResponse, ModelMetricResponse

    service = ProjectService(db)
    project = service.get_project_by_id(id, current_user)
    exp_repo = ExperimentRepository(db)

    if experiment_id:
        experiment = exp_repo.get_with_models(experiment_id)
        if not experiment or experiment.project_id != project.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Experiment not found for this project"
            )
    else:
        experiments = exp_repo.get_by_project(project.id)
        if not experiments:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No experiments found for this project"
            )
        experiment = experiments[0]

    task_type = experiment.task_type or project.task_type or "REGRESSION"
    selection_metric = experiment.selection_metric or ("rmse" if task_type == "REGRESSION" else "f1_macro")
    selection_direction = experiment.selection_direction or ("MINIMIZE" if selection_metric in ["rmse", "mae", "mse"] else "MAXIMIZE")

    # Secondary metric (R2 for regression, ROC-AUC or accuracy for classification)
    secondary_metric_name = "r2" if task_type == "REGRESSION" else "roc_auc"

    models_entries = []
    for model in experiment.trained_models:
        # Find CV_MEAN primary metric
        primary_cv_metric = next(
            (m for m in model.metrics if m.split == "CV_MEAN" and m.metric_name.lower().replace("-", "_") == selection_metric.lower().replace("-", "_")),
            None
        )
        # Find CV_MEAN secondary metric
        secondary_cv_metric = next(
            (m for m in model.metrics if m.split == "CV_MEAN" and m.metric_name.lower().replace("-", "_") == secondary_metric_name.lower().replace("-", "_")),
            None
        )
        # Find LOCKED_TEST primary metric
        locked_test_metric = next(
            (m for m in model.metrics if m.split == "LOCKED_TEST" and m.metric_name.lower().replace("-", "_") == selection_metric.lower().replace("-", "_")),
            None
        )

        prim_val = float(primary_cv_metric.metric_value) if primary_cv_metric and primary_cv_metric.metric_value is not None else (
            float(model.quick_cv_score) if model.quick_cv_score is not None else None
        )
        sec_val = float(secondary_cv_metric.metric_value) if secondary_cv_metric and secondary_cv_metric.metric_value is not None else None
        lt_val = float(locked_test_metric.metric_value) if locked_test_metric and locked_test_metric.metric_value is not None else None

        is_winner = (experiment.selected_model_id == model.id)

        # Exclude TEST_REUSED_DIAGNOSTIC from authoritative leaderboard response per SRS §2.12
        metrics_list = [
            ModelMetricResponse(
                id=m.id,
                model_id=m.model_id,
                metric_name=m.metric_name,
                split=m.split,
                metric_value=float(m.metric_value) if m.metric_value is not None else None,
                metric_json=m.metric_json,
                fold_index=m.fold_index,
                created_at=m.created_at,
            )
            for m in model.metrics
            if m.split != "TEST_REUSED_DIAGNOSTIC"
        ]

        models_entries.append({
            "entry": LeaderboardEntryResponse(
                id=model.id,
                algorithm_name=model.algorithm_name,
                hyperparameters=model.hyperparameters or {},
                fit_diagnosis=model.fit_diagnosis,
                model_selection_score=float(model.model_selection_score) if model.model_selection_score is not None else None,
                primary_metric_name=selection_metric,
                primary_metric_value=prim_val,
                secondary_metric_name=secondary_metric_name,
                secondary_metric_value=sec_val,
                is_winner=is_winner,
                locked_test_score=lt_val,
                status=model.status,
                error_message=model.error_message,
                created_at=model.created_at,
                metrics=metrics_list,
            ),
            "primary_sort_key": prim_val,
            "status": model.status,
        })

    # Sort strictly by primary metric
    def sort_key(item):
        is_completed = item["status"] == "COMPLETED"
        score = item["primary_sort_key"]
        if not is_completed or score is None:
            return (1, 0)
        if selection_direction == "MINIMIZE":
            return (0, score)
        else:
            return (0, -score)

    sorted_models = [item["entry"] for item in sorted(models_entries, key=sort_key)]

    return LeaderboardResponse(
        project_id=project.id,
        experiment_id=experiment.id,
        task_type=task_type,
        selection_metric=selection_metric,
        selection_direction=selection_direction,
        selected_model_id=experiment.selected_model_id,
        locked_test_consumed=experiment.locked_test_consumed,
        locked_test_consumed_at=experiment.locked_test_consumed_at,
        models=sorted_models,
    )


@router.get(
    "/{id}/snapshot",
    status_code=status.HTTP_200_OK,
    summary="Get single project analytics snapshot with derived stage, winner summary, and deployment stats (READ permission required)"
)
def get_project_snapshot(
    id: UUID,
    current_user: User = Depends(require_permission("READ")),
    db: Session = Depends(get_db),
):
    from app.services.workspace_analytics_service import WorkspaceAnalyticsService
    analytics_service = WorkspaceAnalyticsService(db)
    return analytics_service.get_project_snapshot(id, current_user)



