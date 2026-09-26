"""
Preregistered 8-Repeat Empirical Protocol Execution Script (SRS §9, PRE_REGISTRATION.md).

Executes the full frozen protocol:
- 4 Benchmark Datasets
- 8 Feature Selection Methods (6 baselines + Method A + Method B)
- 8 Repeats
- 5 Folds per repeat
Total: 4 * 8 * 8 * 5 = 1,280 runs.
"""

import sys
import time
from pathlib import Path
import pandas as pd

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
from research.statistical_analysis import analyze_research_results


def run_preregistered_8repeat_protocol(n_repeats: int = 8) -> dict:
    print("=" * 80)
    print(f"ML STUDIO RESEARCH TRACK: PREREGISTERED {n_repeats}-REPEAT PROTOCOL EXECUTION")
    print("=" * 80)
    print(f"Datasets: {DATASETS}")
    print(f"Methods: {METHODS}")
    print(f"Repeats: {n_repeats}, Folds: {FOLDS}, Expected Total Runs: {len(DATASETS) * len(METHODS) * n_repeats * FOLDS}")
    print("=" * 80)

    store = ResultsStore(RESULTS_DB)
    store.clear()

    start_total = time.perf_counter()
    matrix_count = 0
    total_combinations = len(DATASETS) * len(METHODS)

    for d_idx, dataset in enumerate(DATASETS, start=1):
        print(f"\n[{d_idx}/{len(DATASETS)}] DATASET: {dataset.upper()}")
        for m_idx, method in enumerate(METHODS, start=1):
            matrix_count += 1
            print(f"  ({matrix_count:02d}/{total_combinations}) Running {method} ({n_repeats} repeats) ...", end="", flush=True)
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
            print(f" Done ({len(records)} runs in {elapsed:.2f}s)")

    total_time = time.perf_counter() - start_total
    print("\n" + "=" * 80)
    print(f"8-REPEAT PROTOCOL RUN COMPLETED in {total_time:.2f} seconds ({total_time / 60:.2f} minutes)")
    print("=" * 80)

    # Export Parquet
    parquet_path = store.export_to_parquet(RUNS_PARQUET)
    print(f"Exported Parquet to: {parquet_path}")

    # Run Statistical Analysis with Holm Correction
    report = analyze_research_results(parquet_path)
    print("Statistical summary with Holm-Bonferroni correction written successfully.")
    return report


if __name__ == "__main__":
    run_preregistered_8repeat_protocol(n_repeats=8)
