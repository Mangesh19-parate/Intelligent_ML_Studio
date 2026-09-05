"""
Results Store for ML Studio Research Track (SRS §9).

Lightweight SQLite & Parquet persistence for feature selection experiment records.
Stores one row per (dataset, method, run, fold) combination.

SCHEMA:
- dataset (TEXT)
- method (TEXT)
- run_index (INTEGER)
- fold_index (INTEGER)
- cv_metric_name (TEXT)
- cv_metric_value (REAL)
- selected_features (TEXT, JSON array)
- runtime_seconds (REAL)
- alpha (REAL)
- timestamp (TEXT, ISO 8601)
"""

from contextlib import contextmanager
from datetime import datetime, timezone
import json
from pathlib import Path
import sqlite3
from typing import Any
import pandas as pd

DEFAULT_DB_PATH = Path(__file__).parent / "results.db"


class ResultsStore:
    """
    Lightweight SQLite storage engine for experimental CV evaluations.
    Completely isolated from the platform's production PostgreSQL database.
    """

    def __init__(self, db_path: str | Path = DEFAULT_DB_PATH):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    @contextmanager
    def _get_connection(self):
        conn = sqlite3.connect(str(self.db_path))
        try:
            yield conn
        finally:
            conn.close()

    def _init_db(self) -> None:
        with self._get_connection() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS experiment_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    dataset TEXT NOT NULL,
                    method TEXT NOT NULL,
                    run_index INTEGER NOT NULL,
                    fold_index INTEGER NOT NULL,
                    cv_metric_name TEXT NOT NULL,
                    cv_metric_value REAL NOT NULL,
                    selected_features TEXT NOT NULL,
                    runtime_seconds REAL NOT NULL,
                    alpha REAL,
                    timestamp TEXT NOT NULL
                );
                """
            )
            # Add alpha column if migrating from earlier schema
            cursor = conn.cursor()
            cursor.execute("PRAGMA table_info(experiment_results)")
            columns = [col[1] for col in cursor.fetchall()]
            if "alpha" not in columns:
                conn.execute("ALTER TABLE experiment_results ADD COLUMN alpha REAL")

            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_dataset_method
                ON experiment_results (dataset, method);
                """
            )
            conn.commit()

    def save_result(
        self,
        dataset: str,
        method: str,
        run_index: int,
        fold_index: int,
        cv_metric_name: str,
        cv_metric_value: float,
        selected_features: list[str] | str,
        runtime_seconds: float,
        alpha: float | None = None,
        timestamp: str | None = None,
    ) -> int:
        """
        Saves a single CV fold experiment record.
        """
        if isinstance(selected_features, (list, tuple)):
            features_json = json.dumps(list(selected_features))
        else:
            features_json = str(selected_features)

        ts = timestamp or datetime.now(timezone.utc).isoformat()

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO experiment_results (
                    dataset, method, run_index, fold_index,
                    cv_metric_name, cv_metric_value,
                    selected_features, runtime_seconds, alpha, timestamp
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    dataset,
                    method,
                    run_index,
                    fold_index,
                    cv_metric_name,
                    float(cv_metric_value),
                    features_json,
                    float(runtime_seconds),
                    float(alpha) if alpha is not None else None,
                    ts,
                ),
            )
            conn.commit()
            return cursor.lastrowid

    def save_batch(self, records: list[dict[str, Any]]) -> int:
        """
        Saves a list of record dicts in a single transaction.
        """
        if not records:
            return 0

        rows = []
        now_iso = datetime.now(timezone.utc).isoformat()
        for r in records:
            feats = r["selected_features"]
            if isinstance(feats, (list, tuple)):
                features_json = json.dumps(list(feats))
            else:
                features_json = str(feats)

            alpha_val = r.get("alpha")
            if alpha_val is not None:
                alpha_val = float(alpha_val)

            rows.append(
                (
                    r["dataset"],
                    r["method"],
                    int(r["run_index"]),
                    int(r["fold_index"]),
                    r["cv_metric_name"],
                    float(r["cv_metric_value"]),
                    features_json,
                    float(r["runtime_seconds"]),
                    alpha_val,
                    r.get("timestamp", now_iso),
                )
            )

        with self._get_connection() as conn:
            conn.executemany(
                """
                INSERT INTO experiment_results (
                    dataset, method, run_index, fold_index,
                    cv_metric_name, cv_metric_value,
                    selected_features, runtime_seconds, alpha, timestamp
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                rows,
            )
            conn.commit()
        return len(rows)

    def get_results(
        self, dataset: str | None = None, method: str | None = None
    ) -> pd.DataFrame:
        """
        Fetches experiment results as a pandas DataFrame.
        """
        query = "SELECT dataset, method, run_index, fold_index, cv_metric_name, cv_metric_value, selected_features, runtime_seconds, alpha, timestamp FROM experiment_results"
        params = []
        conditions = []

        if dataset is not None:
            conditions.append("dataset = ?")
            params.append(dataset)
        if method is not None:
            conditions.append("method = ?")
            params.append(method)

        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        query += " ORDER BY dataset, method, run_index, fold_index"

        with self._get_connection() as conn:
            df = pd.read_sql_query(query, conn, params=params)

        return df

    def get_summary(self) -> pd.DataFrame:
        """
        Produces aggregated summary metrics per (dataset, method).
        """
        df = self.get_results()
        if df.empty:
            return pd.DataFrame(
                columns=[
                    "dataset",
                    "method",
                    "cv_metric_name",
                    "mean_metric",
                    "std_metric",
                    "mean_runtime_sec",
                    "folds_count",
                ]
            )

        summary = (
            df.groupby(["dataset", "method", "cv_metric_name"])
            .agg(
                mean_metric=("cv_metric_value", "mean"),
                std_metric=("cv_metric_value", "std"),
                mean_runtime_sec=("runtime_seconds", "mean"),
                folds_count=("cv_metric_value", "count"),
            )
            .reset_index()
        )
        return summary

    def clear(self, dataset: str | None = None, method: str | None = None) -> int:
        """
        Clears results matching the filter, or all results if no filter provided.
        """
        query = "DELETE FROM experiment_results"
        params = []
        conditions = []
        if dataset is not None:
            conditions.append("dataset = ?")
            params.append(dataset)
        if method is not None:
            conditions.append("method = ?")
            params.append(method)

        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            deleted = cursor.rowcount
            conn.commit()
            return deleted

    def export_to_parquet(self, parquet_path: str | Path | None = None) -> Path:
        """
        Exports the results table to a Parquet file.
        """
        target = Path(parquet_path) if parquet_path else self.db_path.with_suffix(".parquet")
        df = self.get_results()
        df.to_parquet(target, index=False)
        return target
