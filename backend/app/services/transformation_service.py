from uuid import UUID
from typing import Any
import numpy as np
import pandas as pd
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer, KNNImputer
# Enable IterativeImputer (experimental in scikit-learn)
from sklearn.experimental import enable_iterative_imputer  # noqa: F401
from sklearn.impute import IterativeImputer
from sklearn.preprocessing import StandardScaler, MinMaxScaler, RobustScaler, OneHotEncoder, OrdinalEncoder

from app.models.dataset import Dataset
from app.models.dataset_column import DatasetColumn
from app.models.project import Project
from app.models.transformation_config import TransformationConfig
from app.repositories.dataset_repository import DatasetRepository
from app.repositories.project_repository import ProjectRepository
from app.repositories.transformation_repository import TransformationRepository
from app.schemas.transformation import (
    ALLOWED_NUMERIC_MISSING,
    ALLOWED_CATEGORICAL_MISSING,
    ALLOWED_ENCODING,
    ALLOWED_SCALING,
    ALLOWED_OUTLIER,
    TransformationConfigUpdate,
)
from app.services.dataset_split_service import DatasetSplitService
from app.services.storage_service import StorageService, get_storage_service
from app.services.transformers import OutlierCapper

class TransformationService:
    """
    Service responsible for managing feature transformation configurations and
    generating unfit scikit-learn ColumnTransformer templates.
    
    ARCHITECTURAL INVARIANTS (SRS §2.6, §4.2):
    1. Template Architecture: `build_pipeline` generates a fresh, UNFIT ColumnTransformer.
       It is NEVER fit on the whole dataset upfront; Day 6/7 cross-validation fits it per fold.
    2. Strict Structural Validation: Numeric vs categorical strategies are strictly enforced
       against Day 1 structural column metadata; invalid assignments return HTTP 422.
    3. UI Preview Isolation: `preview_transformation` fits exclusively on a temporary sample
       of Development partition data and immediately discards the fitted state.
    4. Database = Declared Recipe: Database stores only configuration strings, never learned
       values (means, standard deviations, quantile bounds, category encodings).
    """

    def __init__(self, db: Session, storage: StorageService | None = None):
        self.db = db
        self.storage = storage or get_storage_service()
        self.project_repo = ProjectRepository(db)
        self.dataset_repo = DatasetRepository(db)
        self.trans_repo = TransformationRepository(db)
        self.split_service = DatasetSplitService(db, self.storage)

    def _get_project_and_latest_dataset(self, project_id: UUID | str) -> tuple[Project, Dataset]:
        project = self.project_repo.get_by_id(project_id)
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found"
            )

        datasets = self.dataset_repo.get_by_project(project.id)
        if not datasets:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Project has no uploaded datasets. Please upload a dataset first."
            )

        return project, datasets[0]

    def _get_column_metadata(self, dataset_id: UUID | str, column_name: str) -> DatasetColumn:
        column_record = (
            self.db.query(DatasetColumn)
            .filter(
                DatasetColumn.dataset_id == dataset_id,
                DatasetColumn.column_name == column_name,
            )
            .first()
        )
        if not column_record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Column '{column_name}' not found in dataset schema."
            )
        return column_record

    def get_project_configs(self, project_id: UUID | str) -> list[dict]:
        """
        Returns all active configs for the project, one row per dataset column.
        Columns without an explicit config row default to 'none'.
        """
        project, latest_dataset = self._get_project_and_latest_dataset(project_id)
        columns = self.dataset_repo.get_columns_by_dataset(latest_dataset.id)
        existing_configs = {
            c.column_name: c for c in self.trans_repo.get_by_project(project.id)
        }

        result = []
        for col in columns:
            cfg = existing_configs.get(col.column_name)
            if cfg:
                result.append({
                    "id": cfg.id,
                    "project_id": project.id,
                    "column_name": col.column_name,
                    "data_type": col.data_type,
                    "missing_value_strategy": cfg.missing_value_strategy or "none",
                    "encoding_strategy": cfg.encoding_strategy or "none",
                    "scaling_strategy": cfg.scaling_strategy or "none",
                    "outlier_strategy": cfg.outlier_strategy or "none",
                    "is_active": cfg.is_active,
                    "created_at": cfg.created_at,
                    "updated_at": cfg.updated_at,
                })
            else:
                result.append({
                    "id": None,
                    "project_id": project.id,
                    "column_name": col.column_name,
                    "data_type": col.data_type,
                    "missing_value_strategy": "none",
                    "encoding_strategy": "none",
                    "scaling_strategy": "none",
                    "outlier_strategy": "none",
                    "is_active": True,
                    "created_at": None,
                    "updated_at": None,
                })
        return result

    def validate_strategy_for_dtype(
        self,
        data_type: str,
        missing_strategy: str | None = None,
        encoding_strategy: str | None = None,
        scaling_strategy: str | None = None,
        outlier_strategy: str | None = None,
    ) -> None:
        """
        Strict validation against structural column data types.
        Raises HTTP 422 on strategy mismatch or unsupported values.
        """
        is_numeric = data_type == "NUMERIC"
        is_categorical = data_type in ["CATEGORICAL", "MIXED"]

        # Missing value validation
        if missing_strategy and missing_strategy != "none":
            if is_numeric and missing_strategy not in ALLOWED_NUMERIC_MISSING:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Invalid missing value strategy '{missing_strategy}' for NUMERIC column. Allowed: {sorted(list(ALLOWED_NUMERIC_MISSING))}",
                )
            elif is_categorical and missing_strategy not in ALLOWED_CATEGORICAL_MISSING:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Invalid missing value strategy '{missing_strategy}' for CATEGORICAL column. Allowed: {sorted(list(ALLOWED_CATEGORICAL_MISSING))}",
                )
            elif not is_numeric and not is_categorical:
                # DATETIME or other
                if missing_strategy not in ["none", "mode"]:
                    raise HTTPException(
                        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                        detail=f"Strategy '{missing_strategy}' not supported for dtype '{data_type}'.",
                    )

        # Encoding validation (CATEGORICAL only)
        if encoding_strategy and encoding_strategy != "none":
            if not is_categorical:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Encoding strategy '{encoding_strategy}' is only valid for CATEGORICAL columns, but column is '{data_type}'.",
                )
            if encoding_strategy not in ALLOWED_ENCODING:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Invalid encoding strategy '{encoding_strategy}'. Allowed: {sorted(list(ALLOWED_ENCODING))}",
                )

        # Scaling validation (NUMERIC only)
        if scaling_strategy and scaling_strategy != "none":
            if not is_numeric:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Scaling strategy '{scaling_strategy}' is only valid for NUMERIC columns, but column is '{data_type}'.",
                )
            if scaling_strategy not in ALLOWED_SCALING:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Invalid scaling strategy '{scaling_strategy}'. Allowed: {sorted(list(ALLOWED_SCALING))}",
                )

        # Outlier validation (NUMERIC only)
        if outlier_strategy and outlier_strategy != "none":
            if not is_numeric:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Outlier strategy '{outlier_strategy}' is only valid for NUMERIC columns, but column is '{data_type}'.",
                )
            if outlier_strategy not in ALLOWED_OUTLIER:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Invalid outlier strategy '{outlier_strategy}'. Allowed: {sorted(list(ALLOWED_OUTLIER))}",
                )

    def set_missing_value_strategy(
        self, project_id: UUID | str, column_name: str, strategy: str
    ) -> TransformationConfig:
        project, latest_dataset = self._get_project_and_latest_dataset(project_id)
        col = self._get_column_metadata(latest_dataset.id, column_name)
        self.validate_strategy_for_dtype(col.data_type, missing_strategy=strategy)

        config = self.trans_repo.upsert_config(
            project.id, column_name, {"missing_value_strategy": strategy}
        )
        self._update_pipeline_stage_if_needed(project)
        return config

    def set_encoding_strategy(
        self, project_id: UUID | str, column_name: str, strategy: str
    ) -> TransformationConfig:
        project, latest_dataset = self._get_project_and_latest_dataset(project_id)
        col = self._get_column_metadata(latest_dataset.id, column_name)
        self.validate_strategy_for_dtype(col.data_type, encoding_strategy=strategy)

        config = self.trans_repo.upsert_config(
            project.id, column_name, {"encoding_strategy": strategy}
        )
        self._update_pipeline_stage_if_needed(project)
        return config

    def set_scaling_strategy(
        self, project_id: UUID | str, column_name: str, strategy: str
    ) -> TransformationConfig:
        project, latest_dataset = self._get_project_and_latest_dataset(project_id)
        col = self._get_column_metadata(latest_dataset.id, column_name)
        self.validate_strategy_for_dtype(col.data_type, scaling_strategy=strategy)

        config = self.trans_repo.upsert_config(
            project.id, column_name, {"scaling_strategy": strategy}
        )
        self._update_pipeline_stage_if_needed(project)
        return config

    def set_outlier_strategy(
        self, project_id: UUID | str, column_name: str, strategy: str
    ) -> TransformationConfig:
        project, latest_dataset = self._get_project_and_latest_dataset(project_id)
        col = self._get_column_metadata(latest_dataset.id, column_name)
        self.validate_strategy_for_dtype(col.data_type, outlier_strategy=strategy)

        config = self.trans_repo.upsert_config(
            project.id, column_name, {"outlier_strategy": strategy}
        )
        self._update_pipeline_stage_if_needed(project)
        return config

    def update_column_transformations(
        self, project_id: UUID | str, column_name: str, payload: TransformationConfigUpdate
    ) -> dict:
        project, latest_dataset = self._get_project_and_latest_dataset(project_id)
        col = self._get_column_metadata(latest_dataset.id, column_name)

        # Validate all provided strategies
        self.validate_strategy_for_dtype(
            col.data_type,
            missing_strategy=payload.missing_value_strategy,
            encoding_strategy=payload.encoding_strategy,
            scaling_strategy=payload.scaling_strategy,
            outlier_strategy=payload.outlier_strategy,
        )

        update_dict = {
            k: v
            for k, v in payload.model_dump(exclude_unset=True).items()
            if v is not None
        }

        config = self.trans_repo.upsert_config(project.id, column_name, update_dict)
        self._update_pipeline_stage_if_needed(project)

        return {
            "id": config.id,
            "project_id": project.id,
            "column_name": col.column_name,
            "data_type": col.data_type,
            "missing_value_strategy": config.missing_value_strategy or "none",
            "encoding_strategy": config.encoding_strategy or "none",
            "scaling_strategy": config.scaling_strategy or "none",
            "outlier_strategy": config.outlier_strategy or "none",
            "is_active": config.is_active,
            "created_at": config.created_at,
            "updated_at": config.updated_at,
        }

    def _update_pipeline_stage_if_needed(self, project: Project) -> None:
        if project.pipeline_stage in ["DATA", "DATA_UPLOADED", "SPLIT", "SPLIT_LOCKED", "PROFILED"]:
            project.pipeline_stage = "TRANSFORMED"
            self.db.add(project)
            self.db.commit()

    def _build_column_pipeline(
        self, column_name: str, data_type: str, config: TransformationConfig | None
    ) -> Pipeline | None:
        """
        Builds a fresh, UNFIT scikit-learn Pipeline for a single column.
        """
        if not config or not config.is_active:
            return None

        steps = []
        is_numeric = data_type == "NUMERIC"
        is_categorical = data_type in ["CATEGORICAL", "MIXED"]

        # 1. Missing Value Imputation
        missing_strat = config.missing_value_strategy
        if missing_strat and missing_strat != "none":
            if is_numeric:
                if missing_strat == "mean":
                    steps.append(("imputer", SimpleImputer(strategy="mean")))
                elif missing_strat == "median":
                    steps.append(("imputer", SimpleImputer(strategy="median")))
                elif missing_strat == "arbitrary":
                    steps.append(("imputer", SimpleImputer(strategy="constant", fill_value=0.0)))
                elif missing_strat == "knn":
                    steps.append(("imputer", KNNImputer(n_neighbors=5)))
                elif missing_strat == "iterative":
                    steps.append(("imputer", IterativeImputer(random_state=42)))
            elif is_categorical:
                if missing_strat == "mode":
                    steps.append(("imputer", SimpleImputer(strategy="most_frequent")))
                elif missing_strat == "missing_category":
                    steps.append(("imputer", SimpleImputer(strategy="constant", fill_value="missing")))

        # 2. Outlier Handling (Numeric only)
        outlier_strat = config.outlier_strategy
        if is_numeric and outlier_strat and outlier_strat != "none":
            steps.append(("outlier_capper", OutlierCapper(strategy=outlier_strat)))

        # 3. Scaling (Numeric only)
        scaling_strat = config.scaling_strategy
        if is_numeric and scaling_strat and scaling_strat != "none":
            if scaling_strat == "standard":
                steps.append(("scaler", StandardScaler()))
            elif scaling_strat == "minmax":
                steps.append(("scaler", MinMaxScaler()))
            elif scaling_strat == "robust":
                steps.append(("scaler", RobustScaler()))

        # 4. Encoding (Categorical only)
        encoding_strat = config.encoding_strategy
        if is_categorical and encoding_strat and encoding_strat != "none":
            if encoding_strat == "one_hot":
                steps.append(("encoder", OneHotEncoder(handle_unknown="ignore", sparse_output=False)))
            elif encoding_strat == "ordinal":
                steps.append(("encoder", OrdinalEncoder(handle_unknown="use_encoded_value", unknown_value=-1)))

        if not steps:
            return None

        return Pipeline(steps=steps)

    def build_pipeline(self, project_id: UUID | str) -> ColumnTransformer:
        """
        Reads all active configs for the project and constructs a scikit-learn ColumnTransformer.
        
        ARCHITECTURAL INVARIANT (SRS §2.6 / DFD Process 5):
        - Returns a fresh, **UNFIT** ColumnTransformer template.
        - NEVER returns a pre-fit or cached instance.
        - Day 6/7 cross-validation will instantiate/clone and fit this object on each fold's
          training partition independently to guarantee ZERO test leakage.
        """
        project, latest_dataset = self._get_project_and_latest_dataset(project_id)
        columns = self.dataset_repo.get_columns_by_dataset(latest_dataset.id)
        configs = {c.column_name: c for c in self.trans_repo.get_by_project(project.id)}

        transformers = []
        for col in columns:
            # Check if column is target column or has active transformations
            cfg = configs.get(col.column_name)
            pipe = self._build_column_pipeline(col.column_name, col.data_type, cfg)
            if pipe is not None:
                transformers.append((f"trans_{col.column_name}", pipe, [col.column_name]))

        if not transformers:
            # Passthrough if no column has active transformation steps
            return ColumnTransformer(transformers=[], remainder="passthrough")

        return ColumnTransformer(transformers=transformers, remainder="passthrough")

    def preview_transformation(
        self, project_id: UUID | str, column_name: str, sample_size: int = 50
    ) -> dict:
        """
        Temporary UI preview for transformation feedback.
        
        ARCHITECTURAL INVARIANT (SRS §2.6):
        - Pulls data EXCLUSIVELY via `DatasetSplitService.get_development_data()`.
        - Fits and transforms ONLY this temporary preview slice.
        - DISCARDS the fitted state immediately — nothing is persisted in the database
          or stored in artifacts.
        """
        project, latest_dataset = self._get_project_and_latest_dataset(project_id)
        col_meta = self._get_column_metadata(latest_dataset.id, column_name)
        cfg = self.trans_repo.get_by_project_and_column(project.id, column_name)

        # Load Development partition data exclusively
        dev_df = self.split_service.get_development_data(latest_dataset.id)
        if column_name not in dev_df.columns:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Column '{column_name}' does not exist in Development partition."
            )

        # Slice temporary preview sample
        sample_df = dev_df[[column_name]].head(sample_size).copy()
        raw_values = sample_df[column_name].tolist()

        # Build single-column pipeline
        pipe = self._build_column_pipeline(column_name, col_meta.data_type, cfg)

        if pipe is None:
            # No transformations configured for this column
            transformed_values = raw_values
        else:
            # Temporary fit on preview slice ONLY (discarded after this method completes)
            try:
                # Scikit-learn imputer/encoder expects 2D array or DataFrame
                transformed_arr = pipe.fit_transform(sample_df)
                if hasattr(transformed_arr, "toarray"):
                    transformed_arr = transformed_arr.toarray()
                
                if transformed_arr.ndim == 2 and transformed_arr.shape[1] == 1:
                    transformed_values = transformed_arr.flatten().tolist()
                elif transformed_arr.ndim == 2 and transformed_arr.shape[1] > 1:
                    # One-hot encoded or multi-column expansion
                    transformed_values = transformed_arr.tolist()
                else:
                    transformed_values = list(transformed_arr)
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Failed to preview transformation for column '{column_name}': {str(e)}"
                )

        # Sanitize NaN/Inf for JSON serialization
        def sanitize_val(v: Any) -> Any:
            if v is None:
                return None
            if isinstance(v, (float, np.floating)):
                if np.isnan(v) or np.isinf(v):
                    return None
                return float(v)
            if isinstance(v, (int, np.integer)):
                return int(v)
            if isinstance(v, list):
                return [sanitize_val(item) for item in v]
            return str(v)

        clean_before = [sanitize_val(v) for v in raw_values]
        clean_after = [sanitize_val(v) for v in transformed_values]

        return {
            "column": column_name,
            "sample_size": len(raw_values),
            "data_type": col_meta.data_type,
            "applied_strategies": {
                "missing_value_strategy": cfg.missing_value_strategy if cfg else "none",
                "encoding_strategy": cfg.encoding_strategy if cfg else "none",
                "scaling_strategy": cfg.scaling_strategy if cfg else "none",
                "outlier_strategy": cfg.outlier_strategy if cfg else "none",
            },
            "before_values": clean_before,
            "after_values": clean_after,
        }
