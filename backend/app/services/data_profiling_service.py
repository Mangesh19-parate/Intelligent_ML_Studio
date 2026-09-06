from uuid import UUID
from datetime import datetime, timezone
import numpy as np
import pandas as pd
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.models.dataset import Dataset
from app.models.project import Project
from app.models.dataset_split import DatasetSplit
from app.models.profiling_report import ProfilingReport
from app.repositories.dataset_repository import DatasetRepository
from app.repositories.dataset_split_repository import DatasetSplitRepository
from app.repositories.project_repository import ProjectRepository
from app.services.dataset_split_service import DatasetSplitService
from app.services.task_type_service import TaskTypeDetectionService
from app.services.diagnostics_service import DiagnosticsService

class DataProfilingService:
    """
    Data Profiling & Diagnostics Service (SRS §2.3, §2.4 Stage B, §2.16; DFD Process 3).
    
    ARCHITECTURAL INVARIANT (The Sixth Invariant):
    Every computation in this service operates EXCLUSIVELY on the DataFrame returned by
    `DatasetSplitService.get_development_data(dataset_id)`. Raw file paths and the Locked Test
    partition are NEVER accessed.
    """

    DEFAULT_WEIGHTS = {
        "missingness": 0.35,
        "duplicate_rate": 0.25,
        "outlier_prevalence": 0.20,
        "type_consistency": 0.20,
    }

    def __init__(self, db: Session):
        self.db = db
        self.dataset_repo = DatasetRepository(db)
        self.split_repo = DatasetSplitRepository(db)
        self.project_repo = ProjectRepository(db)
        self.split_service = DatasetSplitService(db)
        self.task_type_service = TaskTypeDetectionService(db)
        self.diagnostics_service = DiagnosticsService(db)

    def _infer_series_type(self, series: pd.Series) -> tuple[str, bool]:
        """
        Infers high-level semantic type (numeric, categorical, datetime, boolean)
        and checks for mixed/ambiguous types.
        """
        non_null = series.dropna()
        if len(non_null) == 0:
            return "categorical", False

        if pd.api.types.is_bool_dtype(series):
            return "boolean", False

        if pd.api.types.is_numeric_dtype(series):
            return "numeric", False

        # Try datetime parsing
        if pd.api.types.is_datetime64_any_dtype(series):
            return "datetime", False

        # Inspect non-null elements for mixed/ambiguous types
        # Check if sample strings can be converted to datetime or numeric
        sample = non_null.head(100)
        types_set = set(type(x) for x in sample)
        is_mixed = len(types_set) > 1

        # Check if string column contains mixed numeric and non-numeric values
        if all(isinstance(x, str) for x in sample):
            num_convertible = 0
            for val in sample:
                try:
                    float(val)
                    num_convertible += 1
                except ValueError:
                    pass
            if 0 < num_convertible < len(sample):
                is_mixed = True

        # Check if entire column is datetime strings
        try:
            pd.to_datetime(sample, errors="raise")
            return "datetime", is_mixed
        except Exception:
            pass

        return "categorical", is_mixed

    def _detect_datetime_granularity(self, dt_series: pd.Series) -> str:
        """Detects dominant temporal granularity of a datetime series."""
        try:
            converted = pd.to_datetime(dt_series.dropna())
            if len(converted) < 2:
                return "DAY"
            diffs = converted.sort_values().diff().dropna()
            if len(diffs) == 0:
                return "DAY"
            median_sec = diffs.dt.total_seconds().median()
            if median_sec < 60:
                return "SECOND"
            elif median_sec < 3600:
                return "MINUTE"
            elif median_sec < 86400:
                return "HOUR"
            elif median_sec < 86400 * 7:
                return "DAY"
            elif median_sec < 86400 * 32:
                return "MONTH"
            else:
                return "YEAR"
        except Exception:
            return "DAY"

    def compute_column_stats(self, df: pd.DataFrame) -> dict:
        """
        Computes descriptive statistics per column:
        - Numeric: mean, median, std, skew, min, max, q25, q75, iqr, outlier_count, outlier_pct
        - Categorical: mode, unique_count, top-10 frequency distribution table
        - Datetime: min_date, max_date, detected granularity
        """
        stats: dict = {}
        total_rows = len(df)

        for col in df.columns:
            series = df[col]
            missing_count = int(series.isna().sum())
            missing_pct = round(float((missing_count / total_rows * 100.0) if total_rows > 0 else 0.0), 2)
            unique_count = int(series.nunique(dropna=True))
            
            col_type, is_mixed = self._infer_series_type(series)
            col_stat = {
                "name": col,
                "type": col_type,
                "is_mixed_type": is_mixed,
                "missing_count": missing_count,
                "missing_pct": missing_pct,
                "unique_count": unique_count,
            }

            non_null = series.dropna()

            if col_type == "numeric":
                numeric_s = pd.to_numeric(non_null, errors="coerce").dropna()
                if len(numeric_s) > 0:
                    q25 = float(numeric_s.quantile(0.25))
                    q75 = float(numeric_s.quantile(0.75))
                    iqr = q75 - q25
                    lower_bound = q25 - 1.5 * iqr
                    upper_bound = q75 + 1.5 * iqr
                    outliers = numeric_s[(numeric_s < lower_bound) | (numeric_s > upper_bound)]
                    outlier_count = int(len(outliers))
                    outlier_pct = round(float((outlier_count / len(numeric_s) * 100.0) if len(numeric_s) > 0 else 0.0), 2)
                    
                    skew_val = float(numeric_s.skew()) if len(numeric_s) > 2 else 0.0
                    std_val = float(numeric_s.std()) if len(numeric_s) > 1 else 0.0

                    col_stat.update({
                        "mean": round(float(numeric_s.mean()), 4),
                        "median": round(float(numeric_s.median()), 4),
                        "std": round(std_val, 4) if not np.isnan(std_val) else 0.0,
                        "skew": round(skew_val, 4) if not np.isnan(skew_val) else 0.0,
                        "min": round(float(numeric_s.min()), 4),
                        "max": round(float(numeric_s.max()), 4),
                        "q25": round(q25, 4),
                        "q75": round(q75, 4),
                        "iqr": round(iqr, 4),
                        "outlier_count": outlier_count,
                        "outlier_pct": outlier_pct,
                    })
                else:
                    col_stat.update({
                        "mean": None, "median": None, "std": None, "skew": None,
                        "min": None, "max": None, "q25": None, "q75": None,
                        "iqr": None, "outlier_count": 0, "outlier_pct": 0.0
                    })

            elif col_type == "datetime":
                try:
                    dt_s = pd.to_datetime(non_null)
                    min_dt = dt_s.min()
                    max_dt = dt_s.max()
                    granularity = self._detect_datetime_granularity(dt_s)
                    col_stat.update({
                        "min_date": min_dt.isoformat() if pd.notna(min_dt) else None,
                        "max_date": max_dt.isoformat() if pd.notna(max_dt) else None,
                        "granularity": granularity,
                    })
                except Exception:
                    col_stat.update({
                        "min_date": None,
                        "max_date": None,
                        "granularity": "UNKNOWN",
                    })

            else:  # categorical or boolean
                val_counts = non_null.value_counts().head(10)
                freq_table = [
                    {
                        "value": str(val),
                        "count": int(cnt),
                        "percentage": round(float(cnt / len(non_null) * 100.0), 2)
                    }
                    for val, cnt in val_counts.items()
                ]
                mode_val = str(non_null.mode()[0]) if len(non_null) > 0 and len(non_null.mode()) > 0 else None
                col_stat.update({
                    "mode": mode_val,
                    "frequency_table": freq_table
                })

            stats[col] = col_stat

        return stats

    def compute_correlation_matrix(self, df: pd.DataFrame) -> dict:
        """
        Computes pairwise Pearson correlation matrix for numeric columns only.
        Returns labeled structure: {"columns": [...], "matrix": [[...]]}.
        """
        # Filter strictly to numeric columns
        numeric_cols = [
            c for c in df.columns
            if pd.api.types.is_numeric_dtype(df[c]) and not pd.api.types.is_bool_dtype(df[c])
        ]

        if len(numeric_cols) < 2:
            return {
                "columns": numeric_cols,
                "matrix": [[1.0] if len(numeric_cols) == 1 else []]
            }

        numeric_df = df[numeric_cols].apply(pd.to_numeric, errors="coerce")
        corr = numeric_df.corr(method="pearson")

        # Replace NaN / infinite with None for valid JSON serialization
        matrix = []
        for col_i in numeric_cols:
            row = []
            for col_j in numeric_cols:
                val = corr.loc[col_i, col_j]
                if pd.isna(val) or np.isinf(val):
                    row.append(None)
                else:
                    row.append(round(float(val), 4))
            matrix.append(row)

        return {
            "columns": numeric_cols,
            "matrix": matrix
        }

    def compute_duplicate_count(self, df: pd.DataFrame) -> int:
        """Computes exact duplicate row count across all feature columns (excluding row_uid)."""
        feature_cols = [c for c in df.columns if c != "row_uid"]
        if not feature_cols:
            return 0
        return int(df.duplicated(subset=feature_cols).sum())

    def compute_data_quality_index(self, df: pd.DataFrame, custom_weights: dict | None = None) -> dict:
        """
        Computes the Data Quality Index (DQI) according to SRS §2.3:
        
        1. Missingness Score = 100 - (missing cells / total cells) * 100
        2. Duplicate Rate Score = 100 - (duplicate rows / total rows) * 100
        3. Outlier Prevalence Score = 100 - (IQR-flagged numeric cells / total numeric cells) * 100
           -> if NO numeric columns exist, this sub-score is None ("N/A"), excluded from the
              average, and remaining weights are renormalized to sum to 100%.
        4. Type Consistency Score = 100 - (mixed/ambiguous-dtype columns / total columns) * 100
        
        Overall DQI = weighted average with effective weights recorded.
        """
        total_rows, total_cols = df.shape
        total_cells = total_rows * total_cols

        # 1. Missingness Score
        if total_cells > 0:
            missing_cells = int(df.isna().sum().sum())
            missingness_score = round(float(100.0 - (missing_cells / total_cells) * 100.0), 2)
        else:
            missingness_score = 100.0

        # 2. Duplicate Rate Score
        if total_rows > 0:
            dup_rows = self.compute_duplicate_count(df)
            duplicate_score = round(float(100.0 - (dup_rows / total_rows) * 100.0), 2)
        else:
            duplicate_score = 100.0

        # 3. Outlier Prevalence Score (IQR rule on numeric columns)
        numeric_cols = [
            c for c in df.columns
            if pd.api.types.is_numeric_dtype(df[c]) and not pd.api.types.is_bool_dtype(df[c])
        ]
        
        total_numeric_cells = 0
        total_outlier_cells = 0
        for c in numeric_cols:
            s = pd.to_numeric(df[c], errors="coerce").dropna()
            n_cells = len(s)
            if n_cells > 0:
                total_numeric_cells += n_cells
                q25 = s.quantile(0.25)
                q75 = s.quantile(0.75)
                iqr = q75 - q25
                outliers = s[(s < q25 - 1.5 * iqr) | (s > q75 + 1.5 * iqr)]
                total_outlier_cells += len(outliers)

        if len(numeric_cols) == 0 or total_numeric_cells == 0:
            outlier_score = None
        else:
            outlier_score = round(float(100.0 - (total_outlier_cells / total_numeric_cells) * 100.0), 2)

        # 4. Type Consistency Score
        if total_cols > 0:
            mixed_cols = 0
            for c in df.columns:
                _, is_mixed = self._infer_series_type(df[c])
                if is_mixed:
                    mixed_cols += 1
            type_consistency_score = round(float(100.0 - (mixed_cols / total_cols) * 100.0), 2)
        else:
            type_consistency_score = 100.0

        # Weights & Renormalization
        weights = dict(self.DEFAULT_WEIGHTS)
        if custom_weights:
            weights.update(custom_weights)

        sub_scores = {
            "missingness": missingness_score,
            "duplicate_rate": duplicate_score,
            "outlier_prevalence": outlier_score,
            "type_consistency": type_consistency_score,
        }

        # Calculate effective weights (renormalize if any sub-score is None)
        active_keys = [k for k, score in sub_scores.items() if score is not None]
        active_weight_sum = sum(weights[k] for k in active_keys)

        effective_weights = {}
        weighted_sum = 0.0

        for k in ["missingness", "duplicate_rate", "outlier_prevalence", "type_consistency"]:
            if sub_scores[k] is None:
                effective_weights[k] = None
            else:
                eff_w = weights[k] / active_weight_sum if active_weight_sum > 0 else 0.0
                effective_weights[k] = round(float(eff_w), 4)
                weighted_sum += sub_scores[k] * eff_w

        overall_index = round(float(weighted_sum), 2)

        return {
            "sub_scores": sub_scores,
            "effective_weights": effective_weights,
            "overall_index": overall_index,
        }

    def generate_report(self, dataset_id: UUID | str) -> dict:
        """
        Orchestrates full data profiling pipeline on the Development partition:
        1. Reads Development data via DatasetSplitService.get_development_data
        2. Computes column stats, correlation matrix, duplicate count, and DQI
        3. Persists ProfilingReport linked to DEVELOPMENT dataset_split_id
        4. Updates projects.data_quality_index and projects.pipeline_stage = 'PROFILED'
        5. Executes Stage B Task-Type Detection & Diagnostics Recommendations
        """
        dataset = self.dataset_repo.get_by_id(dataset_id)
        if not dataset:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Dataset not found"
            )

        dev_split = self.split_repo.get_by_dataset_and_type(dataset.id, "DEVELOPMENT")
        if not dev_split:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="No outer split found. Please create an outer split before profiling."
            )

        # 1. Obtain data strictly from get_development_data
        dev_df = self.split_service.get_development_data(dataset.id)
        total_rows, total_cols = dev_df.shape

        # 2. Compute profiling metrics
        column_stats = self.compute_column_stats(dev_df)
        correlation_matrix = self.compute_correlation_matrix(dev_df)
        duplicate_count = self.compute_duplicate_count(dev_df)
        dqi = self.compute_data_quality_index(dev_df)

        # 3. Missingness matrix summary
        missing_by_col = {
            col: stats["missing_count"] for col, stats in column_stats.items()
        }

        # 4. Construct complete report payload
        now = datetime.now(timezone.utc)
        report_data = {
            "dataset_id": str(dataset.id),
            "project_id": str(dataset.project_id),
            "dataset_split_id": str(dev_split.id),
            "total_rows": total_rows,
            "total_columns": total_cols,
            "duplicate_row_count": duplicate_count,
            "column_stats": column_stats,
            "correlation_matrix": correlation_matrix,
            "missingness_summary": {
                "missing_cells_by_column": missing_by_col,
                "total_missing_cells": sum(missing_by_col.values()),
                "total_cells": total_rows * total_cols
            },
            "data_quality_index": dqi,
            "generated_at": now.isoformat(),
        }

        # 5. Persist or update ProfilingReport
        existing_report = (
            self.db.query(ProfilingReport)
            .filter(ProfilingReport.dataset_split_id == dev_split.id)
            .first()
        )
        if existing_report:
            existing_report.report_json = report_data
            existing_report.duplicate_row_count = duplicate_count
            existing_report.generated_at = now
            self.db.add(existing_report)
        else:
            new_report = ProfilingReport(
                dataset_split_id=dev_split.id,
                report_json=report_data,
                duplicate_row_count=duplicate_count,
                generated_at=now
            )
            self.db.add(new_report)

        # 6. Update Project data_quality_index & pipeline_stage
        project = self.project_repo.get_by_id(dataset.project_id)
        if project:
            project.data_quality_index = dqi["overall_index"]
            project.pipeline_stage = "PROFILED"
            self.db.add(project)

        self.db.commit()

        # 7. Execute Stage B Task-Type Detection
        task_type_result = self.task_type_service.suggest_task_type(dataset.id)
        report_data["task_type_suggestion"] = task_type_result

        # 8. Execute Diagnostics & Recommendations Layer
        recommendations = self.diagnostics_service.generate_dqi_recommendations(
            dataset_id=dataset.id,
            column_stats=column_stats,
            dqi_report=dqi,
            duplicate_count=duplicate_count,
            total_rows=total_rows
        )
        report_data["recommendations"] = recommendations

        # Update saved report with task-type suggestion and recommendations
        if existing_report:
            existing_report.report_json = report_data
            self.db.add(existing_report)
        else:
            saved_report = self.db.query(ProfilingReport).filter(ProfilingReport.dataset_split_id == dev_split.id).first()
            if saved_report:
                saved_report.report_json = report_data
                self.db.add(saved_report)
        self.db.commit()

        return report_data

    def get_report(self, dataset_id: UUID | str) -> dict | None:
        """Retrieves stored profiling report for a dataset version."""
        dev_split = self.split_repo.get_by_dataset_and_type(dataset_id, "DEVELOPMENT")
        if not dev_split:
            return None

        report = (
            self.db.query(ProfilingReport)
            .filter(ProfilingReport.dataset_split_id == dev_split.id)
            .first()
        )
        if not report:
            return None

        return report.report_json
