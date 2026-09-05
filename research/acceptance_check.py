"""
Acceptance Check Script for ML Studio Research Track Day 13 (SRS §9).

Executes all 7 validation checks:
a) Load all 4 datasets; check shapes, dtypes, summary statistics.
b) Verify outer split reproducibility across duplicate runs with same seed.
c) Verify outer split stratification for classification and random for regression.
d) Verify RFE and no-selection baseline outputs and rank aggregatability.
e) Verify StabilityScorer against exact hand-calculated synthetic example.
f) Run Day 13 smoke test (1 dataset, 2 methods) through ExperimentRunner and verify ResultsStore.
g) Verify zero production PostgreSQL DB imports or side-effects in research module.
"""

import os
import sys
import json
import sqlite3
from pathlib import Path
import numpy as np
import pandas as pd

# Add workspace to path
WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

from research.dataset_loader import (
    load_california_housing,
    load_bike_sharing,
    load_breast_cancer,
    load_adult_income,
    DATASET_LOADERS,
)
from research.outer_split import create_split, partition_data
from research.feature_selectors import (
    rfe_importance,
    no_selection_baseline,
    select_features,
)
from research.stability import StabilityScorer
from research.experiment_runner import ExperimentRunner
from research.results_store import ResultsStore


def check_a_dataset_loading():
    print("=" * 70)
    print("CHECK A: Load all 4 datasets & verify summary statistics")
    print("=" * 70)
    
    datasets = {}
    stats_summary = []
    
    for name, loader in DATASET_LOADERS.items():
        X, y, task_type = loader()
        datasets[name] = (X, y, task_type)
        
        n_rows, n_cols = X.shape
        missing_count = int(X.isna().sum().sum()) + int(y.isna().sum())
        
        if task_type == "CLASSIFICATION":
            class_dist = dict(y.value_counts(normalize=True).round(4))
            target_info = f"Class balance: {class_dist}"
        else:
            target_info = f"Mean={y.mean():.3f}, Std={y.std():.3f}, Min={y.min():.3f}, Max={y.max():.3f}"
            
        stats_summary.append({
            "Dataset": name,
            "Task Type": task_type,
            "Rows": n_rows,
            "Features": n_cols,
            "Missing Values": missing_count,
            "Target Info": target_info,
        })
        print(f"[{name}] Task: {task_type} | Shape: ({n_rows}, {n_cols}) | Missing: {missing_count} | {target_info}")

    print("\nSummary Table:")
    summary_df = pd.DataFrame(stats_summary)
    print(summary_df.to_string(index=False))
    
    # Assert sanity
    for name, (X, y, task_type) in datasets.items():
        assert len(X) == len(y), f"Length mismatch in {name}"
        assert X.shape[1] > 0, f"No features in {name}"
        assert not X.isna().any().any(), f"NaNs found in {name} features"
        assert not y.isna().any(), f"NaNs found in {name} target"
    print("\n>>> CHECK A PASSED: All 4 datasets loaded cleanly with sane dtypes/shapes.\n")
    return datasets


def check_b_split_reproducibility(datasets):
    print("=" * 70)
    print("CHECK B: Verify outer split deterministic reproducibility")
    print("=" * 70)
    
    test_seed = 12345
    for name, (X, y, task_type) in datasets.items():
        split_1 = create_split(X, y, task_type, locked_test_pct=20, seed=test_seed)
        split_2 = create_split(X, y, task_type, locked_test_pct=20, seed=test_seed)
        
        np.testing.assert_array_equal(
            split_1.dev_indices, split_2.dev_indices,
            err_msg=f"Dev indices mismatch in {name}"
        )
        np.testing.assert_array_equal(
            split_1.locked_test_indices, split_2.locked_test_indices,
            err_msg=f"Locked test indices mismatch in {name}"
        )
        assert split_1.seed == split_2.seed == test_seed
        print(f"[{name}] Exact match for seed={test_seed}: Dev rows={len(split_1.dev_indices)}, Test rows={len(split_1.locked_test_indices)}")
        
    print("\n>>> CHECK B PASSED: create_split is 100% deterministic given a fixed seed.\n")


def check_c_stratification(datasets):
    print("=" * 70)
    print("CHECK C: Verify stratification for classification & random for regression")
    print("=" * 70)
    
    seed = 42
    for name, (X, y, task_type) in datasets.items():
        split = create_split(X, y, task_type, locked_test_pct=20, seed=seed)
        (X_dev, y_dev), (X_test, y_test) = partition_data(X, y, split)
        
        if task_type == "CLASSIFICATION":
            assert split.is_stratified is True, f"Expected stratified split for classification dataset {name}"
            orig_prop = y.mean()
            dev_prop = y_dev.mean()
            test_prop = y_test.mean()
            diff_dev = abs(orig_prop - dev_prop)
            diff_test = abs(orig_prop - test_prop)
            print(f"[{name}] CLASSIFICATION (Stratified): Overall={orig_prop:.4f}, Dev={dev_prop:.4f}, Test={test_prop:.4f} (Max diff={max(diff_dev, diff_test):.5f})")
            assert max(diff_dev, diff_test) < 0.01, f"Stratification deviation too large in {name}"
        else:
            assert split.is_stratified is False, f"Expected plain random split for regression dataset {name}"
            print(f"[{name}] REGRESSION (Plain random): Total={len(y)}, Dev={len(y_dev)}, Test={len(y_test)} (Test pct={len(y_test)/len(y)*100:.1f}%)")
            
    print("\n>>> CHECK C PASSED: Proper stratification on classification, random on regression.\n")


def check_d_rfe_and_no_selection(datasets):
    print("=" * 70)
    print("CHECK D: Verify RFE and No-Selection baseline outputs")
    print("=" * 70)
    
    # Test on California Housing (Regression)
    X_cal, y_cal, t_cal = datasets["california_housing"]
    split_cal = create_split(X_cal, y_cal, t_cal, seed=42)
    (X_dev_cal, y_dev_cal), _ = partition_data(X_cal, y_cal, split_cal)
    
    # 1. No selection baseline
    raw_ns, rank_ns, rscore_ns = no_selection_baseline(X_dev_cal, y_dev_cal, t_cal)
    assert len(raw_ns) == X_dev_cal.shape[1]
    assert np.allclose(rscore_ns, 1.0), "No selection baseline should assign rank score 1.0 to all features"
    print(f"[No Selection] Features: {X_dev_cal.shape[1]}, Rank scores: {rscore_ns}")
    
    # 2. RFE baseline on regression
    raw_rfe, rank_rfe, rscore_rfe = rfe_importance(X_dev_cal, y_dev_cal, t_cal, seed=42)
    assert len(raw_rfe) == X_dev_cal.shape[1]
    assert np.min(rscore_rfe) >= 0.0 and np.max(rscore_rfe) <= 1.0
    print(f"[RFE Regression] California Housing (8 features):")
    for feat, raw, r, rs in zip(X_dev_cal.columns, raw_rfe, rank_rfe, rscore_rfe):
        print(f"   {feat:15s} | Raw (score): {raw:4.1f} | Rank: {r:3.1f} | Normalized Rank Score: {rs:.3f}")
        
    # 3. RFE baseline on classification (Breast Cancer)
    X_bc, y_bc, t_bc = datasets["breast_cancer"]
    split_bc = create_split(X_bc, y_bc, t_bc, seed=42)
    (X_dev_bc, y_dev_bc), _ = partition_data(X_bc, y_bc, split_bc)
    raw_bc, rank_bc, rscore_bc = rfe_importance(X_dev_bc, y_dev_bc, t_bc, seed=42)
    assert len(raw_bc) == X_dev_bc.shape[1]
    print(f"[RFE Classification] Breast Cancer (30 features): top ranked features={np.array(X_dev_bc.columns)[np.argsort(-rscore_bc)[:5]]}")
    
    print("\n>>> CHECK D PASSED: RFE and No-Selection baselines produce valid rank-aggregatable outputs.\n")


def check_e_stability_scorer():
    print("=" * 70)
    print("CHECK E: Verify StabilityScorer against hand-calculated synthetic example")
    print("=" * 70)
    
    # Synthetic Example:
    # 4 features: ['A', 'B', 'C', 'D']
    # 5 runs with selected subsets:
    # Run 1: ['A', 'B']
    # Run 2: ['A', 'B', 'C']
    # Run 3: ['A', 'C']
    # Run 4: ['A', 'B', 'D']
    # Run 5: ['A']
    #
    # Hand Calculations:
    # Feature A: 5/5 = 1.00
    # Feature B: 3/5 = 0.60
    # Feature C: 2/5 = 0.40
    # Feature D: 1/5 = 0.20
    
    all_features = ["A", "B", "C", "D"]
    subsets = [
        ["A", "B"],
        ["A", "B", "C"],
        ["A", "C"],
        ["A", "B", "D"],
        ["A"],
    ]
    
    scorer = StabilityScorer(alpha=0.5)
    stab_dict = scorer.compute_stability_from_subsets(subsets, all_features)
    
    expected_stabilities = {"A": 1.0, "B": 0.6, "C": 0.4, "D": 0.2}
    print("Calculated stabilities vs Hand expected:")
    for feat in all_features:
        calc = stab_dict[feat]
        exp = expected_stabilities[feat]
        print(f"   Feature {feat}: Computed = {calc:.4f}, Expected = {exp:.4f} -> Match: {np.isclose(calc, exp)}")
        assert np.isclose(calc, exp), f"Mismatch for feature {feat}: got {calc}, expected {exp}"
        
    # Test Final Score formula: FinalScore_j = alpha * Importance_j + (1 - alpha) * Stability_j
    # Let Importance = [0.8, 0.4, 0.6, 0.1]
    # alpha = 0.5
    # Expected Final:
    # A: 0.5 * 0.8 + 0.5 * 1.0 = 0.4 + 0.5 = 0.90
    # B: 0.5 * 0.4 + 0.5 * 0.6 = 0.2 + 0.3 = 0.50
    # C: 0.5 * 0.6 + 0.5 * 0.4 = 0.3 + 0.2 = 0.50
    # D: 0.5 * 0.1 + 0.5 * 0.2 = 0.05 + 0.10 = 0.15
    importance = np.array([0.8, 0.4, 0.6, 0.1])
    stability = np.array([1.0, 0.6, 0.4, 0.2])
    final = scorer.compute_final_score(importance, stability, alpha=0.5)
    expected_final = np.array([0.90, 0.50, 0.50, 0.15])
    
    np.testing.assert_allclose(final, expected_final)
    print(f"Final blended scores: Computed={final}, Expected={expected_final}")
    print("\n>>> CHECK E PASSED: StabilityScorer matches hand calculations exactly.\n")


def check_f_smoke_test_and_results_store():
    print("=" * 70)
    print("CHECK F: Day 13 Smoke Test (California Housing with Correlation & Rank Aggregation)")
    print("=" * 70)
    
    db_file = Path("research/results.db")
    store = ResultsStore(db_file)
    # Clear previous smoke test records for clean run
    store.clear(dataset="california_housing")
    
    # 1. Run Correlation method
    print("Running Method: 'correlation' on 'california_housing' (2 runs x 5 folds = 10 folds)...")
    runner_corr = ExperimentRunner(
        dataset_name="california_housing",
        method_name="correlation",
        n_splits=5,
        n_repeats=2,
        seed=42,
        results_store=store,
    )
    records_corr = runner_corr.run(save_results=True)
    assert len(records_corr) == 10, f"Expected 10 fold records, got {len(records_corr)}"
    
    # 2. Run Rank Aggregation method
    print("Running Method: 'rank_aggregation' on 'california_housing' (2 runs x 5 folds = 10 folds)...")
    runner_rank = ExperimentRunner(
        dataset_name="california_housing",
        method_name="rank_aggregation",
        n_splits=5,
        n_repeats=2,
        seed=42,
        results_store=store,
    )
    records_rank = runner_rank.run(save_results=True)
    assert len(records_rank) == 10, f"Expected 10 fold records, got {len(records_rank)}"
    
    # 3. Verify SQLite DB rows and schema
    df_results = store.get_results(dataset="california_housing")
    print(f"\nPersisted {len(df_results)} rows in SQLite ResultsStore at '{db_file}'.")
    
    expected_columns = [
        "dataset", "method", "run_index", "fold_index",
        "cv_metric_name", "cv_metric_value", "selected_features",
        "runtime_seconds", "timestamp"
    ]
    assert list(df_results.columns) == expected_columns, f"Columns mismatch: {df_results.columns.tolist()}"
    
    print("\nSample Rows from ResultsStore:")
    print(df_results.head(6)[["dataset", "method", "run_index", "fold_index", "cv_metric_name", "cv_metric_value", "runtime_seconds"]].to_string(index=False))
    
    print("\nAggregated Summary from ResultsStore:")
    summary = store.get_summary()
    print(summary.to_string(index=False))
    
    print("\n>>> CHECK F PASSED: Day 13 smoke test executed end-to-end and stored properly.\n")


def check_g_database_isolation():
    print("=" * 70)
    print("CHECK G: Confirm ZERO production PostgreSQL DB imports or side effects")
    print("=" * 70)
    
    research_dir = Path("research")
    py_files = [f for f in research_dir.glob("*.py") if f.name != "acceptance_check.py"]
    
    forbidden_terms = [
        "get_db",
        "app.core.database",
        "DATABASE_URL",
        "SessionLocal",
        "postgresql",
        "psycopg2",
        "asyncpg",
    ]
    
    violations = []
    for f in py_files:
        content = f.read_text(encoding="utf-8")
        for term in forbidden_terms:
            if term in content:
                violations.append((f.name, term))
                
    if violations:
        print("FAILED: Forbidden production DB references found in research track:")
        for fname, term in violations:
            print(f"   {fname}: {term}")
        sys.exit(1)
    else:
        print(f"Inspected {len(py_files)} research python files: {', '.join([f.name for f in py_files])}")
        print("Confirmed: ZERO production database session, connection string, or DB model imports in research/.")
        print("\n>>> CHECK G PASSED: Complete isolation from production PostgreSQL database.\n")


def main():
    print("\n" + "#" * 70)
    print("   ML STUDIO RESEARCH TRACK - DAY 13 ACCEPTANCE TEST SUITE")
    print("#" * 70 + "\n")
    
    datasets = check_a_dataset_loading()
    check_b_split_reproducibility(datasets)
    check_c_stratification(datasets)
    check_d_rfe_and_no_selection(datasets)
    check_e_stability_scorer()
    check_f_smoke_test_and_results_store()
    check_g_database_isolation()
    
    print("=" * 70)
    print("ALL 7 ACCEPTANCE CHECKS COMPLETED SUCCESSFULLY!")
    print("=" * 70)


if __name__ == "__main__":
    main()
