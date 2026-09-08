import logging
import secrets
import hashlib
import joblib
from pathlib import Path
from datetime import datetime, timezone
from uuid import UUID
from typing import Any
import numpy as np
import pandas as pd
from fastapi import HTTPException, status
from sqlalchemy import update
from sqlalchemy.orm import Session
from sklearn.model_selection import KFold, StratifiedKFold
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.linear_model import LinearRegression, LogisticRegression

from app.core.config import settings
from app.core.database import SessionLocal
from app.config.contract import REPRODUCIBILITY_TOLERANCE
from app.config.state_machines import (
    ExperimentState,
    ModelState,
    can_transition,
    validate_transition,
    InvalidStateTransitionError,
)
from app.models.project import Project
from app.models.dataset_split import DatasetSplit
from app.models.transformation_config import TransformationConfig
from app.models.transformation_snapshot import TransformationSnapshot
from app.models.feature_selection_snapshot import FeatureSelectionSnapshot
from app.models.experiment import Experiment
from app.models.trained_model import TrainedModel
from app.models.model_metric import ModelMetric
from app.repositories.project_repository import ProjectRepository
from app.repositories.dataset_repository import DatasetRepository
from app.repositories.experiment_repository import ExperimentRepository
from app.services.dataset_split_service import DatasetSplitService
from app.services.transformation_service import TransformationService
from app.services.feature_selection_service import FeatureSelectionService
from app.services.evaluation_service import EvaluationService
from app.services.environment_capture_service import EnvironmentCaptureService
from app.services.storage_service import StorageService, get_storage_service
from app.services.trainers import (
    RegressionTrainer,
    ClassificationTrainer,
    FeatureSelector,
)

logger = logging.getLogger(__name__)

# Scavenger registry tracking orphaned artifacts where immediate deletion failed (Day 3 P0)
ORPHANED_RECOVERABLE_REGISTRY: set[str] = set()

def get_orphaned_recoverable_registry() -> set[str]:
    """Returns the set of artifact file paths marked as ORPHANED_RECOVERABLE."""
    return ORPHANED_RECOVERABLE_REGISTRY

def clear_orphaned_recoverable_registry() -> None:
    """Clears the in-memory scavenger registry (useful in test teardown)."""
    ORPHANED_RECOVERABLE_REGISTRY.clear()

class ExperimentService:
    """
    Service responsible for coordinating Leakage-Safe Model Training Experiments,
    Multi-Metric Evaluation, Authoritative Model Selection, and Guarded Locked Test Evaluation (SRS §2.8-§2.12).
    
    ARCHITECTURAL INVARIANTS:
    1. Zero Test Leakage (Invariants 1, 2, 6): CV runs EXCLUSIVELY on the Development partition.
    2. Shared Selection Per Fold: Preprocessing transformer and rank-aggregation feature selection
       fit once per fold on fold-train slice only.
    3. Multi-Metric Evaluation: Stores full TRAIN, VALIDATION, and CV_MEAN metrics per algorithm.
    4. Primary-Metric Driven Leaderboard: Sorting strictly by selection_metric / selection_direction.
    5. Single Locked Test Evaluation: Exactly one evaluation for the winning model, permanently consumed.
    6. Fault Isolation: Single fold failure fails that algorithm entirely; surviving algorithms complete.
    7. Concurrency Protection (SRS v9 §6): At most one active TRAINING job per experiment; concurrent attempts rejected immediately.
    """

    VALID_REGRESSION_ALGORITHMS = {
        "LinearRegression", "Linear Regression",
        "Ridge", "Ridge Regression",
        "RandomForestRegressor", "Random Forest", "Random Forest Regressor"
    }

    VALID_CLASSIFICATION_ALGORITHMS = {
        "LogisticRegression", "Logistic Regression",
        "RandomForestClassifier", "Random Forest", "Random Forest Classifier",
        "GradientBoostingClassifier", "Gradient Boosting", "Gradient Boosting Classifier"
    }

    def __init__(self, db: Session, storage: StorageService | None = None):
        self.db = db
        self.storage = storage or get_storage_service()
        self.project_repo = ProjectRepository(db)
        self.dataset_repo = DatasetRepository(db)
        self.exp_repo = ExperimentRepository(db)
        self.split_service = DatasetSplitService(db, self.storage)
        self.trans_service = TransformationService(db, self.storage)
        self.fs_service = FeatureSelectionService(db, self.storage)

    def start_training(self, experiment_id: UUID | str) -> Experiment:
        """
        Atomically transitions an experiment into TRAINING state with DB-level concurrency protection (SRS v9 §6).
        Ensures at most one active TRAINING job per experiment.
        Rejects concurrent start attempts immediately with HTTP 409 Conflict (not queued or silently allowed).
        """
        exp_uuid = UUID(str(experiment_id)) if not isinstance(experiment_id, UUID) else experiment_id

        # Atomic conditional update at DB level
        try:
            stmt = (
                update(Experiment)
                .where(
                    Experiment.id == exp_uuid,
                    Experiment.status.not_in([ExperimentState.TRAINING.value, "TRAINING", "RUNNING"])
                )
                .values(status=ExperimentState.TRAINING.value)
            )
            result = self.db.execute(stmt)
            self.db.commit()
            rowcount = result.rowcount
        except Exception as e:
            self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Experiment {exp_uuid} is already actively training. Concurrent training execution rejected."
            )

        if rowcount == 0:
            # Check if experiment exists or if it failed condition because it's actively training
            try:
                exp_check = self.exp_repo.get_by_id(exp_uuid)
                if not exp_check:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"Experiment {exp_uuid} not found."
                    )
            except HTTPException:
                raise
            except Exception:
                pass
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Experiment {exp_uuid} is already actively training. Concurrent training execution rejected."
            )

        try:
            exp = self.exp_repo.get_by_id(exp_uuid)
        except Exception:
            self.db.rollback()
            exp = self.exp_repo.get_by_id(exp_uuid)
        return exp

    def freeze_experiment_config(
        self,
        experiment_id: UUID | str,
        config_override: dict[str, Any] | None = None,
    ) -> Experiment:
        """
        Freezes the experiment configuration (ExperimentState.CREATED -> ExperimentState.CONFIGURED).
        Ensures immutability of the experiment specification.
        Strictly rejects any subsequent re-freeze attempts with HTTP 409 Conflict.
        """
        exp_uuid = UUID(str(experiment_id)) if not isinstance(experiment_id, UUID) else experiment_id
        experiment = self.exp_repo.get_by_id(exp_uuid)
        if not experiment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Experiment {exp_uuid} not found."
            )

        # Strict rejection if already configured or in any subsequent lifecycle state
        if experiment.status in [
            ExperimentState.CONFIGURED.value,
            "CONFIGURED",
            ExperimentState.TRAINING.value,
            "TRAINING",
            "RUNNING",
            ExperimentState.EVALUATED.value,
            "EVALUATED",
            ExperimentState.TEST_CONSUMED.value,
            "TEST_CONSUMED",
            ExperimentState.REGISTERED.value,
            "REGISTERED",
            "COMPLETED",
        ] or (experiment.experiment_config is not None and experiment.status != ExperimentState.TRAINING_FAILED.value):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Experiment {exp_uuid} configuration is already frozen. Re-freezing is rejected."
            )

        project = self.project_repo.get_by_id(experiment.project_id)
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Associated project not found."
            )

        override = config_override or {}
        task_type = override.get("task_type") or experiment.task_type or project.task_type or "REGRESSION"
        target_col = override.get("target") or project.target_column
        folds = override.get("folds") or experiment.fold_count or 5
        cv_seed = override.get("seed") or experiment.cv_seed or secrets.randbelow(1_000_000)

        # Capture transformation snapshot if not already present
        trans_configs = self.db.query(TransformationConfig).filter(
            TransformationConfig.project_id == project.id
        ).order_by(TransformationConfig.column_name.asc()).all()
        frozen_trans_json = [
            {
                "id": str(tc.id),
                "column_name": tc.column_name,
                "missing_value_strategy": tc.missing_value_strategy,
                "encoding_strategy": tc.encoding_strategy,
                "scaling_strategy": tc.scaling_strategy,
                "outlier_strategy": tc.outlier_strategy,
                "is_active": tc.is_active,
            }
            for tc in trans_configs
        ]

        trans_snapshot = self.exp_repo.create_transformation_snapshot(
            experiment_id=experiment.id,
            config_json=frozen_trans_json,
        )

        cv_strategy = "STRATIFIED_KFOLD" if task_type == "CLASSIFICATION" else "KFOLD"

        split_seed = 42
        datasets = self.dataset_repo.get_by_project(project.id)
        if datasets:
            dev_split = self.db.query(DatasetSplit).filter(
                DatasetSplit.dataset_id == datasets[0].id,
                DatasetSplit.split_type == "DEVELOPMENT"
            ).first()
            if dev_split:
                split_seed = dev_split.split_seed

        eff_metric = override.get("selection_metric") or experiment.selection_metric or ("rmse" if task_type == "REGRESSION" else "f1_macro")
        eff_dir = override.get("selection_direction") or experiment.selection_direction or ("MINIMIZE" if eff_metric in ["rmse", "mae", "mse"] else "MAXIMIZE")

        dep_thresh_override = override.get("deployment_threshold")
        dep_metric = eff_metric
        dep_min_val = None
        if dep_thresh_override and isinstance(dep_thresh_override, dict):
            dep_metric = dep_thresh_override.get("metric", eff_metric)
            dep_min_val = dep_thresh_override.get("min_value")

        algs = override.get("algorithms")
        if algs:
            algs = self.validate_algorithms(task_type, algs)

        experiment_config_payload = {
            "task_type": task_type,
            "target": target_col,
            "algorithms": algs,
            "split": {
                "seed": split_seed,
                "locked_test_pct": 20,
            },
            "cv": {
                "strategy": cv_strategy,
                "folds": folds,
                "seed": cv_seed,
            },
            "preprocessing": {
                "snapshot_id": str(trans_snapshot.id),
            },
            "feature_selection": {
                "method": "rank_aggregation_ensemble",
            },
            "threshold_selection": {
                "objective": "F1",
                "search_range": [0.10, 0.90],
                "resolution": 0.01,
                "tie_break": "closest_to_0.5",
            },
            "deployment_threshold": {
                "metric": dep_metric,
                "min_value": dep_min_val,
            },
        }

        experiment.experiment_config = experiment_config_payload
        experiment.deployment_threshold_frozen_at_creation = True
        experiment.status = ExperimentState.CONFIGURED.value
        if override.get("selection_metric"):
            experiment.selection_metric = eff_metric
        if override.get("selection_direction"):
            experiment.selection_direction = eff_dir
        if override.get("folds"):
            experiment.fold_count = folds
        if override.get("seed"):
            experiment.cv_seed = cv_seed

        self.db.add(experiment)
        self.db.commit()
        self.db.refresh(experiment)
        return experiment

    @staticmethod
    def normalize_selection_metric(
        metric_name: str | None,
        task_type: str,
        direction: str | None = None
    ) -> tuple[str, str]:
        """
        Normalizes selection metric and derives default direction:
        Regression default: rmse (MINIMIZE)
        Classification default: f1_macro (MAXIMIZE)
        """
        if not metric_name:
            if task_type == "REGRESSION":
                return "rmse", "MINIMIZE"
            else:
                return "f1_macro", "MAXIMIZE"

        cleaned = metric_name.lower().replace("-", "_").strip()
        if cleaned in ["macro_f1", "macro-f1", "f1_macro", "f1"]:
            canonical_metric = "f1_macro"
        elif cleaned in ["weighted_f1", "weighted-f1", "f1_weighted"]:
            canonical_metric = "f1_weighted"
        elif cleaned in ["r_2", "r2", "r_squared"]:
            canonical_metric = "r2"
        elif cleaned in ["adjusted_r2", "adj_r2", "adj_r_squared"]:
            canonical_metric = "adjusted_r2"
        elif cleaned in ["roc_auc", "roc-auc", "auc"]:
            canonical_metric = "roc_auc"
        else:
            canonical_metric = cleaned

        if direction:
            canonical_direction = direction.upper().strip()
            if canonical_direction not in ["MAXIMIZE", "MINIMIZE"]:
                canonical_direction = "MINIMIZE" if canonical_metric in ["rmse", "mae", "mse", "log_loss"] else "MAXIMIZE"
        else:
            if canonical_metric in ["rmse", "mae", "mse", "log_loss"]:
                canonical_direction = "MINIMIZE"
            else:
                canonical_direction = "MAXIMIZE"

        return canonical_metric, canonical_direction

    def validate_algorithms(self, task_type: str, algorithms: list[str]) -> list[str]:
        """
        Validates that all requested algorithms belong to the fixed algorithm set
        for the given project task type. Normalizes them to canonical names.
        Raises HTTP 422 on any unknown or mismatched algorithm.
        """
        if not algorithms:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="At least one algorithm must be specified for training."
            )

        canonical_algorithms: list[str] = []
        for alg in algorithms:
            if task_type == "REGRESSION":
                if not RegressionTrainer.is_supported(alg):
                    raise HTTPException(
                        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                        detail=(
                            f"Invalid algorithm '{alg}' for task type {task_type}. "
                            f"Allowed algorithms: {', '.join(RegressionTrainer.get_supported_algorithms())}"
                        )
                    )
                canonical_name = RegressionTrainer.to_canonical_name(alg)
            elif task_type == "CLASSIFICATION":
                if not ClassificationTrainer.is_supported(alg):
                    raise HTTPException(
                        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                        detail=(
                            f"Invalid algorithm '{alg}' for task type {task_type}. "
                            f"Allowed algorithms: {', '.join(ClassificationTrainer.get_supported_algorithms())}"
                        )
                    )
                canonical_name = ClassificationTrainer.to_canonical_name(alg)
            else:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Unsupported project task_type '{task_type}' for model training."
                )

            if canonical_name not in canonical_algorithms:
                canonical_algorithms.append(canonical_name)

        return canonical_algorithms

    def prepare_experiment_cv_context(
        self,
        experiment_id: UUID | str,
    ) -> dict[str, Any]:
        """
        Builds the foundational execution skeleton for an experiment (SRS v9 §2 / Day 3):
        1. Loads frozen experiment_config (or auto-freezes if CREATED).
        2. Loads Development partition strictly by row_uid (Zero Test Leakage Invariant).
        3. Constructs deterministic CV splits (KFold / StratifiedKFold) and validates zero leakage.

        Returns a structured dictionary with:
        - experiment: Experiment instance
        - project: Project instance
        - dataset: Dataset instance
        - experiment_config: dict
        - dev_df: pd.DataFrame (Development partition only)
        - X_df: pd.DataFrame (features only, without target or row_uid)
        - y_raw: pd.Series / np.ndarray
        - candidate_cols: list[str]
        - cv_strategy: str ("STRATIFIED_KFOLD" or "KFOLD")
        - fold_count: int
        - cv_seed: int
        - splitter: BaseCrossValidator (KFold or StratifiedKFold)
        - fold_splits: list of dicts with fold_idx, train_indices, val_indices, train_size, val_size, train_row_uids, val_row_uids
        """
        exp_uuid = UUID(str(experiment_id)) if not isinstance(experiment_id, UUID) else experiment_id
        experiment = self.exp_repo.get_by_id(exp_uuid)
        if not experiment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Experiment {exp_uuid} not found."
            )

        # 1. Load or freeze config
        if not experiment.experiment_config:
            experiment = self.freeze_experiment_config(experiment.id)

        config = experiment.experiment_config or {}
        task_type = config.get("task_type") or experiment.task_type or "REGRESSION"
        target_col = config.get("target")

        project = self.project_repo.get_by_id(experiment.project_id)
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Associated project not found."
            )

        if not target_col:
            target_col = project.target_column
        if not target_col:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Project has no target column configured. Please select a target column first."
            )

        # 2. Retrieve latest dataset
        datasets = self.dataset_repo.get_by_project(project.id)
        if not datasets:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No dataset found for this project."
            )
        latest_dataset = datasets[0]

        # 3. Load Development data ONLY by row_uid (Zero Test Leakage Invariant)
        dev_df = self.split_service.get_development_data(latest_dataset.id)
        if target_col not in dev_df.columns:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Target column '{target_col}' not found in Development data."
            )

        y_raw = dev_df[target_col]
        drop_cols = [c for c in [target_col, "row_uid"] if c in dev_df.columns]
        X_df = dev_df.drop(columns=drop_cols)
        candidate_cols = list(X_df.columns)

        # Extract CV parameters from frozen config
        cv_conf = config.get("cv", {})
        folds = cv_conf.get("folds") or experiment.fold_count or 5
        cv_seed = cv_conf.get("seed") or experiment.cv_seed or 42

        n_samples = len(dev_df)
        if n_samples < folds:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Insufficient samples ({n_samples}) for {folds}-fold cross-validation."
            )

        # 4. Construct CV Splitter
        if task_type == "CLASSIFICATION":
            class_counts = y_raw.value_counts()
            if (class_counts < folds).any():
                splitter = KFold(n_splits=folds, shuffle=True, random_state=cv_seed)
                cv_strategy = "KFOLD"
            else:
                splitter = StratifiedKFold(n_splits=folds, shuffle=True, random_state=cv_seed)
                cv_strategy = "STRATIFIED_KFOLD"
        else:
            splitter = KFold(n_splits=folds, shuffle=True, random_state=cv_seed)
            cv_strategy = "KFOLD"

        # Generate and verify fold splits
        fold_splits = []
        has_row_uids = "row_uid" in dev_df.columns
        for fold_idx, (train_idx, val_idx) in enumerate(splitter.split(X_df, y_raw)):
            train_set = set(train_idx)
            val_set = set(val_idx)
            overlap = train_set.intersection(val_set)
            if len(overlap) > 0:
                raise RuntimeError(
                    f"Data leakage detected in fold {fold_idx}: overlap indices {overlap}"
                )

            train_uids = dev_df["row_uid"].iloc[train_idx].tolist() if has_row_uids else None
            val_uids = dev_df["row_uid"].iloc[val_idx].tolist() if has_row_uids else None

            fold_splits.append({
                "fold_index": fold_idx,
                "train_indices": train_idx,
                "val_indices": val_idx,
                "train_size": len(train_idx),
                "val_size": len(val_idx),
                "train_row_uids": train_uids,
                "val_row_uids": val_uids,
            })

        return {
            "experiment": experiment,
            "project": project,
            "dataset": latest_dataset,
            "experiment_config": config,
            "dev_df": dev_df,
            "X_df": X_df,
            "y_raw": y_raw,
            "candidate_cols": candidate_cols,
            "cv_strategy": cv_strategy,
            "fold_count": folds,
            "cv_seed": cv_seed,
            "splitter": splitter,
            "fold_splits": fold_splits,
        }

    def build_fold_pipeline(
        self,
        project_id: UUID | str,
        task_type: str = "REGRESSION",
        selected_features: list[str] | list[int] | None = None,
        estimator: Any | None = None,
    ) -> Pipeline:
        """
        Constructs a unified, unfit scikit-learn Pipeline for a cross-validation fold (SRS v9 §2 / Day 4).
        
        Pipeline structure:
        1. 'transformer': Unfit ColumnTransformer generated from project active transformation configs.
        2. 'selector': FeatureSelector transformer step.
        3. 'estimator': Target estimator or placeholder model.
        """
        transformer = self.trans_service.build_pipeline(project_id)
        selector = FeatureSelector(selected_features=selected_features)

        if estimator is None:
            if task_type == "CLASSIFICATION":
                estimator = LogisticRegression(max_iter=1000)
            else:
                estimator = LinearRegression()

        return Pipeline(
            steps=[
                ("transformer", transformer),
                ("selector", selector),
                ("estimator", estimator),
            ]
        )

    def run_experiment_fold_pipelines(
        self,
        experiment_id: UUID | str,
        estimator: Any | None = None,
    ) -> dict[str, Any]:
        """
        Executes per-fold pipeline construction, independent fitting, and validation evaluation (Day 4).
        Ensures that transformer and selector instances are fit strictly per fold without cross-fold leakage.
        """
        ctx = self.prepare_experiment_cv_context(experiment_id)
        project_id = ctx["project"].id
        task_type = ctx["experiment_config"].get("task_type", "REGRESSION")
        X_df = ctx["X_df"]
        y_raw = ctx["y_raw"]

        fold_results = []
        for fold in ctx["fold_splits"]:
            f_idx = fold["fold_index"]
            train_idx = fold["train_indices"]
            val_idx = fold["val_indices"]

            X_train = X_df.iloc[train_idx].copy()
            y_train = y_raw.iloc[train_idx].values
            X_val = X_df.iloc[val_idx].copy()
            y_val = y_raw.iloc[val_idx].values

            # Construct fresh fold pipeline instance
            fold_pipe = self.build_fold_pipeline(
                project_id=project_id,
                task_type=task_type,
                estimator=estimator,
            )

            # Format targets if needed
            if task_type == "CLASSIFICATION":
                if pd.api.types.is_numeric_dtype(y_train) and not np.isnan(y_train).any():
                    y_fit = y_train.astype(int)
                    y_val_eval = y_val.astype(int)
                else:
                    y_fit = pd.Series(y_train).astype(str).values
                    y_val_eval = pd.Series(y_val).astype(str).values
            else:
                y_fit = y_train.astype(float)
                y_val_eval = y_val.astype(float)

            # Fit full pipeline exclusively on fold training partition
            fold_pipe.fit(X_train, y_fit)

            # Predict on fold validation partition
            y_val_pred = fold_pipe.predict(X_val)

            fold_results.append({
                "fold_index": f_idx,
                "pipeline": fold_pipe,
                "train_size": len(train_idx),
                "val_size": len(val_idx),
                "y_val_true": y_val_eval,
                "y_val_pred": y_val_pred,
            })

        return {
            "experiment_id": ctx["experiment"].id,
            "project_id": project_id,
            "task_type": task_type,
            "cv_strategy": ctx["cv_strategy"],
            "fold_count": ctx["fold_count"],
            "fold_results": fold_results,
        }

    def run_experiment(
        self,
        project_id: UUID | str | None = None,
        algorithms: list[str] | None = None,
        folds: int = 5,
        seed: int | None = None,
        threshold: float = 0.0,
        selection_metric: str | None = None,
        selection_direction: str | None = None,
        experiment_id: UUID | str | None = None,
        auto_finalize: bool = True,
        deployment_threshold: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Executes the cross-validation training experiment across requested algorithms.
        Computes full multi-metric evaluations, fit diagnostics, composite scores, and
        optionally executes authoritative finalization & Locked Test evaluation.
        """
        experiment = None
        if experiment_id is not None:
            experiment = self.exp_repo.get_by_id(experiment_id)
            if experiment and project_id is None:
                project_id = experiment.project_id

        if not project_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found"
            )

        project = self.project_repo.get_by_id(project_id)
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found"
            )

        if not project.target_column:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Project has no target column configured. Please select a target column first."
            )

        task_type = project.task_type
        if task_type not in ["REGRESSION", "CLASSIFICATION"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Project task type must be 'REGRESSION' or 'CLASSIFICATION' before training."
            )

        # If experiment already has frozen config, load defaults from it
        if experiment and experiment.experiment_config:
            cfg = experiment.experiment_config
            if not algorithms:
                algorithms = cfg.get("algorithms", algorithms)
            task_type = cfg.get("task_type", task_type)
            folds = cfg.get("cv", {}).get("folds", folds)
            if seed is None:
                seed = cfg.get("cv", {}).get("seed", seed)
            if selection_metric is None:
                selection_metric = cfg.get("selection_metric", selection_metric)
            if selection_direction is None:
                selection_direction = cfg.get("selection_direction", selection_direction)

        if not algorithms:
            if task_type == "REGRESSION":
                algorithms = ["LinearRegression", "Ridge", "RandomForestRegressor"]
            else:
                algorithms = ["LogisticRegression", "RandomForestClassifier", "GradientBoostingClassifier"]

        # 1. Validate requested algorithms against project task type
        canonical_algs = self.validate_algorithms(task_type, algorithms)

        # Determine selection metric & direction
        eff_metric, eff_direction = self.normalize_selection_metric(selection_metric, task_type, selection_direction)

        # Generate seed if not provided
        cv_seed = seed if seed is not None else secrets.randbelow(1_000_000)

        # 2. Validate dataset existence and fetch metadata
        datasets = self.dataset_repo.get_by_project(project.id)
        if not datasets:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No dataset found for this project."
            )
        latest_dataset = datasets[0]
        dataset_content_hash = latest_dataset.content_hash

        # Capture current environment & library versions (Day 8 Lineage)
        env_info = EnvironmentCaptureService.capture_current_environment()

        # Split metadata
        dev_split = self.db.query(DatasetSplit).filter(
            DatasetSplit.dataset_id == latest_dataset.id,
            DatasetSplit.split_type == "DEVELOPMENT"
        ).first()
        split_seed = dev_split.split_seed if dev_split else 42

        # 3. Retrieve or create Experiment record
        if experiment_id is not None:
            if not experiment:
                experiment = self.exp_repo.create_experiment(
                    project_id=project.id,
                    task_type=task_type,
                    fold_count=folds,
                    cv_seed=cv_seed,
                    selection_metric=eff_metric,
                    selection_direction=eff_direction,
                    status=ExperimentState.CREATED.value,
                    dataset_content_hash=dataset_content_hash,
                    code_version=env_info.get("code_version"),
                    python_version=env_info.get("python_version"),
                    sklearn_version=env_info.get("sklearn_version"),
                    numpy_version=env_info.get("numpy_version"),
                    pandas_version=env_info.get("pandas_version"),
                    model_library_versions=env_info.get("model_library_versions"),
                    environment_capture_method="CAPTURED_LIVE",
                )
                self.start_training(experiment.id)
            else:
                experiment.task_type = task_type
                experiment.fold_count = folds
                experiment.cv_seed = cv_seed
                experiment.selection_metric = eff_metric
                experiment.selection_direction = eff_direction
                experiment.dataset_content_hash = dataset_content_hash
                experiment.code_version = env_info.get("code_version")
                experiment.python_version = env_info.get("python_version")
                experiment.sklearn_version = env_info.get("sklearn_version")
                experiment.numpy_version = env_info.get("numpy_version")
                experiment.pandas_version = env_info.get("pandas_version")
                experiment.model_library_versions = env_info.get("model_library_versions")
                experiment.environment_capture_method = "CAPTURED_LIVE"
                self.db.add(experiment)
                self.db.commit()
                self.start_training(experiment.id)
        else:
            experiment = self.exp_repo.create_experiment(
                project_id=project.id,
                task_type=task_type,
                fold_count=folds,
                cv_seed=cv_seed,
                selection_metric=eff_metric,
                selection_direction=eff_direction,
                status=ExperimentState.CREATED.value,
                dataset_content_hash=dataset_content_hash,
                code_version=env_info.get("code_version"),
                python_version=env_info.get("python_version"),
                sklearn_version=env_info.get("sklearn_version"),
                numpy_version=env_info.get("numpy_version"),
                pandas_version=env_info.get("pandas_version"),
                model_library_versions=env_info.get("model_library_versions"),
                environment_capture_method="CAPTURED_LIVE",
            )
            self.start_training(experiment.id)

        # 4. Assemble and freeze experiment_config if not already frozen
        if not experiment.experiment_config:
            trans_configs = self.db.query(TransformationConfig).filter(
                TransformationConfig.project_id == project.id
            ).order_by(TransformationConfig.column_name.asc()).all()
            frozen_trans_json = [
                {
                    "id": str(tc.id),
                    "column_name": tc.column_name,
                    "missing_value_strategy": tc.missing_value_strategy,
                    "encoding_strategy": tc.encoding_strategy,
                    "scaling_strategy": tc.scaling_strategy,
                    "outlier_strategy": tc.outlier_strategy,
                    "is_active": tc.is_active,
                }
                for tc in trans_configs
            ]

            trans_snapshot = self.exp_repo.create_transformation_snapshot(
                experiment_id=experiment.id,
                config_json=frozen_trans_json,
            )

            cv_strategy = "STRATIFIED_KFOLD" if task_type == "CLASSIFICATION" else "KFOLD"

            experiment.experiment_config = {
                "task_type": task_type,
                "target": project.target_column,
                "split": {
                    "seed": split_seed,
                    "locked_test_pct": 20,
                },
                "cv": {
                    "strategy": cv_strategy,
                    "folds": folds,
                    "seed": cv_seed,
                },
                "preprocessing": {
                    "snapshot_id": str(trans_snapshot.id),
                },
                "feature_selection": {
                    "method": "rank_aggregation_ensemble",
                },
                "threshold_selection": {
                    "objective": "F1",
                    "search_range": [0.10, 0.90],
                    "resolution": 0.01,
                    "tie_break": "closest_to_0.5",
                },
                "deployment_threshold": {
                    "metric": (deployment_threshold.get("metric") or eff_metric) if deployment_threshold else eff_metric,
                    "min_value": deployment_threshold.get("min_value") if deployment_threshold else None,
                },
            }
            experiment.deployment_threshold_frozen_at_creation = True
            self.db.add(experiment)
            self.db.commit()
            self.db.refresh(experiment)

        try:
            # 3. Load Development partition ONLY (Zero Test Leakage Invariant)
            dev_df = self.split_service.get_development_data(latest_dataset.id)
            if project.target_column not in dev_df.columns:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Target column '{project.target_column}' not found in Development data."
                )

            y_raw = dev_df[project.target_column]
            drop_cols = [c for c in [project.target_column, "row_uid"] if c in dev_df.columns]
            X_df = dev_df.drop(columns=drop_cols)
            candidate_cols = list(X_df.columns)

            n_samples = len(dev_df)
            if n_samples < folds:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Insufficient samples ({n_samples}) for {folds}-fold cross-validation."
                )

            # 4. Configure CV Splitter
            if task_type == "CLASSIFICATION":
                class_counts = y_raw.value_counts()
                if (class_counts < folds).any():
                    splitter = KFold(n_splits=folds, shuffle=True, random_state=cv_seed)
                else:
                    splitter = StratifiedKFold(n_splits=folds, shuffle=True, random_state=cv_seed)
            else:
                splitter = KFold(n_splits=folds, shuffle=True, random_state=cv_seed)

            # Tracking per algorithm across folds
            # alg -> list of fold metric dictionaries
            fold_train_metrics: dict[str, list[dict[str, Any]]] = {alg: [] for alg in canonical_algs}
            fold_val_metrics: dict[str, list[dict[str, Any]]] = {alg: [] for alg in canonical_algs}
            fold_baselines: list[dict[str, float]] = []
            min_val_fold_size = n_samples

            # Out-of-fold probability tracking for binary threshold selection (SRS v9 §5 / §2.11)
            is_binary_clf = (task_type == "CLASSIFICATION" and len(np.unique(y_raw)) == 2)
            oof_val_probas: dict[str, np.ndarray] = {alg: np.zeros(n_samples, dtype=np.float64) for alg in canonical_algs}
            oof_fold_origin: dict[str, np.ndarray] = {alg: -np.ones(n_samples, dtype=int) for alg in canonical_algs}

            algorithm_errors: dict[str, str] = {}
            algorithm_hyperparams: dict[str, dict[str, Any]] = {}

            # 5. Inner Cross-Validation Loop
            for fold_idx, (train_idx, val_idx) in enumerate(splitter.split(X_df, y_raw)):
                # Zero Leakage verification logging
                train_indices_set = set(train_idx)
                val_indices_set = set(val_idx)
                leakage_overlap = train_indices_set.intersection(val_indices_set)
                if len(leakage_overlap) > 0:
                    raise RuntimeError(f"Data leakage detected in fold {fold_idx}: overlap={leakage_overlap}")

                val_size = len(val_idx)
                if val_size < min_val_fold_size:
                    min_val_fold_size = val_size

                logger.info(
                    f"Experiment {experiment.id} Fold {fold_idx}: "
                    f"Train size={len(train_idx)}, Val size={val_size}, Overlap=0"
                )

                X_train_fold = X_df.iloc[train_idx].copy()
                y_train_fold = y_raw.iloc[train_idx].values
                X_val_fold = X_df.iloc[val_idx].copy()
                y_val_fold = y_raw.iloc[val_idx].values

                # Step 5a: Fit fresh ColumnTransformer on fold training partition ONLY
                transformer = self.trans_service.build_pipeline(project.id)
                X_train_trans = transformer.fit_transform(X_train_fold)
                if hasattr(X_train_trans, "toarray"):
                    X_train_trans = X_train_trans.toarray()

                # Robust numeric conversion for feature selection
                if isinstance(X_train_trans, pd.DataFrame):
                    df_num = X_train_trans.copy()
                    for c in df_num.columns:
                        if not pd.api.types.is_numeric_dtype(df_num[c]):
                            df_num[c] = pd.factorize(df_num[c])[0].astype(np.float64)
                    X_train_trans = df_num.to_numpy(dtype=np.float64)
                else:
                    X_arr = np.asarray(X_train_trans)
                    if not np.issubdtype(X_arr.dtype, np.number):
                        n_rows, n_cols = X_arr.shape
                        num_matrix = np.zeros((n_rows, n_cols), dtype=np.float64)
                        for j in range(n_cols):
                            col_data = X_arr[:, j]
                            try:
                                num_matrix[:, j] = col_data.astype(np.float64)
                            except (ValueError, TypeError):
                                codes, _ = pd.factorize(col_data)
                                num_matrix[:, j] = codes.astype(np.float64)
                        X_train_trans = num_matrix
                    else:
                        X_train_trans = np.asarray(X_arr, dtype=np.float64)

                if np.isnan(X_train_trans).any():
                    fallback_imputer = SimpleImputer(strategy="mean")
                    X_train_trans = fallback_imputer.fit_transform(X_train_trans)

                fold_feature_names = self.fs_service.extract_clean_feature_names(transformer, candidate_cols)

                # Format y for feature selection / model fitting
                if task_type == "CLASSIFICATION":
                    if pd.api.types.is_numeric_dtype(y_train_fold) and not np.isnan(y_train_fold).any():
                        y_fit = y_train_fold.astype(int)
                        y_val_eval = y_val_fold.astype(int)
                    else:
                        y_fit = pd.Series(y_train_fold).astype(str).values
                        y_val_eval = pd.Series(y_val_fold).astype(str).values
                else:
                    y_fit = y_train_fold.astype(float)
                    y_val_eval = y_val_fold.astype(float)

                # Compute baseline metrics for this fold
                fold_baseline = EvaluationService.compute_naive_baseline(y_fit, task_type)
                fold_baselines.append(fold_baseline)

                # Step 5b: Run 4-technique Feature Selection ONCE per fold
                technique_results: dict[str, dict[str, Any]] = {}

                # 1. Correlation
                try:
                    corr_scores = self.fs_service.compute_correlation_scores(X_train_trans, y_fit, task_type)
                    technique_results["Correlation"] = {
                        "status": "APPLIED",
                        "raw_scores": corr_scores,
                        "status_reason": None,
                    }
                except Exception as e:
                    technique_results["Correlation"] = {
                        "status": "FAILED",
                        "raw_scores": None,
                        "status_reason": f"Correlation calculation failed: {str(e)}",
                    }

                # 2. Lasso
                try:
                    lasso_scores = self.fs_service.compute_lasso_scores(
                        X_train_trans, y_fit, task_type, seed=cv_seed + fold_idx
                    )
                    technique_results["Lasso"] = {
                        "status": "APPLIED",
                        "raw_scores": lasso_scores,
                        "status_reason": None,
                    }
                except Exception as e:
                    technique_results["Lasso"] = {
                        "status": "FAILED",
                        "raw_scores": None,
                        "status_reason": f"Lasso execution failed: {str(e)}",
                    }

                # 3. Random Forest
                try:
                    rf_scores = self.fs_service.compute_random_forest_scores(
                        X_train_trans, y_fit, task_type, seed=cv_seed + fold_idx
                    )
                    technique_results["Random Forest"] = {
                        "status": "APPLIED",
                        "raw_scores": rf_scores,
                        "status_reason": None,
                    }
                except Exception as e:
                    technique_results["Random Forest"] = {
                        "status": "FAILED",
                        "raw_scores": None,
                        "status_reason": f"Random Forest execution failed: {str(e)}",
                    }

                # 4. Permutation
                try:
                    perm_scores = self.fs_service.compute_permutation_scores(
                        X_train_trans, y_fit, task_type, seed=cv_seed + fold_idx
                    )
                    technique_results["Permutation"] = {
                        "status": "APPLIED",
                        "raw_scores": perm_scores,
                        "status_reason": None,
                    }
                except Exception as e:
                    technique_results["Permutation"] = {
                        "status": "FAILED",
                        "raw_scores": None,
                        "status_reason": f"Permutation importance failed: {str(e)}",
                    }

                # Aggregate fold ranks per SRS §2.7
                technique_scores_payload, fold_ensemble = self.fs_service.aggregate_technique_scores_for_fold(
                    fold_feature_names, technique_results
                )

                fold_selected = [
                    feat for feat, sc in fold_ensemble.items() if sc >= threshold
                ]
                if not fold_selected:
                    top_col = max(fold_ensemble.items(), key=lambda x: x[1])[0]
                    fold_selected = [top_col]

                # Persist fold feature selection results (ONCE per fold)
                self.exp_repo.add_fold_result(
                    experiment_id=experiment.id,
                    fold_index=fold_idx,
                    selected_features=fold_selected,
                    technique_scores=technique_scores_payload,
                )

                # Resolve selected indices for modeling
                selected_indices = [
                    i for i, c in enumerate(fold_feature_names) if c in fold_selected
                ]
                if not selected_indices:
                    selected_indices = list(range(len(fold_feature_names)))

                X_train_selected = X_train_trans[:, selected_indices]

                # Transform fold validation slice using the fold's fitted transformer
                X_val_trans = transformer.transform(X_val_fold)
                if hasattr(X_val_trans, "toarray"):
                    X_val_trans = X_val_trans.toarray()

                if isinstance(X_val_trans, pd.DataFrame):
                    df_v = X_val_trans.copy()
                    for c in df_v.columns:
                        if not pd.api.types.is_numeric_dtype(df_v[c]):
                            df_v[c] = pd.factorize(df_v[c])[0].astype(np.float64)
                    X_val_trans = df_v.to_numpy(dtype=np.float64)
                else:
                    X_v_arr = np.asarray(X_val_trans)
                    if not np.issubdtype(X_v_arr.dtype, np.number):
                        n_r, n_c = X_v_arr.shape
                        num_m = np.zeros((n_r, n_c), dtype=np.float64)
                        for j in range(n_c):
                            col_d = X_v_arr[:, j]
                            try:
                                num_m[:, j] = col_d.astype(np.float64)
                            except (ValueError, TypeError):
                                codes, _ = pd.factorize(col_d)
                                num_m[:, j] = codes.astype(np.float64)
                        X_val_trans = num_m
                    else:
                        X_val_trans = np.asarray(X_v_arr, dtype=np.float64)

                if np.isnan(X_val_trans).any():
                    fallback_imp = SimpleImputer(strategy="mean")
                    X_val_trans = fallback_imp.fit_transform(X_val_trans)

                X_val_selected = X_val_trans[:, selected_indices]

                # Step 5c: Train and evaluate each competing algorithm on top of shared selection
                for alg_name in canonical_algs:
                    if alg_name in algorithm_errors:
                        # Carry-in decision: any fold failure fails that algorithm entirely
                        continue

                    try:
                        if task_type == "REGRESSION":
                            trainer = RegressionTrainer(
                                algorithm_name=alg_name,
                                random_state=cv_seed + fold_idx,
                            )
                        else:
                            trainer = ClassificationTrainer(
                                algorithm_name=alg_name,
                                random_state=cv_seed + fold_idx,
                            )

                        if alg_name not in algorithm_hyperparams:
                            algorithm_hyperparams[alg_name] = trainer.hyperparameters

                        # Fit estimator on fold training data
                        trainer.fit(X_train_selected, y_fit)

                        # Predict on fold training & validation data
                        y_train_pred = trainer.predict(X_train_selected)
                        y_val_pred = trainer.predict(X_val_selected)

                        if task_type == "REGRESSION":
                            train_metrics = EvaluationService.evaluate_regression(
                                y_fit, y_train_pred, n=len(y_fit), p=len(fold_selected)
                            )
                            val_metrics = EvaluationService.evaluate_regression(
                                y_val_eval, y_val_pred, n=len(y_val_eval), p=len(fold_selected)
                            )
                        else:
                            y_train_proba = trainer.predict_proba(X_train_selected)
                            y_val_proba = trainer.predict_proba(X_val_selected)
                            train_metrics = EvaluationService.evaluate_classification(
                                y_fit, y_train_pred, y_proba=y_train_proba
                            )
                            val_metrics = EvaluationService.evaluate_classification(
                                y_val_eval, y_val_pred, y_proba=y_val_proba
                            )

                            # Record strictly out-of-fold validation probabilities for binary threshold search (SRS v9 §5)
                            if is_binary_clf and y_val_proba is not None:
                                if y_val_proba.ndim == 2 and y_val_proba.shape[1] >= 2:
                                    val_pos_p = y_val_proba[:, 1]
                                elif y_val_proba.ndim == 1:
                                    val_pos_p = y_val_proba
                                else:
                                    val_pos_p = y_val_proba[:, 0]
                                oof_val_probas[alg_name][val_idx] = val_pos_p
                                oof_fold_origin[alg_name][val_idx] = fold_idx

                        fold_train_metrics[alg_name].append(train_metrics)
                        fold_val_metrics[alg_name].append(val_metrics)

                    except Exception as alg_err:
                        logger.error(
                            f"Algorithm '{alg_name}' failed in fold {fold_idx}: {str(alg_err)}"
                        )
                        algorithm_errors[alg_name] = str(alg_err)

            # Compute overall average baseline across folds
            avg_baseline: dict[str, float] = {}
            if fold_baselines:
                for k in fold_baselines[0].keys():
                    vals = [b[k] for b in fold_baselines if b.get(k) is not None]
                    if vals:
                        avg_baseline[k] = float(np.mean(vals))

            # 6. Accumulate CV_MEAN Metrics, Diagnose Fit, Insert TrainedModel & ModelMetric Records
            created_model_records: dict[str, TrainedModel] = {}
            for alg_name in canonical_algs:
                params = algorithm_hyperparams.get(alg_name, {})
                has_failed = alg_name in algorithm_errors or len(fold_val_metrics[alg_name]) != folds

                if has_failed:
                    err_msg = algorithm_errors.get(alg_name, "Model execution failed across CV folds.")
                    model_rec = self.exp_repo.add_trained_model(
                        experiment_id=experiment.id,
                        algorithm_name=alg_name,
                        hyperparameters=params,
                        quick_cv_score=None,
                        fit_diagnosis=None,
                        model_selection_score=None,
                        status=ModelState.ARTIFACT_INVALID.value,
                        error_message=err_msg,
                    )
                else:
                    # Compute average train and validation metrics across all folds
                    val_fold_list = fold_val_metrics[alg_name]
                    train_fold_list = fold_train_metrics[alg_name]

                    cv_mean_metrics: dict[str, float] = {}
                    train_mean_metrics: dict[str, float] = {}

                    # Numeric keys only for averaging
                    metric_keys = [k for k, v in val_fold_list[0].items() if isinstance(v, (int, float))]
                    for mk in metric_keys:
                        cv_mean_vals = [f[mk] for f in val_fold_list if f.get(mk) is not None]
                        if cv_mean_vals:
                            cv_mean_metrics[mk] = float(np.mean(cv_mean_vals))

                        train_mean_vals = [f[mk] for f in train_fold_list if f.get(mk) is not None]
                        if train_mean_vals:
                            train_mean_metrics[mk] = float(np.mean(train_mean_vals))

                    # Fit diagnosis
                    fit_diag = EvaluationService.diagnose_fit(
                        train_metrics=train_mean_metrics,
                        cv_mean_metrics=cv_mean_metrics,
                        baseline_metrics=avg_baseline,
                        metric_name=eff_metric,
                        n_val_samples=min_val_fold_size,
                    )

                    # Model selection score (composite)
                    sel_score = EvaluationService.compute_model_selection_score(
                        task_type=task_type,
                        cv_mean_metrics=cv_mean_metrics,
                        baseline_metrics=avg_baseline,
                    )

                    # Quick CV score = primary selection metric mean
                    primary_val = cv_mean_metrics.get(eff_metric)
                    if primary_val is None:
                        if eff_metric in ["macro_f1", "f1_macro"]:
                            primary_val = cv_mean_metrics.get("macro_f1", cv_mean_metrics.get("f1_macro"))
                        elif eff_metric in ["weighted_f1", "f1_weighted"]:
                            primary_val = cv_mean_metrics.get("weighted_f1", cv_mean_metrics.get("f1_weighted"))

                    # Out-of-fold decision threshold selection for binary classification (SRS §2.11 / SRS v9 §5)
                    optimal_threshold = 0.5
                    if is_binary_clf and alg_name not in algorithm_errors:
                        try:
                            optimal_threshold, _ = EvaluationService.select_optimal_binary_threshold(
                                y_true=y_raw.values,
                                y_proba=oof_val_probas[alg_name],
                                metric_name=eff_metric,
                            )
                        except Exception as t_err:
                            logger.warning(f"OOF threshold search failed for {alg_name}: {t_err}, defaulting to 0.5")
                            optimal_threshold = 0.5

                    model_rec = self.exp_repo.add_trained_model(
                        experiment_id=experiment.id,
                        algorithm_name=alg_name,
                        hyperparameters=params,
                        quick_cv_score=primary_val,
                        fit_diagnosis=fit_diag,
                        model_selection_score=sel_score,
                        decision_threshold=optimal_threshold,
                        status=ModelState.TRAINED.value,
                        error_message=None,
                    )
                    created_model_records[alg_name] = model_rec

                    # Persist per-fold TRAIN and VALIDATION metrics
                    for f_idx in range(folds):
                        t_met = train_fold_list[f_idx]
                        v_met = val_fold_list[f_idx]

                        for m_k, m_v in t_met.items():
                            if isinstance(m_v, (int, float)):
                                self.exp_repo.add_model_metric(
                                    model_id=model_rec.id,
                                    metric_name=m_k,
                                    split="TRAIN",
                                    metric_value=float(m_v),
                                    fold_index=f_idx,
                                )
                            elif isinstance(m_v, (list, dict)):
                                self.exp_repo.add_model_metric(
                                    model_id=model_rec.id,
                                    metric_name=m_k,
                                    split="TRAIN",
                                    metric_json=m_v,
                                    fold_index=f_idx,
                                )

                        for m_k, m_v in v_met.items():
                            if isinstance(m_v, (int, float)):
                                self.exp_repo.add_model_metric(
                                    model_id=model_rec.id,
                                    metric_name=m_k,
                                    split="VALIDATION",
                                    metric_value=float(m_v),
                                    fold_index=f_idx,
                                )
                            elif isinstance(m_v, (list, dict)):
                                self.exp_repo.add_model_metric(
                                    model_id=model_rec.id,
                                    metric_name=m_k,
                                    split="VALIDATION",
                                    metric_json=m_v,
                                    fold_index=f_idx,
                                )

                    # Persist CV_MEAN rows
                    for m_k, m_v in cv_mean_metrics.items():
                        self.exp_repo.add_model_metric(
                            model_id=model_rec.id,
                            metric_name=m_k,
                            split="CV_MEAN",
                            metric_value=float(m_v),
                            fold_index=None,
                        )

            # 7. Finalize Experiment & Locked Test Single Evaluation
            all_trained_models = self.exp_repo.get_trained_models(experiment.id)
            has_successful_models = any(
                m.status in [ModelState.TRAINED.value, ModelState.ARTIFACT_VERIFIED.value, ModelState.DEPLOYABLE.value, "COMPLETED", "TRAINED"]
                for m in all_trained_models
            )
            if auto_finalize and has_successful_models:
                self.finalize_experiment(experiment.id)
            elif has_successful_models:
                self.exp_repo.update_status(experiment.id, ExperimentState.EVALUATED.value)
            else:
                self.exp_repo.update_status(experiment.id, ExperimentState.TRAINING_FAILED.value)

            project.pipeline_stage = "TRAINED"
            self.db.add(project)
            self.db.commit()

            return {
                "experiment_id": experiment.id,
                "project_id": project.id,
                "status": experiment.status,
                "task_type": task_type,
                "fold_count": folds,
                "cv_seed": cv_seed,
                "selection_metric": eff_metric,
                "selection_direction": eff_direction,
                "selected_model_id": experiment.selected_model_id,
                "locked_test_consumed": experiment.locked_test_consumed,
                "trained_models": [
                    {
                        "id": m.id,
                        "algorithm_name": m.algorithm_name,
                        "hyperparameters": m.hyperparameters,
                        "quick_cv_score": float(m.quick_cv_score) if m.quick_cv_score is not None else None,
                        "fit_diagnosis": m.fit_diagnosis,
                        "model_selection_score": float(m.model_selection_score) if m.model_selection_score is not None else None,
                        "status": m.status,
                        "error_message": m.error_message,
                    }
                    for m in self.exp_repo.get_trained_models(experiment.id)
                ],
            }


        except Exception as e:
            self.exp_repo.update_status(experiment.id, ExperimentState.TRAINING_FAILED.value)
            self.db.rollback()
            logger.exception(f"Experiment {experiment.id} failed: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Experiment execution failed: {str(e)}"
            )

    def finalize_experiment(self, experiment_id: UUID | str) -> dict[str, Any]:
        """
        Finalizes the experiment (SRS §2.9, §2.12):
        1. Selects the winning model based purely on selection_metric in selection_direction.
        2. Performs final fresh refit on the entire Development partition.
        3. Executes the single permitted Locked Test evaluation for the winning model.
        4. Permanently consumes the Locked Test partition for this experiment.
        """
        experiment = self.exp_repo.get_with_models(experiment_id)
        if not experiment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Experiment not found"
            )

        # Locked Test Guard
        if experiment.locked_test_consumed:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Locked test partition has already been consumed for this experiment."
            )

        project = self.project_repo.get_by_id(experiment.project_id)
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Associated project not found"
            )

        datasets = self.dataset_repo.get_by_project(project.id)
        if not datasets:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No dataset found for this project"
            )
        latest_dataset = datasets[0]

        completed_models = [
            m for m in experiment.trained_models
            if m.status in [ModelState.TRAINED.value, ModelState.ARTIFACT_VERIFIED.value, ModelState.DEPLOYABLE.value, "COMPLETED", "TRAINED"]
        ]
        if not completed_models:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No completed models available to select a winner."
            )

        # 1. Authoritative Winner Selection based strictly on selection_metric
        task_type = experiment.task_type or project.task_type or "REGRESSION"
        metric_name = experiment.selection_metric or ("rmse" if task_type == "REGRESSION" else "f1_macro")
        direction = experiment.selection_direction or ("MINIMIZE" if metric_name in ["rmse", "mae", "mse"] else "MAXIMIZE")

        # Map each model to its primary metric value from CV_MEAN
        model_scores = []
        for model in completed_models:
            cv_metric = next(
                (
                    m for m in model.metrics
                    if m.split == "CV_MEAN" and (
                        m.metric_name == metric_name
                        or (metric_name in ["macro_f1", "f1_macro"] and m.metric_name in ["macro_f1", "f1_macro"])
                        or (metric_name in ["weighted_f1", "f1_weighted"] and m.metric_name in ["weighted_f1", "f1_weighted"])
                    )
                ),
                None
            )
            val = float(cv_metric.metric_value) if cv_metric and cv_metric.metric_value is not None else float(model.quick_cv_score or 0.0)
            model_scores.append((model, val))

        if direction == "MINIMIZE":
            winning_model, winning_score = min(model_scores, key=lambda x: x[1])
        else:
            winning_model, winning_score = max(model_scores, key=lambda x: x[1])

        experiment.selected_model_id = winning_model.id
        self.db.add(experiment)
        self.db.commit()

        # 2. Final Refit on ENTIRE Development Partition
        dev_df = self.split_service.get_development_data(latest_dataset.id)
        total_dev_rows = len(dev_df)
        logger.info(
            f"Final refit for winning model {winning_model.id} ({winning_model.algorithm_name}) "
            f"on full Development partition: {total_dev_rows} rows."
        )

        target_col = project.target_column
        y_dev = dev_df[target_col].values
        drop_cols = [c for c in [target_col, "row_uid"] if c in dev_df.columns]
        X_dev = dev_df.drop(columns=drop_cols)
        candidate_cols = list(X_dev.columns)

        # Fresh Transformer on full Development data
        transformer = self.trans_service.build_pipeline(project.id)
        X_dev_trans = transformer.fit_transform(X_dev)
        if hasattr(X_dev_trans, "toarray"):
            X_dev_trans = X_dev_trans.toarray()

        if isinstance(X_dev_trans, pd.DataFrame):
            df_num = X_dev_trans.copy()
            for c in df_num.columns:
                if not pd.api.types.is_numeric_dtype(df_num[c]):
                    df_num[c] = pd.factorize(df_num[c])[0].astype(np.float64)
            X_dev_trans = df_num.to_numpy(dtype=np.float64)
        else:
            X_arr = np.asarray(X_dev_trans)
            if not np.issubdtype(X_arr.dtype, np.number):
                n_rows, n_cols = X_arr.shape
                num_matrix = np.zeros((n_rows, n_cols), dtype=np.float64)
                for j in range(n_cols):
                    col_data = X_arr[:, j]
                    try:
                        num_matrix[:, j] = col_data.astype(np.float64)
                    except (ValueError, TypeError):
                        codes, _ = pd.factorize(col_data)
                        num_matrix[:, j] = codes.astype(np.float64)
                X_dev_trans = num_matrix
            else:
                X_dev_trans = np.asarray(X_arr, dtype=np.float64)

        if np.isnan(X_dev_trans).any():
            fallback_imp = SimpleImputer(strategy="mean")
            X_dev_trans = fallback_imp.fit_transform(X_dev_trans)

        dev_feature_names = self.fs_service.extract_clean_feature_names(transformer, candidate_cols)

        # Format y_dev
        if task_type == "CLASSIFICATION":
            if pd.api.types.is_numeric_dtype(y_dev) and not np.isnan(y_dev).any():
                y_dev_fit = y_dev.astype(int)
            else:
                y_dev_fit = pd.Series(y_dev).astype(str).values
        else:
            y_dev_fit = y_dev.astype(float)

        # Select features on full development data (Rank Aggregation)
        final_selected = self._select_features_for_refit(
            X_dev_trans, y_dev_fit, task_type, dev_feature_names, experiment.cv_seed or 42
        )

        selected_indices = [
            i for i, c in enumerate(dev_feature_names) if c in final_selected
        ]
        if not selected_indices:
            selected_indices = list(range(len(dev_feature_names)))

        X_dev_selected = X_dev_trans[:, selected_indices]

        # Fresh Estimator for winning algorithm
        if task_type == "REGRESSION":
            trainer = RegressionTrainer(
                algorithm_name=winning_model.algorithm_name,
                hyperparameters=winning_model.hyperparameters,
                random_state=experiment.cv_seed or 42,
            )
        else:
            trainer = ClassificationTrainer(
                algorithm_name=winning_model.algorithm_name,
                hyperparameters=winning_model.hyperparameters,
                random_state=experiment.cv_seed or 42,
            )

        # Fit fresh winning model on full Development partition
        trainer.fit(X_dev_selected, y_dev_fit)

        # Day 8: Create Feature Selection Snapshot on Full Development Set
        fs_snapshot = self.exp_repo.create_feature_selection_snapshot(
            experiment_id=experiment.id,
            final_selected_features=final_selected,
            final_selection_method="rank_aggregation_ensemble",
        )
        experiment.feature_selection_snapshot_id = fs_snapshot.id

        # Day 8 / Day 2 (P0): Atomic Artifact Save: Write Artifact -> Verify Checksum -> Commit trained_models row
        artifact_dir = Path(settings.STORAGE_LOCAL_DIR) / "models" / str(project.id) / str(experiment.id)
        artifact_dir.mkdir(parents=True, exist_ok=True)
        artifact_file = artifact_dir / f"{winning_model.algorithm_name}.joblib"

        fitted_pipeline = {
            "algorithm_name": winning_model.algorithm_name,
            "task_type": task_type,
            "target_column": target_col,
            "feature_names_in": candidate_cols,
            "transformer": transformer,
            "selected_feature_names": final_selected,
            "selected_indices": selected_indices,
            "estimator": trainer.estimator if hasattr(trainer, "estimator") else trainer,
            "hyperparameters": winning_model.hyperparameters,
        }

        try:
            # 1. WRITE ARTIFACT
            joblib.dump(fitted_pipeline, artifact_file)

            if not artifact_file.exists():
                raise IOError(f"Artifact file '{artifact_file}' was not created on disk.")

            # 2. VERIFY CHECKSUM
            hasher = hashlib.sha256()
            with open(artifact_file, "rb") as f:
                while chunk := f.read(65536):
                    hasher.update(chunk)
            artifact_checksum = hasher.hexdigest()

            if not artifact_checksum or len(artifact_checksum) != 64:
                raise ValueError(f"Computed invalid SHA-256 checksum: {artifact_checksum}")

            # Re-read verification to guarantee disk integrity
            verify_hasher = hashlib.sha256()
            with open(artifact_file, "rb") as f:
                while chunk := f.read(65536):
                    verify_hasher.update(chunk)
            if verify_hasher.hexdigest() != artifact_checksum:
                raise ValueError("Artifact checksum re-verification failed immediately after write.")

            # 3. TRANSITION TO ARTIFACT_VERIFIED AND COMMIT TRAINED_MODELS ROW
            winning_model.artifact_path = str(artifact_file)
            winning_model.artifact_checksum = artifact_checksum
            winning_model.feature_selection_snapshot_id = fs_snapshot.id
            winning_model.status = ModelState.ARTIFACT_VERIFIED.value

            # Retrieve preprocessing snapshot ID
            trans_snapshot_id = None
            if experiment.experiment_config and isinstance(experiment.experiment_config, dict):
                trans_snapshot_id = experiment.experiment_config.get("preprocessing", {}).get("snapshot_id")
            if not trans_snapshot_id:
                trans_snapshots = self.exp_repo.get_transformation_snapshots(experiment.id)
                if trans_snapshots:
                    trans_snapshot_id = str(trans_snapshots[0].id)
            if trans_snapshot_id:
                try:
                    from uuid import UUID as PyUUID
                    winning_model.preprocessing_snapshot_id = PyUUID(trans_snapshot_id) if isinstance(trans_snapshot_id, str) else trans_snapshot_id
                except Exception:
                    pass

            self.db.add(experiment)
            self.db.add(winning_model)
            self.db.commit()

        except Exception as write_err:
            logger.error(f"Artifact save / DB commit failure for experiment {experiment.id}: {write_err}")
            self.db.rollback()

            cleanup_failed = False
            cleanup_error_msg = None

            # Attempt to clean up orphaned/partial file on disk
            if artifact_file.exists():
                try:
                    artifact_file.unlink()
                    logger.info(f"Successfully cleaned up orphaned artifact file '{artifact_file}' following DB commit failure.")
                except Exception as cleanup_err:
                    cleanup_failed = True
                    cleanup_error_msg = str(cleanup_err)
                    ORPHANED_RECOVERABLE_REGISTRY.add(str(artifact_file))
                    logger.error(
                        f"[ORPHANED_RECOVERABLE] Failed to delete orphaned artifact file at '{artifact_file}' "
                        f"after DB commit failure: {cleanup_err}. File marked as ORPHANED_RECOVERABLE for background scavenger."
                    )

            # Mark experiment as ARTIFACT_WRITE_FAILED
            try:
                self.exp_repo.update_status(experiment.id, ExperimentState.ARTIFACT_WRITE_FAILED.value)
            except Exception:
                pass

            if cleanup_failed:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"DB commit failed and orphaned artifact cleanup failed. Marked as ORPHANED_RECOVERABLE: {str(write_err)} | Cleanup error: {cleanup_error_msg}"
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Artifact write/commit failed; orphaned file cleaned up: {str(write_err)}"
                )



        # Evaluate final refit on Development partition
        if task_type == "REGRESSION":
            y_dev_pred = trainer.predict(X_dev_selected)
            refit_train_metrics = EvaluationService.evaluate_regression(
                y_dev_fit, y_dev_pred, n=len(y_dev_fit), p=len(final_selected)
            )
        else:
            y_dev_proba = trainer.predict_proba(X_dev_selected)
            unique_dev_classes = np.unique(y_dev_fit)
            if len(unique_dev_classes) == 2 and winning_model.decision_threshold is not None:
                t_thresh = float(winning_model.decision_threshold)
                if y_dev_proba.ndim == 2 and y_dev_proba.shape[1] >= 2:
                    p_dev = y_dev_proba[:, 1]
                elif y_dev_proba.ndim == 1:
                    p_dev = y_dev_proba
                else:
                    p_dev = y_dev_proba[:, 0]
                if pd.api.types.is_numeric_dtype(unique_dev_classes):
                    y_dev_pred = (p_dev >= t_thresh).astype(unique_dev_classes.dtype)
                else:
                    pos_c = unique_dev_classes[1]
                    neg_c = unique_dev_classes[0]
                    y_dev_pred = np.where(p_dev >= t_thresh, pos_c, neg_c)
            else:
                y_dev_pred = trainer.predict(X_dev_selected)
            refit_train_metrics = EvaluationService.evaluate_classification(
                y_dev_fit, y_dev_pred, y_proba=y_dev_proba
            )

        # Store refit TRAIN metrics for winning model (fold_index=None to distinguish from fold metrics)
        for m_k, m_v in refit_train_metrics.items():
            if isinstance(m_v, (int, float)):
                self.exp_repo.add_model_metric(
                    model_id=winning_model.id,
                    metric_name=m_k,
                    split="TRAIN",
                    metric_value=float(m_v),
                    fold_index=None,
                )
            elif isinstance(m_v, (list, dict)):
                self.exp_repo.add_model_metric(
                    model_id=winning_model.id,
                    metric_name=m_k,
                    split="TRAIN",
                    metric_json=m_v,
                    fold_index=None,
                )

        # 3. The Single Locked Test Evaluation
        locked_test_df = self.split_service.get_locked_test_data(latest_dataset.id)
        y_test_raw = locked_test_df[target_col].values
        X_test_raw = locked_test_df.drop(columns=[target_col])

        # Transform Locked Test data (transform ONLY, NEVER fit)
        X_test_trans = transformer.transform(X_test_raw)
        if hasattr(X_test_trans, "toarray"):
            X_test_trans = X_test_trans.toarray()

        if isinstance(X_test_trans, pd.DataFrame):
            df_t = X_test_trans.copy()
            for c in df_t.columns:
                if not pd.api.types.is_numeric_dtype(df_t[c]):
                    df_t[c] = pd.factorize(df_t[c])[0].astype(np.float64)
            X_test_trans = df_t.to_numpy(dtype=np.float64)
        else:
            X_t_arr = np.asarray(X_test_trans)
            if not np.issubdtype(X_t_arr.dtype, np.number):
                n_r, n_c = X_t_arr.shape
                num_m = np.zeros((n_r, n_c), dtype=np.float64)
                for j in range(n_c):
                    col_d = X_t_arr[:, j]
                    try:
                        num_m[:, j] = col_d.astype(np.float64)
                    except (ValueError, TypeError):
                        codes, _ = pd.factorize(col_d)
                        num_m[:, j] = codes.astype(np.float64)
                X_test_trans = num_m
            else:
                X_test_trans = np.asarray(X_t_arr, dtype=np.float64)

        if np.isnan(X_test_trans).any():
            fallback_imp = SimpleImputer(strategy="mean")
            X_test_trans = fallback_imp.fit_transform(X_test_trans)

        X_test_selected = X_test_trans[:, selected_indices]

        if task_type == "CLASSIFICATION":
            if pd.api.types.is_numeric_dtype(y_test_raw) and not np.isnan(y_test_raw).any():
                y_test_eval = y_test_raw.astype(int)
            else:
                y_test_eval = pd.Series(y_test_raw).astype(str).values
        else:
            y_test_eval = y_test_raw.astype(float)

        # Predict on Locked Test data (predict ONLY, NEVER fit)
        if task_type == "REGRESSION":
            y_test_pred = trainer.predict(X_test_selected)
            locked_test_metrics = EvaluationService.evaluate_regression(
                y_test_eval, y_test_pred, n=len(y_test_eval), p=len(final_selected)
            )
        else:
            y_test_proba = trainer.predict_proba(X_test_selected)
            unique_test_classes = np.unique(y_test_eval)
            if len(unique_test_classes) == 2 and winning_model.decision_threshold is not None:
                t_thresh = float(winning_model.decision_threshold)
                if y_test_proba.ndim == 2 and y_test_proba.shape[1] >= 2:
                    p_test = y_test_proba[:, 1]
                elif y_test_proba.ndim == 1:
                    p_test = y_test_proba
                else:
                    p_test = y_test_proba[:, 0]
                if pd.api.types.is_numeric_dtype(unique_test_classes):
                    y_test_pred = (p_test >= t_thresh).astype(unique_test_classes.dtype)
                else:
                    pos_c = unique_test_classes[1]
                    neg_c = unique_test_classes[0]
                    y_test_pred = np.where(p_test >= t_thresh, pos_c, neg_c)
            else:
                y_test_pred = trainer.predict(X_test_selected)
            locked_test_metrics = EvaluationService.evaluate_classification(
                y_test_eval, y_test_pred, y_proba=y_test_proba
            )

        # Store LOCKED_TEST model_metrics rows for the winning model
        for m_k, m_v in locked_test_metrics.items():
            if isinstance(m_v, (int, float)):
                self.exp_repo.add_model_metric(
                    model_id=winning_model.id,
                    metric_name=m_k,
                    split="LOCKED_TEST",
                    metric_value=float(m_v),
                    fold_index=None,
                )
            elif isinstance(m_v, (list, dict)):
                self.exp_repo.add_model_metric(
                    model_id=winning_model.id,
                    metric_name=m_k,
                    split="LOCKED_TEST",
                    metric_json=m_v,
                    fold_index=None,
                )

        # 4. Mark Locked Test as Permanently Consumed & Experiment Registered
        now = datetime.now(timezone.utc)
        self.exp_repo.update_status(experiment.id, ExperimentState.TEST_CONSUMED.value)
        self.exp_repo.mark_locked_test_consumed(experiment.id, consumed_at=now)
        winning_model.status = ModelState.DEPLOYABLE.value
        self.db.add(winning_model)
        self.db.commit()
        self.exp_repo.update_status(experiment.id, ExperimentState.REGISTERED.value, completed_at=now)

        return {
            "experiment_id": experiment.id,
            "status": ExperimentState.REGISTERED.value,
            "selected_model_id": winning_model.id,
            "winning_algorithm": winning_model.algorithm_name,
            "selection_metric": metric_name,
            "selection_direction": direction,
            "development_rows_fit": total_dev_rows,
            "locked_test_rows": len(locked_test_df),
            "locked_test_consumed": True,
            "locked_test_consumed_at": now.isoformat(),
            "locked_test_metrics": locked_test_metrics,
            "artifact_path": winning_model.artifact_path,
            "artifact_checksum": winning_model.artifact_checksum,
            "feature_selection_snapshot_id": str(fs_snapshot.id),
            "preprocessing_snapshot_id": str(winning_model.preprocessing_snapshot_id) if winning_model.preprocessing_snapshot_id else None,
        }

    def get_experiment_lineage(self, experiment_id: UUID | str) -> dict[str, Any]:
        """
        Retrieves the complete experiment lineage bundle (SRS §2.17 / Day 8).
        """
        experiment = self.exp_repo.get_with_models(experiment_id)
        if not experiment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Experiment not found"
            )

        trans_snapshots = self.exp_repo.get_transformation_snapshots(experiment.id)
        fs_snapshots = self.exp_repo.get_feature_selection_snapshots(experiment.id)

        winning_model = None
        if experiment.selected_model_id:
            winning_model = next((m for m in experiment.trained_models if m.id == experiment.selected_model_id), None)

        trans_snap_data = None
        if trans_snapshots:
            ts = trans_snapshots[0]
            trans_snap_data = {
                "id": str(ts.id),
                "experiment_id": str(ts.experiment_id),
                "config_json": ts.config_json,
                "created_at": ts.created_at.isoformat() if ts.created_at else None,
            }

        fs_snap_data = None
        if fs_snapshots:
            fs = fs_snapshots[0]
            fs_snap_data = {
                "id": str(fs.id),
                "experiment_id": str(fs.experiment_id),
                "final_selected_features": fs.final_selected_features,
                "final_selection_method": fs.final_selection_method,
                "created_at": fs.created_at.isoformat() if fs.created_at else None,
            }
        elif experiment.feature_selection_snapshot_id:
            fs = self.db.query(FeatureSelectionSnapshot).filter(FeatureSelectionSnapshot.id == experiment.feature_selection_snapshot_id).first()
            if fs:
                fs_snap_data = {
                    "id": str(fs.id),
                    "experiment_id": str(fs.experiment_id),
                    "final_selected_features": fs.final_selected_features,
                    "final_selection_method": fs.final_selection_method,
                    "created_at": fs.created_at.isoformat() if fs.created_at else None,
                }

        winning_model_data = None
        if winning_model:
            winning_model_data = {
                "id": str(winning_model.id),
                "algorithm_name": winning_model.algorithm_name,
                "artifact_path": winning_model.artifact_path,
                "artifact_checksum": winning_model.artifact_checksum,
                "preprocessing_snapshot_id": str(winning_model.preprocessing_snapshot_id) if winning_model.preprocessing_snapshot_id else None,
                "feature_selection_snapshot_id": str(winning_model.feature_selection_snapshot_id) if winning_model.feature_selection_snapshot_id else None,
            }

        # Extract deterministic tuple fields
        split_seed = None
        cv_strategy = None
        if experiment.experiment_config and isinstance(experiment.experiment_config, dict):
            split_seed = experiment.experiment_config.get("split", {}).get("seed")
            cv_strategy = experiment.experiment_config.get("cv", {}).get("strategy")
        if split_seed is None:
            dataset_splits = (
                self.db.query(DatasetSplit)
                .join(Dataset, DatasetSplit.dataset_id == Dataset.id)
                .filter(Dataset.project_id == experiment.project_id)
                .all()
            )
            if dataset_splits:
                split_seed = dataset_splits[0].split_seed

        if not cv_strategy:
            cv_strategy = "STRATIFIED_KFOLD" if (experiment.task_type == "CLASSIFICATION") else "KFOLD"

        dataset_hash = experiment.dataset_content_hash
        if not dataset_hash:
            datasets = self.dataset_repo.get_by_project(experiment.project_id)
            if datasets and datasets[0].content_hash:
                dataset_hash = datasets[0].content_hash

        return {
            "experiment_id": str(experiment.id),
            "project_id": str(experiment.project_id),
            "status": experiment.status,
            "task_type": experiment.task_type,
            "fold_count": experiment.fold_count,
            "cv_seed": experiment.cv_seed,
            "cv_strategy": cv_strategy,
            "split_seed": split_seed,
            "experiment_config": experiment.experiment_config,
            "dataset_content_hash": dataset_hash,
            "environment_capture_method": experiment.environment_capture_method,
            "code_version": experiment.code_version,
            "python_version": experiment.python_version,
            "sklearn_version": experiment.sklearn_version,
            "numpy_version": experiment.numpy_version,
            "pandas_version": experiment.pandas_version,
            "model_library_versions": experiment.model_library_versions or {},
            "transformation_snapshot": trans_snap_data,
            "feature_selection_snapshot": fs_snap_data,
            "winning_model": winning_model_data,
            "created_at": experiment.created_at.isoformat() if experiment.created_at else None,
            "completed_at": experiment.completed_at.isoformat() if experiment.completed_at else None,
        }

    def rerun_locked_test_diagnostic(self, experiment_id: UUID | str) -> dict[str, Any]:
        """
        Debug / Diagnostic rerun of locked test evaluation (SRS §2.12).
        Stores metrics with split='TEST_REUSED_DIAGNOSTIC'.
        NEVER overwrites split='LOCKED_TEST' rows and NEVER changes selected_model_id.
        """
        experiment = self.exp_repo.get_with_models(experiment_id)
        if not experiment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Experiment not found"
            )

        if not experiment.selected_model_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Experiment has no selected winning model to re-evaluate."
            )

        project = self.project_repo.get_by_id(experiment.project_id)
        datasets = self.dataset_repo.get_by_project(project.id)
        if not datasets:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No dataset found for this project"
            )
        latest_dataset = datasets[0]

        winning_model = next((m for m in experiment.trained_models if m.id == experiment.selected_model_id), None)
        if not winning_model:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Selected model record not found"
            )

        task_type = experiment.task_type or project.task_type or "REGRESSION"
        dev_df = self.split_service.get_development_data(latest_dataset.id)
        target_col = project.target_column
        y_dev = dev_df[target_col].values
        drop_cols = [c for c in [target_col, "row_uid"] if c in dev_df.columns]
        X_dev = dev_df.drop(columns=drop_cols)
        candidate_cols = list(X_dev.columns)

        transformer = self.trans_service.build_pipeline(project.id)
        X_dev_trans = transformer.fit_transform(X_dev)
        if hasattr(X_dev_trans, "toarray"):
            X_dev_trans = X_dev_trans.toarray()

        dev_feature_names = self.fs_service.extract_clean_feature_names(transformer, candidate_cols)

        if task_type == "CLASSIFICATION":
            if pd.api.types.is_numeric_dtype(y_dev) and not np.isnan(y_dev).any():
                y_dev_fit = y_dev.astype(int)
            else:
                y_dev_fit = pd.Series(y_dev).astype(str).values
        else:
            y_dev_fit = y_dev.astype(float)

        final_selected = self._select_features_for_refit(
            X_dev_trans, y_dev_fit, task_type, dev_feature_names, experiment.cv_seed or 42
        )
        selected_indices = [i for i, c in enumerate(dev_feature_names) if c in final_selected] or list(range(len(dev_feature_names)))
        X_dev_selected = X_dev_trans[:, selected_indices]

        if task_type == "REGRESSION":
            trainer = RegressionTrainer(
                algorithm_name=winning_model.algorithm_name,
                hyperparameters=winning_model.hyperparameters,
                random_state=experiment.cv_seed or 42,
            )
        else:
            trainer = ClassificationTrainer(
                algorithm_name=winning_model.algorithm_name,
                hyperparameters=winning_model.hyperparameters,
                random_state=experiment.cv_seed or 42,
            )

        trainer.fit(X_dev_selected, y_dev_fit)

        # Load Locked Test data & evaluate
        locked_test_df = self.split_service.get_locked_test_data(latest_dataset.id)
        y_test_raw = locked_test_df[target_col].values
        X_test_raw = locked_test_df.drop(columns=[target_col])

        X_test_trans = transformer.transform(X_test_raw)
        if hasattr(X_test_trans, "toarray"):
            X_test_trans = X_test_trans.toarray()
        X_test_selected = X_test_trans[:, selected_indices]

        if task_type == "CLASSIFICATION":
            if pd.api.types.is_numeric_dtype(y_test_raw) and not np.isnan(y_test_raw).any():
                y_test_eval = y_test_raw.astype(int)
            else:
                y_test_eval = pd.Series(y_test_raw).astype(str).values
            y_test_pred = trainer.predict(X_test_selected)
            y_test_proba = trainer.predict_proba(X_test_selected)
            diag_metrics = EvaluationService.evaluate_classification(
                y_test_eval, y_test_pred, y_proba=y_test_proba
            )
        else:
            y_test_eval = y_test_raw.astype(float)
            y_test_pred = trainer.predict(X_test_selected)
            diag_metrics = EvaluationService.evaluate_regression(
                y_test_eval, y_test_pred, n=len(y_test_eval), p=len(final_selected)
            )

        # Store with split='TEST_REUSED_DIAGNOSTIC'
        for m_k, m_v in diag_metrics.items():
            if isinstance(m_v, (int, float)):
                self.exp_repo.add_model_metric(
                    model_id=winning_model.id,
                    metric_name=m_k,
                    split="TEST_REUSED_DIAGNOSTIC",
                    metric_value=float(m_v),
                    fold_index=None,
                )
            elif isinstance(m_v, (list, dict)):
                self.exp_repo.add_model_metric(
                    model_id=winning_model.id,
                    metric_name=m_k,
                    split="TEST_REUSED_DIAGNOSTIC",
                    metric_json=m_v,
                    fold_index=None,
                )

        return {
            "experiment_id": experiment.id,
            "selected_model_id": winning_model.id,
            "split": "TEST_REUSED_DIAGNOSTIC",
            "message": "Diagnostic test evaluation recorded. This does not alter authoritative leaderboard evidence.",
            "metrics": diag_metrics,
        }

    def _select_features_for_refit(
        self,
        X_trans: np.ndarray,
        y: np.ndarray,
        task_type: str,
        feature_names: list[str],
        seed: int,
    ) -> list[str]:
        """Helper to run 4-technique rank aggregation on full Development data for refit."""
        technique_results = {}
        try:
            corr = self.fs_service.compute_correlation_scores(X_trans, y, task_type)
            technique_results["Correlation"] = {"status": "APPLIED", "raw_scores": corr, "status_reason": None}
        except Exception as e:
            technique_results["Correlation"] = {"status": "FAILED", "raw_scores": None, "status_reason": str(e)}

        try:
            lasso = self.fs_service.compute_lasso_scores(X_trans, y, task_type, seed=seed)
            technique_results["Lasso"] = {"status": "APPLIED", "raw_scores": lasso, "status_reason": None}
        except Exception as e:
            technique_results["Lasso"] = {"status": "FAILED", "raw_scores": None, "status_reason": str(e)}

        try:
            rf = self.fs_service.compute_random_forest_scores(X_trans, y, task_type, seed=seed)
            technique_results["Random Forest"] = {"status": "APPLIED", "raw_scores": rf, "status_reason": None}
        except Exception as e:
            technique_results["Random Forest"] = {"status": "FAILED", "raw_scores": None, "status_reason": str(e)}

        try:
            perm = self.fs_service.compute_permutation_scores(X_trans, y, task_type, seed=seed)
            technique_results["Permutation"] = {"status": "APPLIED", "raw_scores": perm, "status_reason": None}
        except Exception as e:
            technique_results["Permutation"] = {"status": "FAILED", "raw_scores": None, "status_reason": str(e)}

        _, ensemble = self.fs_service.aggregate_technique_scores_for_fold(feature_names, technique_results)
        selected = [feat for feat, sc in ensemble.items() if sc >= 0.0]
        if not selected:
            top_col = max(ensemble.items(), key=lambda x: x[1])[0]
            selected = [top_col]
        return selected

    def reproduce_experiment(self, experiment_id: UUID | str) -> dict[str, Any]:
        """
        Re-runs run_experiment with the identical frozen configuration and compares
        the newly observed primary metric against the original using the frozen contract
        tolerance from Week 1 (metric_absolute_tolerance=1e-3, metric_relative_tolerance=0.01).
        Returns {status, expected, observed, difference, relative_difference, metric_name, ...}.
        """
        exp_uuid = UUID(str(experiment_id)) if not isinstance(experiment_id, UUID) else experiment_id
        original_exp = self.exp_repo.get_with_models(exp_uuid)
        if not original_exp:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Experiment {exp_uuid} not found."
            )

        project = self.project_repo.get_by_id(original_exp.project_id)
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Associated project not found."
            )

        # 1. Determine primary selection metric and expected value from original experiment
        task_type = original_exp.task_type or project.task_type or "REGRESSION"
        metric_name = original_exp.selection_metric or ("rmse" if task_type == "REGRESSION" else "f1_macro")
        direction = original_exp.selection_direction or ("MINIMIZE" if metric_name in ["rmse", "mae", "mse"] else "MAXIMIZE")

        # Find original winning model or best completed model
        winning_model = None
        if original_exp.selected_model_id:
            winning_model = next((m for m in original_exp.trained_models if m.id == original_exp.selected_model_id), None)

        if not winning_model and original_exp.trained_models:
            completed = [
                m for m in original_exp.trained_models
                if m.status in [
                    ModelState.TRAINED.value,
                    ModelState.ARTIFACT_VERIFIED.value,
                    ModelState.DEPLOYABLE.value,
                    "COMPLETED",
                    "TRAINED",
                ]
            ]
            if completed:
                winning_model = completed[0]

        if not winning_model:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Original experiment {exp_uuid} has no completed trained models to reproduce."
            )

        # Extract expected metric value (CV_MEAN metric or quick_cv_score)
        expected_metric = next(
            (
                m for m in winning_model.metrics
                if m.split == "CV_MEAN" and (
                    m.metric_name == metric_name
                    or (metric_name in ["macro_f1", "f1_macro"] and m.metric_name in ["macro_f1", "f1_macro"])
                    or (metric_name in ["weighted_f1", "f1_weighted"] and m.metric_name in ["weighted_f1", "f1_weighted"])
                )
            ),
            None
        )
        if expected_metric and expected_metric.metric_value is not None:
            expected_val = float(expected_metric.metric_value)
        elif winning_model.quick_cv_score is not None:
            expected_val = float(winning_model.quick_cv_score)
        else:
            expected_val = 0.0

        # 2. Extract identical configuration
        algorithms = [m.algorithm_name for m in original_exp.trained_models] if original_exp.trained_models else None
        if original_exp.experiment_config and "algorithms" in original_exp.experiment_config:
            algorithms = original_exp.experiment_config["algorithms"]

        folds = original_exp.fold_count or 5
        cv_seed = original_exp.cv_seed

        dep_threshold = None
        if original_exp.experiment_config and "deployment_threshold" in original_exp.experiment_config:
            dep_threshold = original_exp.experiment_config["deployment_threshold"]

        # 3. Re-run experiment synchronously with identical configuration
        reproduced_res = self.run_experiment(
            project_id=original_exp.project_id,
            algorithms=algorithms,
            folds=folds,
            seed=cv_seed,
            selection_metric=metric_name,
            selection_direction=direction,
            auto_finalize=True,
            deployment_threshold=dep_threshold,
        )

        reproduced_exp_id = reproduced_res["experiment_id"]
        self.db.expire_all()
        reproduced_exp = self.exp_repo.get_with_models(reproduced_exp_id)

        # 4. Extract observed metric value from reproduced experiment
        reproduced_winning_model = None
        if reproduced_exp and reproduced_exp.selected_model_id:
            reproduced_winning_model = next((m for m in reproduced_exp.trained_models if m.id == reproduced_exp.selected_model_id), None)

        if not reproduced_winning_model and reproduced_exp and reproduced_exp.trained_models:
            reproduced_winning_model = reproduced_exp.trained_models[0]

        observed_val = 0.0
        if reproduced_winning_model:
            obs_metric = next(
                (
                    m for m in reproduced_winning_model.metrics
                    if m.split == "CV_MEAN" and (
                        m.metric_name == metric_name
                        or (metric_name in ["macro_f1", "f1_macro"] and m.metric_name in ["macro_f1", "f1_macro"])
                        or (metric_name in ["weighted_f1", "f1_weighted"] and m.metric_name in ["weighted_f1", "f1_weighted"])
                    )
                ),
                None
            )
            if obs_metric and obs_metric.metric_value is not None:
                observed_val = float(obs_metric.metric_value)
            elif reproduced_winning_model.quick_cv_score is not None:
                observed_val = float(reproduced_winning_model.quick_cv_score)

        # 5. Compare using Week 1 FROZEN tolerance contract (SRS v9 §3 & Architecture Contract §11)
        abs_tol = REPRODUCIBILITY_TOLERANCE["metric_absolute_tolerance"]  # 1e-3
        rel_tol = REPRODUCIBILITY_TOLERANCE["metric_relative_tolerance"]  # 0.01

        diff = abs(observed_val - expected_val)
        denom = abs(expected_val) + 1e-9
        rel_diff = diff / denom

        # Tolerant if absolute difference <= abs_tol OR relative difference <= rel_tol
        is_reproduced = (diff <= abs_tol) or (rel_diff <= rel_tol)
        reproduce_status = "REPRODUCED" if is_reproduced else "REPRODUCIBILITY_FAILED"

        return {
            "status": reproduce_status,
            "expected": expected_val,
            "observed": observed_val,
            "difference": diff,
            "relative_difference": rel_diff,
            "metric_name": metric_name,
            "original_experiment_id": original_exp.id,
            "reproduced_experiment_id": reproduced_exp_id,
            "tolerance": {
                "metric_absolute_tolerance": abs_tol,
                "metric_relative_tolerance": rel_tol,
            },
        }

    @classmethod
    def run_experiment_background(
        cls,
        project_id: UUID | str,
        experiment_id: UUID | str,
        algorithms: list[str],
        folds: int = 5,
        seed: int | None = None,
        threshold: float = 0.0,
        selection_metric: str | None = None,
        selection_direction: str | None = None,
        deployment_threshold: dict[str, Any] | None = None,
    ) -> None:
        """
        Background task runner for executing an experiment with an isolated database session.
        """
        db = SessionLocal()
        try:
            service = cls(db)
            service.run_experiment(
                project_id=project_id,
                algorithms=algorithms,
                folds=folds,
                seed=seed,
                threshold=threshold,
                selection_metric=selection_metric,
                selection_direction=selection_direction,
                experiment_id=experiment_id,
                auto_finalize=True,
                deployment_threshold=deployment_threshold,
            )
        except Exception as e:
            logger.exception(f"Background experiment {experiment_id} error: {str(e)}")
        finally:
            db.close()
