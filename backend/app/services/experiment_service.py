import logging
import secrets
from datetime import datetime, timezone
from uuid import UUID
from typing import Any
import numpy as np
import pandas as pd
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from sklearn.model_selection import KFold, StratifiedKFold
from sklearn.metrics import r2_score, accuracy_score

from app.core.database import SessionLocal
from app.models.project import Project
from app.models.experiment import Experiment
from app.models.trained_model import TrainedModel
from app.repositories.project_repository import ProjectRepository
from app.repositories.dataset_repository import DatasetRepository
from app.repositories.experiment_repository import ExperimentRepository
from app.services.dataset_split_service import DatasetSplitService
from app.services.transformation_service import TransformationService
from app.services.feature_selection_service import FeatureSelectionService
from app.services.storage_service import StorageService, get_storage_service
from app.services.trainers import (
    RegressionTrainer,
    ClassificationTrainer,
    FeatureSelector,
)

logger = logging.getLogger(__name__)

class ExperimentService:
    """
    Service responsible for coordinating Leakage-Safe Model Training Experiments (SRS §2.8).
    
    ARCHITECTURAL INVARIANTS:
    1. Zero Test Leakage (Invariant 1, 2, 6): Runs EXCLUSIVELY on Development partition via
       `DatasetSplitService.get_development_data()`. Locked Test partition is NEVER accessed.
    2. Shared Selection Per Fold: ColumnTransformer and 4-technique Rank-Aggregation Feature Selection
       are fit ONCE per CV fold. All competing algorithms evaluate on top of that same fold's
       transformed + selected training data.
    3. Evaluation-Only Cross-Validation: Every fold's fitted pipeline is temporary and discarded
       after computing quick sanity scores. No full Development refit or .joblib artifact is persisted
       today (Day 7 handles evaluation/model selection; Day 8 handles final winner refit and artifacts).
    4. Fault Isolation: A failure in an individual algorithm marks that algorithm's `trained_models`
       record as FAILED while other algorithms finish normally, and the experiment completes.
    5. Strict Validation: Algorithm names are validated against project `task_type` before execution,
       raising HTTP 422 on mismatch.
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
        experiment_id: UUID | str | None = None,
    ) -> dict[str, Any]:
        """
        Executes the cross-validation training experiment across requested algorithms.
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

        # Generate seed if not provided
        cv_seed = seed if seed is not None else secrets.randbelow(1_000_000)

        # 2. Retrieve or create Experiment record
        if experiment_id is not None:
            experiment = self.exp_repo.get_by_id(experiment_id)
            if not experiment:
                experiment = self.exp_repo.create_experiment(
                    project_id=project.id,
                    task_type=task_type,
                    fold_count=folds,
                    cv_seed=cv_seed,
                    status="RUNNING",
                )
            else:
                experiment.task_type = task_type
                experiment.fold_count = folds
                experiment.cv_seed = cv_seed
                experiment.status = "RUNNING"
                self.db.add(experiment)
                self.db.commit()
        else:
            experiment = self.exp_repo.create_experiment(
                project_id=project.id,
                task_type=task_type,
                fold_count=folds,
                cv_seed=cv_seed,
                status="RUNNING",
            )

        datasets = self.dataset_repo.get_by_project(project.id)
        if not datasets:
            self.exp_repo.update_status(experiment.id, "FAILED")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No dataset found for this project."
            )
        latest_dataset = datasets[0]

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
            # alg -> list of fold scores
            fold_scores: dict[str, list[float]] = {alg: [] for alg in canonical_algs}
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

                logger.info(
                    f"Experiment {experiment.id} Fold {fold_idx}: "
                    f"Train size={len(train_idx)}, Val size={len(val_idx)}, Overlap=0"
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
                    from sklearn.impute import SimpleImputer
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
                        # Skip if already failed in prior fold
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

                        # Predict on fold validation data
                        y_val_pred = trainer.predict(X_val_selected)

                        # Compute quick sanity score
                        if task_type == "REGRESSION":
                            score = float(r2_score(y_val_eval, y_val_pred))
                            if np.isnan(score):
                                score = 0.0
                        else:
                            score = float(accuracy_score(y_val_eval, y_val_pred))

                        fold_scores[alg_name].append(score)

                    except Exception as alg_err:
                        logger.error(
                            f"Algorithm '{alg_name}' failed in fold {fold_idx}: {str(alg_err)}"
                        )
                        algorithm_errors[alg_name] = str(alg_err)

            # 6. Accumulate Average Quick CV Scores and Insert TrainedModel Records
            # Fault tolerance: failed algorithms are recorded with status=FAILED, others succeed
            for alg_name in canonical_algs:
                params = algorithm_hyperparams.get(alg_name, {})
                if alg_name in algorithm_errors or len(fold_scores[alg_name]) == 0:
                    err_msg = algorithm_errors.get(alg_name, "Model execution failed across CV folds.")
                    self.exp_repo.add_trained_model(
                        experiment_id=experiment.id,
                        algorithm_name=alg_name,
                        hyperparameters=params,
                        quick_cv_score=None,
                        status="FAILED",
                        error_message=err_msg,
                    )
                else:
                    avg_quick_score = float(np.mean(fold_scores[alg_name]))
                    self.exp_repo.add_trained_model(
                        experiment_id=experiment.id,
                        algorithm_name=alg_name,
                        hyperparameters=params,
                        quick_cv_score=avg_quick_score,
                        status="COMPLETED",
                        error_message=None,
                    )

            # 7. Finalize Experiment & Transition Project Pipeline Stage
            self.exp_repo.update_status(experiment.id, "COMPLETED")
            project.pipeline_stage = "TRAINED"
            self.db.add(project)
            self.db.commit()

            return {
                "experiment_id": experiment.id,
                "project_id": project.id,
                "status": "COMPLETED",
                "task_type": task_type,
                "fold_count": folds,
                "cv_seed": cv_seed,
                "trained_models": [
                    {
                        "id": m.id,
                        "algorithm_name": m.algorithm_name,
                        "hyperparameters": m.hyperparameters,
                        "quick_cv_score": float(m.quick_cv_score) if m.quick_cv_score is not None else None,
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

    @classmethod
    def run_experiment_background(
        cls,
        project_id: UUID | str,
        experiment_id: UUID | str,
        algorithms: list[str],
        folds: int = 5,
        seed: int | None = None,
        threshold: float = 0.0,
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
                experiment_id=experiment_id,
            )
        except Exception as e:
            logger.exception(f"Background experiment {experiment_id} error: {str(e)}")
        finally:
            db.close()
