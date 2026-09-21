import os
from pathlib import Path
import pandas as pd
import pytest

from backend.scripts.run_cv_benchmark import (
    generate_synthetic_small,
    generate_synthetic_medium,
    load_real_stress_dataset,
    benchmark_dataset_and_algorithm,
    run_full_benchmark,
)
from sklearn.linear_model import LinearRegression


def test_synthetic_small_generation():
    X, y = generate_synthetic_small(rows=200, seed=42)
    assert len(X) == 200
    assert len(y) == 200
    assert X.shape[1] == 10
    assert any(col.startswith("num_") for col in X.columns)
    assert any(col.startswith("cat_") for col in X.columns)


def test_synthetic_medium_generation():
    X, y = generate_synthetic_medium(rows=500, seed=42)
    assert len(X) == 500
    assert len(y) == 500
    assert X.shape[1] == 25


def test_benchmark_dataset_and_algorithm_measurement():
    X, y = generate_synthetic_small(rows=100, seed=42)
    res = benchmark_dataset_and_algorithm(
        dataset_name="Test Synthetic",
        dataset_type="SYNTHETIC",
        X=X,
        y=y,
        algorithm_name="LinearRegression",
        model_factory=lambda: LinearRegression(),
        n_splits=5,
    )

    assert res["actual_5fold_cv_time_sec"] > 0
    assert res["transform_time_sec"] > 0
    assert res["one_fold_one_model_time_sec"] > 0
    assert res["estimation_formula"] == "fold_1_time_sec * 5"
    assert "estimation_error_pct" in res
    assert "overhead_sec" in res


def test_run_full_benchmark_creates_artifacts(tmp_path):
    results_df = run_full_benchmark(output_dir=tmp_path)
    assert isinstance(results_df, pd.DataFrame)
    assert len(results_df) >= 3

    csv_file = tmp_path / "benchmark-timing.csv"
    assert csv_file.exists()

    df_loaded = pd.read_csv(csv_file)
    expected_columns = {
        "dataset_name",
        "dataset_type",
        "n_rows",
        "n_features",
        "algorithm",
        "task_type",
        "transform_time_sec",
        "one_fold_one_model_time_sec",
        "actual_5fold_cv_time_sec",
        "estimated_5fold_cv_time_sec",
        "estimation_formula",
        "estimation_error_pct",
        "overhead_sec",
        "timestamp",
    }
    assert expected_columns.issubset(set(df_loaded.columns))
