"""
Dry Run Execution Script for ML Studio Research Track Day 14 (SRS §9).

Executes the FULL experiment matrix across:
- 4 benchmark datasets
- 8 feature selection methods (6 baselines + Method A + Method B)
- 2 repeats (reduced from 8 for dry run)
- 5-fold CV

Total expected row count: 4 * 8 * 2 * 5 = 320 rows in results.db and runs.parquet.
"""

import sys
import time
from pathlib import Path
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
    RESULTS_DB,
    RUNS_PARQUET,
)
from research.experiment_runner import ExperimentRunner
from research.results_store import ResultsStore
from research.stability import compute_selection_stability


def run_full_matrix_dry_run(n_repeats: int = 2) -> pd.DataFrame:
    """
    Executes the dry run across all datasets and methods, exporting results to Parquet.
    """
    print("=" * 80)
    print("ML STUDIO RESEARCH TRACK — FULL MATRIX DRY RUN (DAY 14)")
    print("=" * 80)
    print(f"Datasets ({len(DATASETS)}): {DATASETS}")
    print(f"Methods ({len(METHODS)}): {METHODS}")
    print(f"Repeats: {n_repeats} (reduced dry-run), Folds: {FOLDS}, Total Runs: {len(DATASETS) * len(METHODS) * n_repeats * FOLDS}")
    print(f"Alpha: {ALPHA}, Reference Model: {REFERENCE_MODEL}, Base Seed: {BASE_SEED}")
    print("=" * 80)

    store = ResultsStore(RESULTS_DB)
    # Clear existing records for a fresh dry run
    store.clear()

    start_total = time.perf_counter()
    matrix_count = 0
    total_combinations = len(DATASETS) * len(METHODS)

    for d_idx, dataset in enumerate(DATASETS, start=1):
        print(f"\n[{d_idx}/{len(DATASETS)}] DATASET: {dataset.upper()}")
        print("-" * 60)

        for m_idx, method in enumerate(METHODS, start=1):
            matrix_count += 1
            print(f"  ({matrix_count:02d}/{total_combinations}) Running {method} ...", end="", flush=True)
            m_start = time.perf_counter()

            runner = ExperimentRunner(
                dataset_name=dataset,
                method_name=method,
                n_splits=FOLDS,
                n_repeats=n_repeats,
                seed=BASE_SEED,
                alpha=ALPHA,
                reference_model=REFERENCE_MODEL,
                results_store=store,
            )
            records = runner.run(save_results=True)
            elapsed = time.perf_counter() - m_start
            print(f" Done ({len(records)} folds in {elapsed:.2f}s)")

    total_time = time.perf_counter() - start_total
    print("\n" + "=" * 80)
    print(f"DRY RUN COMPLETED in {total_time:.2f} seconds ({total_time / 60:.2f} minutes)")
    print("=" * 80)

    # Export to Parquet
    parquet_path = store.export_to_parquet(RUNS_PARQUET)
    print(f"Exported Parquet to: {parquet_path}")

    # Load and verify DataFrame
    df_runs = pd.read_parquet(parquet_path)
    print(f"Total rows in runs.parquet: {len(df_runs)}")

    return df_runs


if __name__ == "__main__":
    df = run_full_matrix_dry_run(n_repeats=2)
