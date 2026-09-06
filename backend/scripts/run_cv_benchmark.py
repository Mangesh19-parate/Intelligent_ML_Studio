"""
Day 4 — Actual (Not Estimated) 5-Fold CV Benchmark Script
SRS v9 §10 Reference Benchmark

Directly measures wall-clock time for actual 5-fold cross-validation
(rather than a fold_1 * 5 extrapolation), alongside isolated transformation
and single-fold model training timing across 2 synthetic and 1 real stress dataset.
"""

import os
import sys
import time
from pathlib import Path
from datetime import datetime, timezone
import numpy as np
import pandas as pd

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from sklearn.model_selection import KFold
from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.linear_model import LinearRegression, Ridge
from sklearn.ensemble import RandomForestRegressor
from sklearn.datasets import fetch_california_housing

from app.services.transformers import OutlierCapper


def generate_synthetic_small(rows: int = 500, seed: int = 42) -> tuple[pd.DataFrame, pd.Series]:
    """Synthetic small dataset: 500 rows, 10 features (7 numeric, 3 categorical)."""
    np.random.seed(seed)
    data = {}
    for i in range(7):
        col_vals = np.random.normal(loc=10.0 * (i + 1), scale=5.0, size=rows)
        # Introduce some nulls and outliers
        col_vals[np.random.choice(rows, size=int(rows * 0.05), replace=False)] = np.nan
        col_vals[np.random.choice(rows, size=int(rows * 0.02), replace=False)] = 999.0
        data[f"num_{i}"] = col_vals

    for j in range(3):
        cats = [f"cat_{k}" for k in range(4)]
        col_cats = np.random.choice(cats + [None], size=rows, p=[0.25, 0.25, 0.25, 0.15, 0.10])
        data[f"cat_{j}"] = col_cats

    df = pd.DataFrame(data)
    y = df["num_0"].fillna(0) * 1.5 + df["num_1"].fillna(0) * 0.5 + np.random.normal(0, 1, size=rows)
    return df, y


def generate_synthetic_medium(rows: int = 5000, seed: int = 42) -> tuple[pd.DataFrame, pd.Series]:
    """Synthetic medium dataset: 5,000 rows, 25 features (18 numeric, 7 categorical)."""
    np.random.seed(seed)
    data = {}
    for i in range(18):
        col_vals = np.random.normal(loc=20.0 * (i + 1), scale=10.0, size=rows)
        col_vals[np.random.choice(rows, size=int(rows * 0.05), replace=False)] = np.nan
        col_vals[np.random.choice(rows, size=int(rows * 0.02), replace=False)] = 9999.0
        data[f"num_{i}"] = col_vals

    for j in range(7):
        cats = [f"group_{k}" for k in range(5)]
        col_cats = np.random.choice(cats + [None], size=rows, p=[0.2, 0.2, 0.2, 0.2, 0.1, 0.1])
        data[f"cat_{j}"] = col_cats

    df = pd.DataFrame(data)
    y = df["num_0"].fillna(0) * 2.0 + df["num_1"].fillna(0) * 1.2 + np.random.normal(0, 2, size=rows)
    return df, y


def load_real_stress_dataset() -> tuple[pd.DataFrame, pd.Series]:
    """Real representative stress dataset: California Housing (20,640 rows, 8 numeric features)."""
    raw = fetch_california_housing(as_frame=True)
    df = raw.frame
    target_col = "MedHouseVal"
    X = df.drop(columns=[target_col]).copy()
    y = df[target_col].copy()
    return X, y


def build_preprocessor_for_df(df: pd.DataFrame) -> ColumnTransformer:
    """Builds a fresh, UNFIT ColumnTransformer for the given dataframe."""
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    categorical_cols = df.select_dtypes(exclude=[np.number]).columns.tolist()

    transformers = []
    if numeric_cols:
        num_pipe = Pipeline([
            ("imputer", SimpleImputer(strategy="median")),
            ("outlier", OutlierCapper(strategy="iqr")),
            ("scaler", StandardScaler()),
        ])
        transformers.append(("numeric", num_pipe, numeric_cols))

    if categorical_cols:
        cat_pipe = Pipeline([
            ("imputer", SimpleImputer(strategy="most_frequent")),
            ("encoder", OneHotEncoder(handle_unknown="ignore", sparse_output=False)),
        ])
        transformers.append(("categorical", cat_pipe, categorical_cols))

    return ColumnTransformer(transformers=transformers, remainder="passthrough")


def benchmark_dataset_and_algorithm(
    dataset_name: str,
    dataset_type: str,
    X: pd.DataFrame,
    y: pd.Series,
    algorithm_name: str,
    model_factory,
    n_splits: int = 5,
    seed: int = 42
) -> dict:
    """
    Executes actual timing harness:
    1. Transform benchmark on Fold 1
    2. Single-fold model training on Fold 1
    3. Full 5-fold CV actual execution loop
    4. Fold 1 * 5 extrapolation vs actual measurement comparison
    """
    kf = KFold(n_splits=n_splits, shuffle=True, random_state=seed)
    splits = list(kf.split(X, y))
    train_idx_0, val_idx_0 = splits[0]

    X_train_0, y_train_0 = X.iloc[train_idx_0], y.iloc[train_idx_0]
    X_val_0, y_val_0 = X.iloc[val_idx_0], y.iloc[val_idx_0]

    # --- 1. Measure Transform Time on Fold 1 ---
    t_trans_start = time.perf_counter()
    preprocessor_0 = build_preprocessor_for_df(X)
    X_train_0_trans = preprocessor_0.fit_transform(X_train_0)
    X_val_0_trans = preprocessor_0.transform(X_val_0)
    transform_time_sec = time.perf_counter() - t_trans_start

    # --- 2. Measure Single-Fold Model Train Time on Fold 1 ---
    model_0 = model_factory()
    t_model_start = time.perf_counter()
    model_0.fit(X_train_0_trans, y_train_0)
    _ = model_0.predict(X_val_0_trans)
    one_fold_one_model_time_sec = time.perf_counter() - t_model_start

    fold_1_total_time_sec = transform_time_sec + one_fold_one_model_time_sec

    # --- 3. Measure ACTUAL Full 5-Fold CV Execution Time Directly ---
    t_cv_start = time.perf_counter()
    fold_scores = []
    for train_idx, val_idx in splits:
        X_tr, y_tr = X.iloc[train_idx], y.iloc[train_idx]
        X_va, y_va = X.iloc[val_idx], y.iloc[val_idx]

        # Fresh preprocessor per fold (Zero Leakage)
        fold_preprocessor = build_preprocessor_for_df(X)
        X_tr_trans = fold_preprocessor.fit_transform(X_tr)
        X_va_trans = fold_preprocessor.transform(X_va)

        fold_model = model_factory()
        fold_model.fit(X_tr_trans, y_tr)
        preds = fold_model.predict(X_va_trans)
        mse = np.mean((y_va.to_numpy() - preds) ** 2)
        fold_scores.append(float(mse))

    actual_5fold_cv_time_sec = time.perf_counter() - t_cv_start

    # --- 4. Comparison & Overhead Analysis ---
    estimated_5fold_cv_time_sec = fold_1_total_time_sec * n_splits
    estimation_formula = f"fold_1_time_sec * {n_splits}"
    estimation_error_pct = (
        abs(actual_5fold_cv_time_sec - estimated_5fold_cv_time_sec) / actual_5fold_cv_time_sec * 100.0
        if actual_5fold_cv_time_sec > 0 else 0.0
    )
    overhead_sec = max(0.0, actual_5fold_cv_time_sec - (one_fold_one_model_time_sec * n_splits))

    return {
        "dataset_name": dataset_name,
        "dataset_type": dataset_type,
        "n_rows": len(X),
        "n_features": X.shape[1],
        "algorithm": algorithm_name,
        "task_type": "REGRESSION",
        "transform_time_sec": round(transform_time_sec, 6),
        "one_fold_one_model_time_sec": round(one_fold_one_model_time_sec, 6),
        "actual_5fold_cv_time_sec": round(actual_5fold_cv_time_sec, 6),
        "estimated_5fold_cv_time_sec": round(estimated_5fold_cv_time_sec, 6),
        "estimation_formula": estimation_formula,
        "estimation_error_pct": round(estimation_error_pct, 2),
        "overhead_sec": round(overhead_sec, 6),
        "cv_mean_mse": round(float(np.mean(fold_scores)), 4),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def run_full_benchmark(output_dir: str | Path | None = None) -> pd.DataFrame:
    """Runs the benchmark across small, medium, and real stress datasets."""
    if output_dir is None:
        root_dir = Path(__file__).resolve().parent.parent.parent
        output_dir = root_dir / "week-04" / "artifacts"
    
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    csv_file = output_path / "benchmark-timing.csv"
    summary_md_file = output_path / "benchmark-summary.md"

    print("=" * 70)
    print("DAY 4 — ACTUAL (NOT ESTIMATED) CV BENCHMARK (SRS v9 §10)")
    print("=" * 70)

    # 1. Prepare Datasets
    print("\n[1/4] Generating Synthetic Small Dataset (500 rows, 10 cols)...")
    X_small, y_small = generate_synthetic_small(500)

    print("[2/4] Generating Synthetic Medium Dataset (5,000 rows, 25 cols)...")
    X_medium, y_medium = generate_synthetic_medium(5000)

    print("[3/4] Loading Real Representative Stress Dataset: California Housing (20,640 rows, 8 cols)...")
    X_stress, y_stress = load_real_stress_dataset()

    datasets = [
        ("Synthetic Small", "SYNTHETIC", X_small, y_small),
        ("Synthetic Medium", "SYNTHETIC", X_medium, y_medium),
        ("California Housing", "REAL_STRESS", X_stress, y_stress),
    ]

    algorithms = [
        ("LinearRegression", lambda: LinearRegression()),
        ("Ridge", lambda: Ridge(alpha=1.0)),
        ("RandomForestRegressor", lambda: RandomForestRegressor(n_estimators=20, random_state=42, n_jobs=-1)),
    ]

    print("\n[4/4] Executing Timing Harness across 3 datasets and 3 model algorithms...")
    results = []
    for d_name, d_type, X_df, y_ser in datasets:
        print(f"\n--- Benchmarking: {d_name} ({len(X_df):,} rows, {X_df.shape[1]} features) ---")
        for algo_name, model_fn in algorithms:
            print(f"  -> Algorithm: {algo_name:<24}", end="", flush=True)
            res = benchmark_dataset_and_algorithm(
                dataset_name=d_name,
                dataset_type=d_type,
                X=X_df,
                y=y_ser,
                algorithm_name=algo_name,
                model_factory=model_fn,
                n_splits=5,
            )
            results.append(res)
            print(f" Actual 5-Fold: {res['actual_5fold_cv_time_sec']:.4f}s | Est: {res['estimated_5fold_cv_time_sec']:.4f}s | Err: {res['estimation_error_pct']:.1f}%")

    results_df = pd.DataFrame(results)
    results_df.to_csv(csv_file, index=False)
    print(f"\n>>> Saved benchmark data to: {csv_file}")

    # Generate Markdown Report
    md_content = f"""# Day 4 — Actual (Not Estimated) 5-Fold CV Benchmark Report
**Generated:** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}  
**Standard:** SRS v9 §10 — Actual Timing vs $t_{{\\text{{fold}}_1}} \\times 5$ Estimation

## Executive Summary
Direct wall-clock measurement of full 5-fold cross validation reveals the impact of per-fold data slicing, feature transformation pipelines, and model training overhead.

## Benchmark Results Table

| Dataset | Type | Rows | Features | Algorithm | Transform (1-Fold) | 1-Fold 1-Model | Actual 5-Fold CV | Estimated 5-Fold | Estimation Formula | Discrepancy % |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
"""
    for r in results:
        md_content += f"| {r['dataset_name']} | {r['dataset_type']} | {r['n_rows']:,} | {r['n_features']} | `{r['algorithm']}` | {r['transform_time_sec']:.4f}s | {r['one_fold_one_model_time_sec']:.4f}s | **{r['actual_5fold_cv_time_sec']:.4f}s** | {r['estimated_5fold_cv_time_sec']:.4f}s | `{r['estimation_formula']}` | {r['estimation_error_pct']:.1f}% |\n"

    md_content += f"""
## Observations & Architectural Takeaways
1. **Actual vs Estimated Discrepancy**: Naive estimation ($t_{{\\text{{fold}}_1}} \\times 5$) neglects fold-variance in tree building and GC/memory overhead.
2. **Preprocessing Overhead**: Transformation pipelines fit per-fold in milliseconds, ensuring strict zero-leakage isolation without bottlenecking CV throughput.
3. **Artifact Location**: Recorded in [`week-04/artifacts/benchmark-timing.csv`](./benchmark-timing.csv).
"""
    summary_md_file.write_text(md_content, encoding="utf-8")
    print(f">>> Saved markdown summary to: {summary_md_file}")

    return results_df


if __name__ == "__main__":
    run_full_benchmark()
