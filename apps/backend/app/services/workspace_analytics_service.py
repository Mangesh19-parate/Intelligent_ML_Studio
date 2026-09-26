from uuid import UUID
from typing import Any
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.project import Project
from app.models.dataset import Dataset
from app.models.dataset_split import DatasetSplit
from app.models.profiling_report import ProfilingReport
from app.models.transformation_config import TransformationConfig
from app.models.experiment import Experiment
from app.models.trained_model import TrainedModel
from app.models.model_metric import ModelMetric
from app.models.deployment_gate import DeploymentGate
from app.models.deployment import Deployment
from app.models.user import User
from app.services.monitoring_service import MonitoringService


def derive_pipeline_stages_batch(project_ids: list[UUID | str], db: Session) -> dict[UUID, str]:
    """
    Derives pipeline stages for multiple projects in a single batched O(1) query round trip.
    Eliminates the N+1 query problem when loading project lists or workspace dashboards.
    
    State transition precedence (evaluated highest to lowest):
    1. DEPLOYED: A deployments row exists with status=LIVE
    2. GATE_PASSED: A deployment_gates row exists with gate_passed=True for a model in this project
    3. EVALUATED: LOCKED_TEST metrics exist for a model in this project (or locked_test_consumed=True)
    4. TRAINED: An experiment is COMPLETED, but no LOCKED_TEST metrics exist yet
    5. TRAINING: An experiment is currently RUNNING
    6. TRANSFORMED: Active transformation_configs exist, but no experiments
    7. PROFILED: A profiling_reports row exists, but no active transformation_configs
    8. SPLIT: A dataset_splits row exists, but no profiling_reports row
    9. DATA: No dataset uploaded OR dataset uploaded with no split
    """
    if not project_ids:
        return {}

    normalized_ids = [UUID(str(pid)) if not isinstance(pid, UUID) else pid for pid in project_ids]
    results: dict[UUID, str] = {pid: "DATA" for pid in normalized_ids}

    # 1. Fetch datasets grouped by project
    datasets = (
        db.query(Dataset.id, Dataset.project_id)
        .filter(Dataset.project_id.in_(normalized_ids))
        .all()
    )
    if not datasets:
        return results

    dataset_to_project: dict[UUID, UUID] = {d.id: d.project_id for d in datasets}
    all_dataset_ids = list(dataset_to_project.keys())

    # 2. Fetch splits grouped by dataset
    splits = (
        db.query(DatasetSplit.id, DatasetSplit.dataset_id)
        .filter(DatasetSplit.dataset_id.in_(all_dataset_ids))
        .all()
    )
    split_to_project: dict[UUID, UUID] = {s.id: dataset_to_project[s.dataset_id] for s in splits}
    all_split_ids = list(split_to_project.keys())

    # Update candidate stage: projects with splits reach at least SPLIT
    for pid in split_to_project.values():
        results[pid] = "SPLIT"

    # 3. Fetch profiling reports
    if all_split_ids:
        profiling_reports = (
            db.query(ProfilingReport.dataset_split_id)
            .filter(ProfilingReport.dataset_split_id.in_(all_split_ids))
            .all()
        )
        for pr in profiling_reports:
            pid = split_to_project.get(pr.dataset_split_id)
            if pid:
                results[pid] = "PROFILED"

    # 4. Fetch active transformation configs
    active_transforms = (
        db.query(TransformationConfig.project_id)
        .filter(
            TransformationConfig.project_id.in_(normalized_ids),
            TransformationConfig.is_active == True,
        )
        .all()
    )
    for at in active_transforms:
        results[at.project_id] = "TRANSFORMED"

    # 5. Fetch experiments
    experiments = (
        db.query(Experiment.id, Experiment.project_id, Experiment.status, Experiment.locked_test_consumed)
        .filter(Experiment.project_id.in_(normalized_ids))
        .all()
    )
    if not experiments:
        return results

    exp_to_project: dict[UUID, UUID] = {e.id: e.project_id for e in experiments}
    all_exp_ids = list(exp_to_project.keys())

    # Track training states per project
    completed_exps: set[UUID] = set()
    running_exps: set[UUID] = set()
    locked_consumed_projects: set[UUID] = set()

    for e in experiments:
        if e.locked_test_consumed:
            locked_consumed_projects.add(e.project_id)
        if e.status in ["COMPLETED", "REGISTERED", "EVALUATED", "TEST_CONSUMED"]:
            completed_exps.add(e.project_id)
        elif e.status in ["RUNNING", "TRAINING"]:
            running_exps.add(e.project_id)

    # 6. Fetch trained models
    trained_models = (
        db.query(TrainedModel.id, TrainedModel.experiment_id)
        .filter(TrainedModel.experiment_id.in_(all_exp_ids))
        .all()
    )
    model_to_project: dict[UUID, UUID] = {m.id: exp_to_project[m.experiment_id] for m in trained_models}
    all_model_ids = list(model_to_project.keys())

    deployed_projects: set[UUID] = set()
    gate_passed_projects: set[UUID] = set()
    evaluated_projects: set[UUID] = set(locked_consumed_projects)

    if all_model_ids:
        # Check LIVE Deployments
        live_deployments = (
            db.query(Deployment.model_id)
            .filter(
                Deployment.model_id.in_(all_model_ids),
                Deployment.status.in_(["LIVE", "DEPLOYED"]),
            )
            .all()
        )
        for dep in live_deployments:
            pid = model_to_project.get(dep.model_id)
            if pid:
                deployed_projects.add(pid)

        # Check Passed Deployment Gates
        passed_gates = (
            db.query(DeploymentGate.model_id)
            .filter(
                DeploymentGate.model_id.in_(all_model_ids),
                DeploymentGate.gate_passed == True,
            )
            .all()
        )
        for g in passed_gates:
            pid = model_to_project.get(g.model_id)
            if pid:
                gate_passed_projects.add(pid)

        # Check LOCKED_TEST metrics
        locked_metrics = (
            db.query(ModelMetric.model_id)
            .filter(
                ModelMetric.model_id.in_(all_model_ids),
                ModelMetric.split == "LOCKED_TEST",
            )
            .all()
        )
        for lm in locked_metrics:
            pid = model_to_project.get(lm.model_id)
            if pid:
                evaluated_projects.add(pid)

    # Final Stage Assignment following exact precedence order:
    for pid in normalized_ids:
        if pid in deployed_projects:
            results[pid] = "DEPLOYED"
        elif pid in gate_passed_projects:
            results[pid] = "GATE_PASSED"
        elif pid in evaluated_projects:
            results[pid] = "EVALUATED"
        elif pid in completed_exps:
            results[pid] = "TRAINED"
        elif pid in running_exps:
            results[pid] = "TRAINING"
        elif results[pid] not in ["TRANSFORMED", "PROFILED", "SPLIT", "DATA"]:
            results[pid] = "TRANSFORMED"

    return results


def derive_pipeline_stage(project_id: UUID | str, db: Session) -> str:
    """
    Derives the project's pipeline stage dynamically from live DB relational state.
    Delegates to batch resolution to ensure zero logic divergence.
    """
    proj_id = UUID(str(project_id)) if not isinstance(project_id, UUID) else project_id
    stages = derive_pipeline_stages_batch([proj_id], db)
    return stages.get(proj_id, "DATA")


class WorkspaceAnalyticsService:
    """
    Workspace Analytics Service (Day 11).
    
    ARCHITECTURAL NOTE:
    Powers workspace dashboards and project snapshot cards using live derived pipeline stages.
    - Scoped strictly by user role permissions (MANAGE_USERS / ADMIN sees platform-wide; others see self-owned).
    - Omits composite Model Selection Score headline per Day 7 specification.
    """

    def __init__(self, db: Session):
        self.db = db
        self.monitoring_service = MonitoringService(db)

    def _user_has_admin(self, user: User) -> bool:
        if not user:
            return False
        if getattr(user, "role", None):
            if getattr(user.role, "role_name", "") == "ADMIN":
                return True
            if getattr(user.role, "permissions", None):
                perm_keys = {p.permission_key for p in user.role.permissions}
                if "MANAGE_USERS" in perm_keys:
                    return True
        return False

    def get_summary(self, current_user: User) -> dict[str, Any]:
        """
        Aggregates workspace metrics scoped to the user's projects unless they hold MANAGE_USERS (ADMIN).
        """
        is_admin = self._user_has_admin(current_user)

        # 1. Projects scope
        if is_admin:
            projects = self.db.query(Project).all()
        else:
            projects = self.db.query(Project).filter(Project.owner_id == current_user.id).all()

        total_projects = len(projects)
        project_ids = [p.id for p in projects]

        # 2. Derive stages across projects
        stage_counts = {
            "DATA": 0,
            "SPLIT": 0,
            "PROFILED": 0,
            "TRANSFORMED": 0,
            "TRAINING": 0,
            "TRAINED": 0,
            "EVALUATED": 0,
            "GATE_PASSED": 0,
            "DEPLOYED": 0,
        }
        for proj in projects:
            stage = derive_pipeline_stage(proj.id, self.db)
            if stage in stage_counts:
                stage_counts[stage] += 1
            else:
                stage_counts[stage] = 1

        if not project_ids:
            return {
                "total_projects": 0,
                "projects_by_stage": stage_counts,
                "datasets_uploaded": 0,
                "experiments_completed": 0,
                "models_trained": 0,
                "models_gate_passed": 0,
                "live_deployments": 0,
                "is_platform_wide": is_admin,
            }

        # 3. Datasets uploaded count
        datasets_count = (
            self.db.query(func.count(Dataset.id))
            .filter(Dataset.project_id.in_(project_ids))
            .scalar() or 0
        )

        # 4. Experiments completed count
        experiments_completed_count = (
            self.db.query(func.count(Experiment.id))
            .filter(
                Experiment.project_id.in_(project_ids),
                Experiment.status.in_(["COMPLETED", "REGISTERED", "EVALUATED", "TEST_CONSUMED"])
            )
            .scalar() or 0
        )

        # 5. Models trained count
        models_trained_count = (
            self.db.query(func.count(TrainedModel.id))
            .join(Experiment, TrainedModel.experiment_id == Experiment.id)
            .filter(
                Experiment.project_id.in_(project_ids),
                TrainedModel.status.in_(["COMPLETED", "TRAINED", "ARTIFACT_VERIFIED", "DEPLOYABLE"])
            )
            .scalar() or 0
        )

        # 6. Models with passed deployment gate count
        models_gate_passed_count = (
            self.db.query(func.count(func.distinct(DeploymentGate.model_id)))
            .join(TrainedModel, DeploymentGate.model_id == TrainedModel.id)
            .join(Experiment, TrainedModel.experiment_id == Experiment.id)
            .filter(
                Experiment.project_id.in_(project_ids),
                DeploymentGate.gate_passed == True
            )
            .scalar() or 0
        )

        # 7. Currently LIVE / DEPLOYED deployments count
        live_deployments_count = (
            self.db.query(func.count(Deployment.id))
            .join(TrainedModel, Deployment.model_id == TrainedModel.id)
            .join(Experiment, TrainedModel.experiment_id == Experiment.id)
            .filter(
                Experiment.project_id.in_(project_ids),
                Deployment.status.in_(["LIVE", "DEPLOYED"])
            )
            .scalar() or 0
        )

        return {
            "total_projects": total_projects,
            "projects_by_stage": stage_counts,
            "datasets_uploaded": datasets_count,
            "experiments_completed": experiments_completed_count,
            "models_trained": models_trained_count,
            "models_gate_passed": models_gate_passed_count,
            "live_deployments": live_deployments_count,
            "is_platform_wide": is_admin,
        }

    def get_project_snapshot(self, project_id: UUID | str, current_user: User) -> dict[str, Any]:
        """
        Returns a single-project analytics snapshot including derived pipeline stage,
        latest leaderboard-winner summary (primary metric, not composite score),
        and deployment monitoring stats if deployed.
        """
        proj_id = UUID(str(project_id)) if not isinstance(project_id, UUID) else project_id
        project = self.db.query(Project).filter(Project.id == proj_id).first()
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found"
            )

        is_admin = self._user_has_admin(current_user)
        if not is_admin and project.owner_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have access to this project"
            )

        derived_stage = derive_pipeline_stage(proj_id, self.db)

        # Latest experiment & leaderboard winner summary
        latest_experiment = (
            self.db.query(Experiment)
            .filter(Experiment.project_id == proj_id)
            .order_by(Experiment.created_at.desc())
            .first()
        )

        winner_summary = None
        if latest_experiment:
            selected_model = None
            if latest_experiment.selected_model_id:
                selected_model = (
                    self.db.query(TrainedModel)
                    .filter(TrainedModel.id == latest_experiment.selected_model_id)
                    .first()
                )
            elif latest_experiment.trained_models:
                # Fallback to first completed model if not finalized
                selected_model = next((m for m in latest_experiment.trained_models if m.status == "COMPLETED"), None)

            if selected_model:
                sel_metric = latest_experiment.selection_metric or (
                    "rmse" if (latest_experiment.task_type or project.task_type) == "REGRESSION" else "f1_macro"
                )
                
                # Fetch CV_MEAN primary metric
                primary_metric = next(
                    (m for m in selected_model.metrics if m.split == "CV_MEAN" and m.metric_name.lower().replace("-", "_") == sel_metric.lower().replace("-", "_")),
                    None
                )
                locked_metric = next(
                    (m for m in selected_model.metrics if m.split == "LOCKED_TEST" and m.metric_name.lower().replace("-", "_") == sel_metric.lower().replace("-", "_")),
                    None
                )

                winner_summary = {
                    "experiment_id": str(latest_experiment.id),
                    "model_id": str(selected_model.id),
                    "algorithm_name": selected_model.algorithm_name,
                    "fit_diagnosis": selected_model.fit_diagnosis,
                    "selection_metric": sel_metric,
                    "primary_cv_score": float(primary_metric.metric_value) if primary_metric and primary_metric.metric_value is not None else (
                        float(selected_model.quick_cv_score) if selected_model.quick_cv_score is not None else None
                    ),
                    "locked_test_score": float(locked_metric.metric_value) if locked_metric and locked_metric.metric_value is not None else None,
                    "is_winner": bool(latest_experiment.selected_model_id == selected_model.id),
                }

        # Check for active or latest deployment
        all_models = (
            self.db.query(TrainedModel)
            .join(Experiment, TrainedModel.experiment_id == Experiment.id)
            .filter(Experiment.project_id == proj_id)
            .all()
        )
        model_ids = [m.id for m in all_models]

        deployment_summary = None
        if model_ids:
            # Find LIVE / DEPLOYED deployment first, else latest deployment
            deployment = (
                self.db.query(Deployment)
                .filter(Deployment.model_id.in_(model_ids), Deployment.status.in_(["LIVE", "DEPLOYED"]))
                .first()
            )
            if not deployment:
                deployment = (
                    self.db.query(Deployment)
                    .filter(Deployment.model_id.in_(model_ids))
                    .order_by(Deployment.deployed_at.desc())
                    .first()
                )

            if deployment:
                latency_stats = self.monitoring_service.latency_summary(deployment.id)
                error_stats = self.monitoring_service.error_rate(deployment.id)
                deployment_summary = {
                    "deployment_id": str(deployment.id),
                    "model_id": str(deployment.model_id),
                    "status": deployment.status,
                    "endpoint_path": deployment.endpoint_path,
                    "deployed_at": deployment.deployed_at.isoformat() if deployment.deployed_at else None,
                    "latency_summary": latency_stats,
                    "error_rate": error_stats,
                }

        return {
            "project_id": str(project.id),
            "project_name": project.project_name,
            "task_type": project.task_type,
            "target_column": project.target_column,
            "derived_pipeline_stage": derived_stage,
            "data_quality_index": float(project.data_quality_index) if project.data_quality_index is not None else None,
            "created_at": project.created_at.isoformat() if project.created_at else None,
            "winner_summary": winner_summary,
            "deployment": deployment_summary,
        }
