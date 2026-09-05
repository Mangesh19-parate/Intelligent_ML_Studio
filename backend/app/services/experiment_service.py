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
from sqlalchemy.orm import Session
from sklearn.model_selection import KFold, StratifiedKFold
from sklearn.impute import SimpleImputer

from app.core.config import settings
from app.core.database import SessionLocal
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
        if task_type == "REGRESSION":
            valid_set = self.VALID_REGRESSION_ALGORITHMS
            canonical_map = RegressionTrainer.CANONICAL_NAMES
            allowed_str = "LinearRegression, Ridge, RandomForestRegressor"
        elif task_type == "CLASSIFICATION":
            valid_set = self.VALID_CLASSIFICATION_ALGORITHMS
            canonical_map = ClassificationTrainer.CANONICAL_NAMES
            allowed_str = "LogisticRegression, RandomForestClassifier, GradientBoostingClassifier"
        else:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Unsupported project task_type '{task_type}' for model training."
            )

        for alg in algorithms:
            if alg not in valid_set:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=(
                        f"Invalid algorithm '{alg}' for task type {task_type}. "
                        f"Allowed algorithms: {allowed_str}"
                    )
                )
            canonical_name = canonical_map[alg]
            if canonical_name not in canonical_algorithms:
                canonical_algorithms.append(canonical_name)

        return canonical_algorithms

    def run_experiment(
        self,
        project_id: UUID | str,
        algorithms: list[str],
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
            experiment = self.exp_repo.get_by_id(experiment_id)
            if not experiment:
                experiment = self.exp_repo.create_experiment(
                    project_id=project.id,
                    task_type=task_type,
                    fold_count=folds,
                    cv_seed=cv_seed,
                    selection_metric=eff_metric,
                    selection_direction=eff_direction,
                    status="RUNNING",
                    dataset_content_hash=dataset_content_hash,
                    code_version=env_info.get("code_version"),
                    python_version=env_info.get("python_version"),
                    sklearn_version=env_info.get("sklearn_version"),
                    numpy_version=env_info.get("numpy_version"),
                    pandas_version=env_info.get("pandas_version"),
                    model_library_versions=env_info.get("model_library_versions"),
                    environment_capture_method="CAPTURED_LIVE",
                )
            else:
                experiment.task_type = task_type
                experiment.fold_count = folds
                experiment.cv_seed = cv_seed
                experiment.selection_metric = eff_metric
                experiment.selection_direction = eff_direction
                experiment.status = "RUNNING"
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
        else:
            experiment = self.exp_repo.create_experiment(
                project_id=project.id,
                task_type=task_type,
                fold_count=folds,
                cv_seed=cv_seed,
                selection_metric=eff_metric,
                selection_direction=eff_direction,
                status="RUNNING",
                dataset_content_hash=dataset_content_hash,
                code_version=env_info.get("code_version"),
                python_version=env_info.get("python_version"),
                sklearn_version=env_info.get("sklearn_version"),
                numpy_version=env_info.get("numpy_version"),
                pandas_version=env_info.get("pandas_version"),
                model_library_versions=env_info.get("model_library_versions"),
                environment_capture_method="CAPTURED_LIVE",
            )

        # 4. Deep copy current transformation configs into TransformationSnapshot (Day 8)
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

        # 5. Assemble and freeze experiment_config (SRS §2.5 / Day 8) - never edited after
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
            X_df = dev_df.drop(columns=[project.target_column])
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
                        status="FAILED",
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

                    model_rec = self.exp_repo.add_trained_model(
                        experiment_id=experiment.id,
                        algorithm_name=alg_name,
                        hyperparameters=params,
                        quick_cv_score=primary_val,
                        fit_diagnosis=fit_diag,
                        model_selection_score=sel_score,
                        status="COMPLETED",
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
            if auto_finalize and any(m.status == "COMPLETED" for m in self.exp_repo.get_trained_models(experiment.id)):
                self.finalize_experiment(experiment.id)
            else:
                self.exp_repo.update_status(experiment.id, "COMPLETED")

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
            self.exp_repo.update_status(experiment.id, "FAILED")
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

        completed_models = [m for m in experiment.trained_models if m.status == "COMPLETED"]
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
                (m for m in model.metrics if m.split == "CV_MEAN" and m.metric_name == metric_name),
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
        X_dev = dev_df.drop(columns=[target_col])
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

        # Day 8: Serialize fitted pipeline to disk (/data/models/{project_id}/{experiment_id}/{algorithm_name}.joblib)
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
        joblib.dump(fitted_pipeline, artifact_file)

        # Compute SHA-256 Integrity Checksum
        hasher = hashlib.sha256()
        with open(artifact_file, "rb") as f:
            while chunk := f.read(65536):
                hasher.update(chunk)
        artifact_checksum = hasher.hexdigest()

        # Update winning model record with artifact path, checksum, and snapshot foreign keys
        winning_model.artifact_path = str(artifact_file)
        winning_model.artifact_checksum = artifact_checksum
        winning_model.feature_selection_snapshot_id = fs_snapshot.id

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

        # Evaluate final refit on Development partition
        y_dev_pred = trainer.predict(X_dev_selected)
        if task_type == "REGRESSION":
            refit_train_metrics = EvaluationService.evaluate_regression(
                y_dev_fit, y_dev_pred, n=len(y_dev_fit), p=len(final_selected)
            )
        else:
            y_dev_proba = trainer.predict_proba(X_dev_selected)
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
        y_test_pred = trainer.predict(X_test_selected)

        if task_type == "REGRESSION":
            locked_test_metrics = EvaluationService.evaluate_regression(
                y_test_eval, y_test_pred, n=len(y_test_eval), p=len(final_selected)
            )
        else:
            y_test_proba = trainer.predict_proba(X_test_selected)
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

        # 4. Mark Locked Test as Permanently Consumed & Experiment Completed
        now = datetime.now(timezone.utc)
        self.exp_repo.mark_locked_test_consumed(experiment.id, consumed_at=now)
        self.exp_repo.update_status(experiment.id, "COMPLETED", completed_at=now)

        return {
            "experiment_id": experiment.id,
            "status": "COMPLETED",
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

        return {
            "experiment_id": str(experiment.id),
            "project_id": str(experiment.project_id),
            "status": experiment.status,
            "experiment_config": experiment.experiment_config,
            "dataset_content_hash": experiment.dataset_content_hash,
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
        X_dev = dev_df.drop(columns=[target_col])
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
