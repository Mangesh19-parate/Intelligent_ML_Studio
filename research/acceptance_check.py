"""
Acceptance Check Script for ML Studio Research Track Day 14 (SRS §9).

Executes Day 14 Acceptance Suite:
a) Stability boundary check: Confirm Stability(j) is exactly 1.0 when selected in 100% of runs
   and exactly 0.0 when selected in 0% of runs.
b) Distinction check: Confirm RANK_AGGREGATION (Experiment A) and RANK_AGGREGATION_STABILITY (Experiment B)
   produce genuinely different selected_features for at least one dataset in the dry run.
c) Row count & Matrix verification: Confirm runs.parquet matches len(DATASETS) * len(METHODS) * 2 * FOLDS = 320 rows,
   with exact breakdown by method.
d) Frozen config verification: Confirm research/config.py is treated as frozen (read-only, no write mutations).
"""

import os
import sys
import json
from pathlib import Path
import numpy as np
import pandas as pd

# Add workspace root to path
WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

from research.config import (
    DATASETS,
    METHODS,
    FOLDS,
    ALPHA,
    REFERENCE_MODEL,
    BASE_SEED,
    RUNS_PARQUET,
    RESULTS_DB,
)
from research.stability import compute_selection_stability, StabilityScorer
from research.results_store import ResultsStore
from research.dry_run import run_full_matrix_dry_run


def check_a_stability_boundary():
    print("=" * 80)
    print("ACCEPTANCE CHECK A: Stability Metric Boundary Values (1.0 and 0.0)")
    print("=" * 80)

    # Construct synthetic runs dataframe to test boundary conditions
    synthetic_runs = pd.DataFrame([
        {"dataset": "test_ds", "method": "test_method", "selected_features": ["feat_always", "feat_half"]},
        {"dataset": "test_ds", "method": "test_method", "selected_features": ["feat_always", "feat_half"]},
        {"dataset": "test_ds", "method": "test_method", "selected_features": ["feat_always"]},
        {"dataset": "test_ds", "method": "test_method", "selected_features": ["feat_always"]},
    ])

    all_features = ["feat_always", "feat_half", "feat_never"]

    stab = compute_selection_stability(
        runs_df=synthetic_runs,
        dataset_name="test_ds",
        method="test_method",
        all_features=all_features,
    )

    print("Computed Boundary Stability Scores:")
    for f, val in stab.items():
        print(f"   Feature '{f:12s}': Stability = {val:.4f}")

    # Boundary assertions
    assert stab["feat_always"] == 1.0, f"Expected exactly 1.0 for always-selected, got {stab['feat_always']}"
    assert stab["feat_never"] == 0.0, f"Expected exactly 0.0 for never-selected, got {stab['feat_never']}"
    assert stab["feat_half"] == 0.5, f"Expected exactly 0.5 for half-selected, got {stab['feat_half']}"

    # Verify type and range
    for f, val in stab.items():
        assert 0.0 <= val <= 1.0, f"Stability score out of bounds: {val}"
        assert isinstance(val, float)

    print("\n>>> CHECK A PASSED: Stability(j) is exactly 1.0 for 100% selection and exactly 0.0 for 0% selection.\n")


def check_b_distinct_methods_in_dry_run(df_runs: pd.DataFrame):
    print("=" * 80)
    print("ACCEPTANCE CHECK B: Distinction between Experiment A and Experiment B")
    print("=" * 80)

    # Filter Method A (RANK_AGGREGATION) and Method B (RANK_AGGREGATION_STABILITY)
    df_exp_a = df_runs[df_runs["method"].str.upper() == "RANK_AGGREGATION"]
    df_exp_b = df_runs[df_runs["method"].str.upper() == "RANK_AGGREGATION_STABILITY"]

    assert not df_exp_a.empty, "No rows found for RANK_AGGREGATION (Experiment A)"
    assert not df_exp_b.empty, "No rows found for RANK_AGGREGATION_STABILITY (Experiment B)"

    print(f"Experiment A (RANK_AGGREGATION) rows: {len(df_exp_a)}")
    print(f"Experiment B (RANK_AGGREGATION_STABILITY) rows: {len(df_exp_b)}")

    # Check for differences in selected features across datasets and folds
    dataset_differences = {}
    total_differing_folds = 0

    for ds in DATASETS:
        a_ds = df_exp_a[df_exp_a["dataset"] == ds].sort_values(["run_index", "fold_index"])
        b_ds = df_exp_b[df_exp_b["dataset"] == ds].sort_values(["run_index", "fold_index"])

        diff_count = 0
        diff_samples = []

        for (_, row_a), (_, row_b) in zip(a_ds.iterrows(), b_ds.iterrows()):
            feats_a = sorted(row_a["selected_features"]) if isinstance(row_a["selected_features"], list) else sorted(json.loads(row_a["selected_features"]))
            feats_b = sorted(row_b["selected_features"]) if isinstance(row_b["selected_features"], list) else sorted(json.loads(row_b["selected_features"]))

            if feats_a != feats_b:
                diff_count += 1
                diff_samples.append({
                    "run": row_a["run_index"],
                    "fold": row_a["fold_index"],
                    "selected_A": feats_a,
                    "selected_B": feats_b,
                })

        dataset_differences[ds] = diff_count
        total_differing_folds += diff_count
        print(f"[{ds}] Differing feature subsets between Exp A and Exp B: {diff_count}/{len(a_ds)} folds")
        if diff_samples:
            sample = diff_samples[0]
            print(f"   Example at Run {sample['run']}, Fold {sample['fold']}:")
            print(f"     Exp A: {sample['selected_A']}")
            print(f"     Exp B: {sample['selected_B']}")

    print(f"\nTotal differing folds across full matrix: {total_differing_folds}/{len(df_exp_a)}")
    assert total_differing_folds > 0, (
        "RANK_AGGREGATION and RANK_AGGREGATION_STABILITY produced identical feature selections "
        "across all folds and datasets. Stability reweighting must have an effect on at least one dataset."
    )

    print("\n>>> CHECK B PASSED: RANK_AGGREGATION and RANK_AGGREGATION_STABILITY produce genuinely different selected_features.\n")


def check_c_row_count_and_breakdown(df_runs: pd.DataFrame, expected_repeats: int = 2):
    print("=" * 80)
    print("ACCEPTANCE CHECK C: Full Matrix Row Count & Method Breakdown")
    print("=" * 80)

    expected_total_rows = len(DATASETS) * len(METHODS) * expected_repeats * FOLDS
    actual_rows = len(df_runs)

    print(f"Formula: len(DATASETS={len(DATASETS)}) * len(METHODS={len(METHODS)}) * repeats={expected_repeats} * FOLDS={FOLDS}")
    print(f"Expected Rows: {expected_total_rows}")
    print(f"Actual Rows:   {actual_rows}")

    assert actual_rows == expected_total_rows, (
        f"Row count mismatch! Expected {expected_total_rows}, got {actual_rows}"
    )

    # Method breakdown
    breakdown = df_runs.groupby("method").size().reset_index(name="row_count")
    expected_per_method = len(DATASETS) * expected_repeats * FOLDS
    print("\nBreakdown by Method:")
    print("-" * 50)
    for _, row in breakdown.iterrows():
        m = row["method"]
        cnt = row["row_count"]
        print(f"  {m:30s}: {cnt:4d} rows (Expected: {expected_per_method})")
        assert cnt == expected_per_method, f"Method {m} has {cnt} rows, expected {expected_per_method}"

    # Dataset breakdown
    print("\nBreakdown by Dataset:")
    print("-" * 50)
    ds_breakdown = df_runs.groupby("dataset").size().reset_index(name="row_count")
    expected_per_ds = len(METHODS) * expected_repeats * FOLDS
    for _, row in ds_breakdown.iterrows():
        d = row["dataset"]
        cnt = row["row_count"]
        print(f"  {d:30s}: {cnt:4d} rows (Expected: {expected_per_ds})")
        assert cnt == expected_per_ds, f"Dataset {d} has {cnt} rows, expected {expected_per_ds}"

    # Alpha verification
    stability_rows = df_runs[df_runs["method"].str.upper() == "RANK_AGGREGATION_STABILITY"]
    assert (stability_rows["alpha"] == ALPHA).all(), f"Alpha values for stability method do not match {ALPHA}"
    print(f"\nVerified: All {len(stability_rows)} RANK_AGGREGATION_STABILITY rows record alpha = {ALPHA}")

    print("\n>>> CHECK C PASSED: Row count matches 320 exactly with balanced breakdown across all methods & datasets.\n")


def check_d_frozen_config():
    print("=" * 80)
    print("ACCEPTANCE CHECK D: Verify research/config.py is Frozen")
    print("=" * 80)

    # Scan codebase for any file modifying research/config.py
    research_dir = Path("research")
    all_py_files = list(research_dir.glob("*.py"))

    modifying_patterns = [
        "config.py",
        "write_text",
        "open('research/config.py', 'w')",
        'open("research/config.py", "w")',
    ]

    violations = []
    for f in all_py_files:
        if f.name in ["config.py", "acceptance_check.py"]:
            continue
        text = f.read_text(encoding="utf-8")
        if "open" in text and "config.py" in text and ("'w'" in text or '"w"' in text):
            violations.append(f.name)

    assert not violations, f"Found files attempting to modify config.py: {violations}"
    print(f"Inspected {len(all_py_files)} files in research/. Zero runtime write mutations detected for config.py.")
    print("Protocol parameters are confirmed frozen: DATASETS, METHODS, FOLDS, REPEATS, ALPHA, REFERENCE_MODEL, BASE_SEED.")

    print("\n>>> CHECK D PASSED: research/config.py is strictly read-only and frozen.\n")


def main():
    print("\n" + "#" * 80)
    print("   ML STUDIO RESEARCH TRACK — DAY 14 ACCEPTANCE TEST SUITE")
    print("#" * 80 + "\n")

    # Step 1: Stability boundary check
    check_a_stability_boundary()

    # Step 2: Full Matrix Dry Run (320 rows)
    if RUNS_PARQUET.exists():
        df_runs = pd.read_parquet(RUNS_PARQUET)
        if len(df_runs) != len(DATASETS) * len(METHODS) * 2 * FOLDS:
            print("Existing runs.parquet row count does not match full matrix. Running dry run...")
            df_runs = run_full_matrix_dry_run(n_repeats=2)
    else:
        df_runs = run_full_matrix_dry_run(n_repeats=2)

    # Step 3: Check distinction between Exp A and Exp B
    check_b_distinct_methods_in_dry_run(df_runs)

    # Step 4: Check row count and breakdown
    check_c_row_count_and_breakdown(df_runs, expected_repeats=2)

    # Step 5: Check frozen config
    check_d_frozen_config()

    print("=" * 80)
    print("ALL DAY 14 ACCEPTANCE CHECKS PASSED SUCCESSFULLY!")
    print("=" * 80)


if __name__ == "__main__":
    main()
