from uuid import UUID
from datetime import datetime, timezone
from typing import Any
import warnings
import numpy as np
import pandas as pd
from scipy.stats import rankdata
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from sklearn.model_selection import KFold, StratifiedKFold
from sklearn.linear_model import Lasso, LogisticRegression, Ridge
from sklearn.ensemble import RandomForestRegressor, RandomForestClassifier
from sklearn.inspection import permutation_importance
from sklearn.compose import ColumnTransformer

from app.models.project import Project
from app.models.dataset import Dataset
from app.models.experiment import Experiment
from app.models.feature_selection_fold_result import FeatureSelectionFoldResult
from app.models.feature_importance_score import FeatureImportanceScore
from app.repositories.project_repository import ProjectRepository
from app.repositories.dataset_repository import DatasetRepository
from app.repositories.experiment_repository import ExperimentRepository
from app.repositories.feature_importance_repository import FeatureImportanceRepository
from app.services.transformation_service import TransformationService
from app.services.dataset_split_service import DatasetSplitService
from app.services.storage_service import StorageService, get_storage_service

class FeatureSelectionService:
    """
    Service responsible for running the 4-technique Rank-Aggregation Feature Selection
    Ensemble within a leakage-safe Cross-Validation Harness (SRS §2.7, §2.17, §4.2).
    
    ARCHITECTURAL INVARIANTS:
    1. Zero Test Leakage (Invariant 1, 2, 6): Runs EXCLUSIVELY on Development partition.
       Locked Test set is NEVER accessed.
    2. Per-Fold Fitting: ColumnTransformer preprocessing and Feature Selection selectors
       are fitted fresh per training fold slice; validation folds are never leaked into selection.
    3. Exact Rank Aggregation Formula (SRS §2.7):
       - Ties handled via average rank.
       - p = 1 edge case yields rank score = 1.0 (prevents division by zero).
       - Normalized rank score: r_{j,T} = 1 - (rank_{j,T} - 1) / (p - 1).
       - Ensemble score = (1 / T_applied) * sum(r_{j,T}).
    4. Explicit Status Tracking: APPLIED, SKIPPED, or FAILED recorded per technique per fold.
    5. Traceable Persistence: Experiments, fold results, and live editable importance scores.
    """

    def __init__(self, db: Session, storage: StorageService | None = None):
        self.db = db
        self.storage = storage or get_storage_service()
        self.project_repo = ProjectRepository(db)
        self.dataset_repo = DatasetRepository(db)
        self.exp_repo = ExperimentRepository(db)
        self.importance_repo = FeatureImportanceRepository(db)
        self.trans_service = TransformationService(db, self.storage)
        self.split_service = DatasetSplitService(db, self.storage)

    # -------------------------------------------------------------------------
    # 1. Feature Selection Selectors (4 Techniques)
    # -------------------------------------------------------------------------

    @staticmethod
    def compute_correlation_scores(
        X: np.ndarray, y: np.ndarray, task_type: str
    ) -> np.ndarray:
        """
        Computes absolute correlation between each feature and the target.
        - Numeric / Binary / Regression: Absolute Pearson correlation.
        - Multiclass: Mean absolute Pearson correlation against one-hot target classes.
        """
        n_samples, p = X.shape
        scores = np.zeros(p, dtype=np.float64)

        if n_samples < 2 or p == 0:
            return scores

        y_arr = np.asarray(y)

        # Handle multiclass or non-numeric target
        if task_type == "CLASSIFICATION" and len(np.unique(y_arr)) > 2:
            # One-hot indicator matrix for classes
            classes = np.unique(y_arr)
            one_hot_y = np.column_stack([(y_arr == c).astype(float) for c in classes])
            
            for j in range(p):
                col = X[:, j]
                col_std = np.std(col)
                if col_std == 0 or np.isnan(col_std):
                    scores[j] = 0.0
                    continue
                
                corrs = []
                for k in range(one_hot_y.shape[1]):
                    yk = one_hot_y[:, k]
                    yk_std = np.std(yk)
                    if yk_std == 0 or np.isnan(yk_std):
                        continue
                    r = np.corrcoef(col, yk)[0, 1]
                    if not np.isnan(r):
                        corrs.append(abs(float(r)))
                scores[j] = float(np.mean(corrs)) if corrs else 0.0
        else:
            # Binary classification or numeric regression
            y_numeric = y_arr.astype(float)
            y_std = np.std(y_numeric)
            if y_std == 0 or np.isnan(y_std):
                return scores

            for j in range(p):
                col = X[:, j]
                col_std = np.std(col)
                if col_std == 0 or np.isnan(col_std):
                    scores[j] = 0.0
                    continue
                r = np.corrcoef(col, y_numeric)[0, 1]
                scores[j] = abs(float(r)) if not np.isnan(r) else 0.0

        return scores

    @staticmethod
    def compute_lasso_scores(
        X: np.ndarray, y: np.ndarray, task_type: str, seed: int = 42
    ) -> np.ndarray:
        """
        Computes L1 (Lasso) feature importance = abs(coefficients).
        - Regression: Lasso(alpha=0.01)
        - Classification: LogisticRegression(penalty='l1', solver='liblinear'/'saga')
        """
        n_samples, p = X.shape
        if p == 0:
            return np.zeros(0, dtype=np.float64)

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            if task_type == "REGRESSION":
                model = Lasso(alpha=0.01, max_iter=2000, random_state=seed)
                model.fit(X, y)
                coefs = np.abs(model.coef_)
                if coefs.ndim == 0:
                    coefs = np.array([float(coefs)])
                return coefs.astype(np.float64)
            else:
                n_classes = len(np.unique(y))
                solver = "liblinear" if n_classes <= 2 else "saga"
                model = LogisticRegression(
                    penalty="l1",
                    solver=solver,
                    max_iter=1000,
                    random_state=seed,
                    tol=1e-3,
                )
                model.fit(X, y)
                coefs = np.abs(model.coef_)
                if coefs.ndim == 2:
                    # Average magnitude across classes
                    return np.mean(coefs, axis=0).astype(np.float64)
                return coefs.flatten().astype(np.float64)

    @staticmethod
    def compute_random_forest_scores(
        X: np.ndarray, y: np.ndarray, task_type: str, seed: int = 42
    ) -> np.ndarray:
        """
        Computes Random Forest Gini / Impurity feature importances.
        """
        p = X.shape[1]
        if p == 0:
            return np.zeros(0, dtype=np.float64)

        if task_type == "REGRESSION":
            rf = RandomForestRegressor(
                n_estimators=50,
                max_depth=10,
                random_state=seed,
                n_jobs=1,
            )
        else:
            rf = RandomForestClassifier(
                n_estimators=50,
                max_depth=10,
                random_state=seed,
                n_jobs=1,
            )

        rf.fit(X, y)
        return rf.feature_importances_.astype(np.float64)

    @staticmethod
    def compute_permutation_scores(
        X: np.ndarray, y: np.ndarray, task_type: str, seed: int = 42
    ) -> np.ndarray:
        """
        Computes Permutation Feature Importance using a fast baseline estimator.
        """
        p = X.shape[1]
        if p == 0:
            return np.zeros(0, dtype=np.float64)

        if task_type == "REGRESSION":
            estimator = Ridge(alpha=1.0, random_state=seed)
        else:
            estimator = LogisticRegression(
                max_iter=500,
                random_state=seed,
                tol=1e-3,
            )

        estimator.fit(X, y)
        res = permutation_importance(
            estimator,
            X,
            y,
            n_repeats=5,
            random_state=seed,
            n_jobs=1,
        )
        # Importance is non-negative magnitude
        scores = np.maximum(0.0, res.importances_mean)
        return scores.astype(np.float64)

    # -------------------------------------------------------------------------
    # 2. Rank Aggregation Mathematical Engine (SRS §2.7)
    # -------------------------------------------------------------------------

    @classmethod
    def calculate_technique_rank_scores(
        cls, raw_scores: np.ndarray
    ) -> tuple[np.ndarray, np.ndarray]:
        """
        Given raw importance scores for p features:
        - Ranks features 1 (most important) to p (least important) based on |score|.
        - Ties receive the average rank.
        - Special case: p = 1 -> rank = 1.0, rank_score = 1.0 (avoids p - 1 = 0 division).
        - Normalized rank score: r_j,T = 1.0 - (rank_j,T - 1.0) / (p - 1.0).
        
        Returns:
            (ranks, normalized_rank_scores)
        """
        p = len(raw_scores)
        if p == 0:
            return np.array([]), np.array([])
        if p == 1:
            return np.array([1.0]), np.array([1.0])

        abs_scores = np.abs(raw_scores)
        # rankdata with negative values assigns rank 1 to the highest score
        # method='average' assigns average rank to ties (e.g. 2 tied at rank 2 and 3 get 2.5)
        ranks = rankdata(-abs_scores, method="average")
        
        # r_j,T = 1 - (rank_j,T - 1) / (p - 1)
        normalized_scores = 1.0 - (ranks - 1.0) / (p - 1.0)
        return ranks, normalized_scores

    @classmethod
    def aggregate_technique_scores_for_fold(
        cls,
        feature_names: list[str],
        technique_results: dict[str, dict[str, Any]],
    ) -> tuple[dict[str, dict[str, Any]], dict[str, float]]:
        """
        Combines technique scores per fold according to SRS §2.7:
        EnsembleScore_j = (1 / T_applied) * sum_{T in Applied} r_{j,T}
        
        Returns:
            (technique_scores_payload, ensemble_scores_dict)
        """
        p = len(feature_names)
        technique_scores_payload: dict[str, dict[str, Any]] = {}
        applied_rank_scores: list[np.ndarray] = []

        for tech_name, res in technique_results.items():
            status_val = res.get("status", "FAILED")
            status_reason = res.get("status_reason")
            raw_scores = res.get("raw_scores")

            if status_val == "APPLIED" and raw_scores is not None and len(raw_scores) == p:
                ranks, rank_scores = cls.calculate_technique_rank_scores(raw_scores)
                applied_rank_scores.append(rank_scores)

                tech_feature_map = {}
                for idx, col in enumerate(feature_names):
                    tech_feature_map[col] = {
                        "raw_score": float(raw_scores[idx]),
                        "rank": float(ranks[idx]),
                        "rank_score": float(rank_scores[idx]),
                        "status": "APPLIED",
                        "status_reason": None,
                    }
                technique_scores_payload[tech_name] = tech_feature_map
            else:
                tech_feature_map = {}
                for col in feature_names:
                    tech_feature_map[col] = {
                        "raw_score": None,
                        "rank": None,
                        "rank_score": None,
                        "status": status_val,
                        "status_reason": status_reason,
                    }
                technique_scores_payload[tech_name] = tech_feature_map

        # Calculate Ensemble Scores across applied techniques
        t_applied = len(applied_rank_scores)
        if t_applied > 0 and p > 0:
            sum_r = np.sum(np.vstack(applied_rank_scores), axis=0)
            ensemble_arr = sum_r / float(t_applied)
        else:
            ensemble_arr = np.zeros(p, dtype=np.float64)

        ensemble_scores_dict = {
            col: float(ensemble_arr[i]) for i, col in enumerate(feature_names)
        }

        return technique_scores_payload, ensemble_scores_dict

    # -------------------------------------------------------------------------
    # 3. Clean Feature Name Extraction from ColumnTransformer
    # -------------------------------------------------------------------------

    @staticmethod
    def extract_clean_feature_names(
        transformer: ColumnTransformer, input_columns: list[str]
    ) -> list[str]:
        """
        Extracts human-readable feature names from a fitted ColumnTransformer.
        Strips sklearn pipeline internal prefix decorators while preserving one-hot categories.
        """
        try:
            raw_names = list(transformer.get_feature_names_out())
            clean_names = []
            for name in raw_names:
                if "__" in name:
                    # Strip 'trans_col__' or 'remainder__' prefix
                    clean_names.append(name.split("__", 1)[1])
                else:
                    clean_names.append(name)
            return clean_names
        except Exception:
            return input_columns

    # -------------------------------------------------------------------------
    # 4. Cross-Validation Feature Selection Ensemble Harness
    # -------------------------------------------------------------------------

    def run_cv_feature_selection(
        self,
        project_id: UUID | str,
        n_splits: int = 5,
        cv_strategy: str | None = None,
        seed: int = 42,
        threshold: float = 0.0,
    ) -> dict[str, Any]:
        """
        Executes the Day 5 Rank-Aggregation Feature Selection Ensemble within a 5-fold CV harness.
        
        LEAKAGE INVARIANT:
        - Retrieves Development partition data ONLY. Locked Test partition is NEVER loaded.
        - Preprocessing ColumnTransformer is fitted inside each fold on X_train_fold only.
        - All 4 selectors evaluate fold-transformed training matrices.
        - Fold results persisted to `feature_selection_fold_results`.
        - Overall aggregate scores persisted to `feature_importance_scores`.
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
                detail="Project has no target column selected. Please configure target column first."
            )

        if project.task_type not in ["REGRESSION", "CLASSIFICATION"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Project task type must be either 'REGRESSION' or 'CLASSIFICATION' before running feature selection."
            )

        datasets = self.dataset_repo.get_by_project(project.id)
        if not datasets:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No datasets found for this project."
            )
        latest_dataset = datasets[0]

        # 1. Load Development partition ONLY (Zero Test Leakage)
        dev_df = self.split_service.get_development_data(latest_dataset.id)
        if project.target_column not in dev_df.columns:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Target column '{project.target_column}' does not exist in dataset."
            )

        # Separate target y and feature candidates X
        y_raw = dev_df[project.target_column]
        X_df = dev_df.drop(columns=[project.target_column])
        candidate_cols = list(X_df.columns)

        if len(candidate_cols) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No feature columns found in dataset after removing target column."
            )

        n_samples = len(dev_df)
        if n_samples < n_splits:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Insufficient samples ({n_samples}) for {n_splits}-fold cross-validation."
            )

        # 2. Configure CV Strategy
        task_type = project.task_type
        if cv_strategy == "STRATIFIED_KFOLD" or (cv_strategy is None and task_type == "CLASSIFICATION"):
            # Check class representation for stratified split
            class_counts = y_raw.value_counts()
            if (class_counts < n_splits).any():
                splitter = KFold(n_splits=n_splits, shuffle=True, random_state=seed)
            else:
                splitter = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=seed)
        else:
            splitter = KFold(n_splits=n_splits, shuffle=True, random_state=seed)

        # 3. Create Experiment shell record
        experiment = self.exp_repo.create_experiment(project.id, status="RUNNING")

        fold_ensemble_scores: list[dict[str, float]] = []
        all_feature_names: set[str] = set()

        try:
            # 4. Execute Per-Fold Leakage-Safe Feature Selection
            for fold_idx, (train_idx, val_idx) in enumerate(splitter.split(X_df, y_raw)):
                X_train_fold = X_df.iloc[train_idx].copy()
                y_train_fold = y_raw.iloc[train_idx].values

                # Fit fresh ColumnTransformer on training fold slice ONLY
                transformer = self.trans_service.build_pipeline(project.id)
                X_train_trans = transformer.fit_transform(X_train_fold)
                if hasattr(X_train_trans, "toarray"):
                    X_train_trans = X_train_trans.toarray()

                # Robust numeric conversion for unencoded/passthrough columns
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

                # Fallback imputer for unhandled NaNs during feature selection
                if np.isnan(X_train_trans).any():
                    from sklearn.impute import SimpleImputer
                    fallback_imputer = SimpleImputer(strategy="mean")
                    X_train_trans = fallback_imputer.fit_transform(X_train_trans)

                # Resolve feature names
                fold_feature_names = self.extract_clean_feature_names(transformer, candidate_cols)
                all_feature_names.update(fold_feature_names)

                # Ensure y is clean for model fitting
                if task_type == "CLASSIFICATION":
                    # Convert to string labels or categorical codes
                    if pd.api.types.is_numeric_dtype(y_train_fold) and not np.isnan(y_train_fold).any():
                        y_fit = y_train_fold.astype(int)
                    else:
                        y_fit = pd.Series(y_train_fold).astype(str).values
                else:
                    y_fit = y_train_fold.astype(float)

                technique_results: dict[str, dict[str, Any]] = {}

                # Technique A: Correlation
                try:
                    corr_scores = self.compute_correlation_scores(X_train_trans, y_fit, task_type)
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

                # Technique B: Lasso (L1)
                try:
                    lasso_scores = self.compute_lasso_scores(X_train_trans, y_fit, task_type, seed=seed + fold_idx)
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

                # Technique C: Random Forest
                try:
                    rf_scores = self.compute_random_forest_scores(X_train_trans, y_fit, task_type, seed=seed + fold_idx)
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

                # Technique D: Permutation Importance
                try:
                    perm_scores = self.compute_permutation_scores(X_train_trans, y_fit, task_type, seed=seed + fold_idx)
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

                # Aggregate fold ranks according to SRS §2.7
                technique_scores_payload, fold_ensemble = self.aggregate_technique_scores_for_fold(
                    fold_feature_names, technique_results
                )
                fold_ensemble_scores.append(fold_ensemble)

                # Determine fold selected features based on threshold
                fold_selected = [
                    feat for feat, sc in fold_ensemble.items() if sc >= threshold
                ]
                if not fold_selected:
                    # If threshold selects none, default to top feature
                    top_col = max(fold_ensemble.items(), key=lambda x: x[1])[0]
                    fold_selected = [top_col]

                # Persist fold record
                self.exp_repo.add_fold_result(
                    experiment_id=experiment.id,
                    fold_index=fold_idx,
                    selected_features=fold_selected,
                    technique_scores=technique_scores_payload,
                )

            # 5. Aggregate Across All CV Folds
            overall_scores: dict[str, float] = {}
            for col in all_feature_names:
                scores_for_col = [
                    fold_dict[col] for fold_dict in fold_ensemble_scores if col in fold_dict
                ]
                overall_scores[col] = float(np.mean(scores_for_col)) if scores_for_col else 0.0

            # 6. Upsert into live editable `feature_importance_scores` table
            importance_items = self.importance_repo.upsert_scores(
                project.id, overall_scores, default_selected=True
            )
            # Apply initial threshold filtering
            self.importance_repo.update_selection(project.id, threshold=threshold)

            # 7. Finalize Experiment & Update Project Stage
            self.exp_repo.update_status(experiment.id, "COMPLETED")
            if project.pipeline_stage in ["DATA", "SPLIT", "PROFILED", "TRANSFORMED"]:
                project.pipeline_stage = "FEATURE_SELECTED"
                self.db.add(project)
                self.db.commit()

            return {
                "project_id": project.id,
                "experiment_id": experiment.id,
                "status": "COMPLETED",
                "fold_count": n_splits,
                "features": [
                    {
                        "column_name": item.column_name,
                        "avg_rank_score": float(item.avg_rank_score),
                        "is_selected": item.is_selected,
                    }
                    for item in self.importance_repo.get_by_project(project.id)
                ],
            }

        except Exception as err:
            self.exp_repo.update_status(experiment.id, "FAILED")
            self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Cross-validation feature selection failed: {str(err)}"
            )

    def get_feature_importance_scores(self, project_id: UUID | str) -> dict[str, Any]:
        """
        Returns the current live feature importance scores and selection states.
        """
        project = self.project_repo.get_by_id(project_id)
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found"
            )

        experiments = self.exp_repo.get_by_project(project.id)
        latest_exp_id = experiments[0].id if experiments else None

        items = self.importance_repo.get_by_project(project.id)
        return {
            "project_id": project.id,
            "experiment_id": latest_exp_id,
            "features": [
                {
                    "column_name": item.column_name,
                    "avg_rank_score": float(item.avg_rank_score),
                    "is_selected": item.is_selected,
                }
                for item in items
            ],
        }

    def get_experiment_fold_results(
        self, project_id: UUID | str, experiment_id: UUID | str
    ) -> dict[str, Any]:
        """
        Returns the per-fold detailed execution breakdown for an experiment.
        """
        experiment = self.exp_repo.get_by_id(experiment_id)
        if not experiment or str(experiment.project_id) != str(project_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Experiment not found for this project."
            )

        folds = self.exp_repo.get_fold_results(experiment.id)
        return {
            "experiment_id": experiment.id,
            "project_id": experiment.project_id,
            "status": experiment.status,
            "created_at": experiment.created_at,
            "completed_at": experiment.completed_at,
            "fold_count": len(folds),
            "folds": [
                {
                    "id": f.id,
                    "experiment_id": f.experiment_id,
                    "fold_index": f.fold_index,
                    "selected_features": f.selected_features,
                    "technique_scores": f.technique_scores,
                }
                for f in folds
            ],
        }

    def update_feature_selection(
        self,
        project_id: UUID | str,
        threshold: float | None = None,
        selected_features: list[str] | None = None,
    ) -> dict[str, Any]:
        """
        Updates live `is_selected` states based on threshold or explicit column list.
        """
        project = self.project_repo.get_by_id(project_id)
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found"
            )

        updated_items = self.importance_repo.update_selection(
            project.id, threshold=threshold, selected_columns=selected_features
        )
        experiments = self.exp_repo.get_by_project(project.id)
        latest_exp_id = experiments[0].id if experiments else None

        return {
            "project_id": project.id,
            "experiment_id": latest_exp_id,
            "features": [
                {
                    "column_name": item.column_name,
                    "avg_rank_score": float(item.avg_rank_score),
                    "is_selected": item.is_selected,
                }
                for item in updated_items
            ],
        }
