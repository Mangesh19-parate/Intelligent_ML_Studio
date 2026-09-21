from pathlib import Path
import pandas as pd
import pytest

from backend.scripts.run_resource_benchmark import (
    profile_dataset_and_algorithm,
    run_full_resource_benchmark,
)
from sklearn.linear_model import LinearRegression


def test_profile_dataset_and_algorithm():
    df = pd.DataFrame({
        "num1": [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0],
        "cat1": ["a", "b", "a", "b", "a", "b", "a", "b", "a", "b"],
    })
    y = pd.Series([10.0, 20.0, 15.0, 25.0, 12.0, 22.0, 14.0, 24.0, 11.0, 21.0])

    res = profile_dataset_and_algorithm(
        dataset_name="Test Resource Mini",
        dataset_type="SYNTHETIC",
        X=df,
        y=y,
        algorithm_name="LinearRegression",
        model_factory=lambda: LinearRegression(),
        n_splits=2,
    )

    assert res["peak_ram_mb"] > 0
    assert res["artifact_size_mb"] > 0
    assert res["encoded_feature_count"] >= 2
    assert "shap_memory_mb" in res
    assert "shap_time_s" in res


def test_run_full_resource_benchmark_report_content(tmp_path):
    results_df = run_full_resource_benchmark(output_dir=tmp_path)
    assert isinstance(results_df, pd.DataFrame)
    assert len(results_df) >= 3

    csv_file = tmp_path / "benchmark-resources.csv"
    report_file = tmp_path / "benchmark-report.md"

    assert csv_file.exists()
    assert report_file.exists()

    report_text = report_file.read_text(encoding="utf-8")
    # Verify observation-vs-policy requirements in report text
    assert "SHAP Explanation Footprint" in report_text
    assert "Observed Peak RAM" in report_text
    assert "Enforced Policy Cap" in report_text
    assert "Headroom Multiplier" in report_text
    assert "Headroom Rationale & Justification" in report_text
