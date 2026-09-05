"""
Day 15 — Research Track: Full Runs, Regression Datasets (SRS §9).

Executes the full experimental protocol on regression benchmark datasets:
- Datasets: California Housing, Bike Sharing (Regression)
- 8 Methods: NO_SELECTION, CORRELATION, LASSO, RANDOM_FOREST, PERMUTATION, RFE,
             RANK_AGGREGATION, RANK_AGGREGATION_STABILITY
- 8 Repeats × 5 Folds = 40 folds per method per dataset (Total 640 rows)
- Seed: BASE_SEED + repeat_index (1000 to 1007)
- Computes CV metrics, feature selection stability, and summary metrics.
- Evaluates Locked Test partition strictly ONCE each for proposed methods (RANK_AGGREGATION and RANK_AGGREGATION_STABILITY).
- Generates:
    * research/runs.parquet (640 rows)
    * research/results/regression_summary.parquet
    * research/results/locked_test_regression.parquet
    * research/results/locked_test_consumed.json
"""

import sys
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import numpy as np
import pandas as pd
from sklearn.metrics import mean_squared_error
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestRegressor

# Workspace root
WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

from research.config import (
    DATASETS,
    METHODS,
    FOLDS,
    REPEATS,
    ALPHA,
    REFERENCE_MODEL,
    BASE_SEED,
    RESULTS_DB,
    RUNS_PARQUET,
    RESEARCH_DIR,
)
from research.dataset_loader import load_dataset
from research.outer_split import create_split, partition_data
from research.feature_selectors import (
    select_features,
    rank_aggregation_ensemble,
    _resolve_k,
)
from research.experiment_runner import ResearchExperimentRunner
from research.results_store import ResultsStore
from research.stability import compute_selection_stability, StabilityScorer
from app.services.feature_selection_service import FeatureSelectionService

RESULTS_DIR = RESEARCH_DIR / "results"
REGRESSION_SUMMARY_PARQUET = RESULTS_DIR / "regression_summary.parquet"
LOCKED_TEST_REGRESSION_PARQUET = RESULTS_DIR / "locked_test_regression.parquet"
LOCKED_TEST_CONSUMED_JSON = RESULTS_DIR / "locked_test_consumed.json"


# -----------------------------------------------------------------------------
# Locked Test Access Logger & Audit Tracker
# -----------------------------------------------------------------------------
class LockedTestAccessTracker:
    """
    Strict audit log to ensure Locked Test partitions are accessed at most 2 times
    per dataset (once for RANK_AGGREGATION and once for RANK_AGGREGATION_STABILITY).
    """

    def __init__(self):
        self.access_log: list[dict[str, Any]] = []

    def get_locked_test_data(
        self,
        dataset_name: str,
        method_name: str,
        X_test: pd.DataFrame,
        y_test: pd.Series,
    ) -> tuple[pd.DataFrame, pd.Series]:
        norm_method = method_name.upper().strip()
        allowed_methods = ["RANK_AGGREGATION", "RANK_AGGREGATION_STABILITY"]
        if norm_method not in allowed_methods:
            raise PermissionError(
                f"LOCKED TEST ACCESS DENIED: Baseline method '{method_name}' is not permitted "
                f"to access Locked Test. Only proposed methods {allowed_methods} are authorized."
            )

        # Count prior accesses for this dataset
        prior_calls = [
            r for r in self.access_log if r["dataset"] == dataset_name and r["method"] == norm_method
        ]
        if len(prior_calls) > 0:
            raise PermissionError(
                f"LOCKED TEST ACCESS DENIED: Dataset '{dataset_name}' method '{norm_method}' "
                f"has already consumed its one-time Locked Test evaluation quota."
            )

        timestamp = datetime.now(timezone.utc).isoformat()
        self.access_log.append({
            "dataset": dataset_name,
            "method": norm_method,
            "timestamp": timestamp,
            "rows_accessed": len(X_test),
        })
        print(f"   [LOCKED TEST ACCESS] Dataset: {dataset_name} | Method: {norm_method} | Rows: {len(X_test)} | Timestamp: {timestamp}")
        return X_test, y_test

    def verify_access_counts(self, regression_datasets: list[str]) -> None:
        print("\n" + "=" * 80)
        print("LOCKED TEST ACCESS AUDIT VERIFICATION")
        print("=" * 80)
        for ds in regression_datasets:
            ds_calls = [r for r in self.access_log if r["dataset"] == ds]
            print(f"Dataset '{ds}': Total Locked Test accesses = {len(ds_calls)}")
            for c in ds_calls:
                print(f"   - Method: {c['method']} at {c['timestamp']}")
            assert len(ds_calls) <= 2, f"VIOLATION: Dataset '{ds}' was accessed {len(ds_calls)} times (>2)!"
            assert len(ds_calls) == 2, f"WARNING: Dataset '{ds}' had {len(ds_calls)} accesses (expected 2)."
        print(">>> LOCKED TEST AUDIT PASSED: All accesses are within authorized limits.\n")


# -----------------------------------------------------------------------------
# Step 1: Run Full Repeated CV Experiments for Regression Datasets
# -----------------------------------------------------------------------------
def run_regression_experiments(
    regression_datasets: list[str],
    store: ResultsStore,
    n_repeats: int = REPEATS,
    n_splits: int = FOLDS,
) -> pd.DataFrame:
    print("=" * 80)
    print("STEP 1: EXECUTING FULL EXPERIMENTAL MATRIX ON REGRESSION DATASETS")
    print("=" * 80)
    print(f"Regression Datasets ({len(regression_datasets)}): {regression_datasets}")
    print(f"Methods ({len(METHODS)}): {METHODS}")
    print(f"Repeats: {n_repeats}, Folds: {n_splits}")
    print(f"Total Expected Rows: {len(regression_datasets)} * {len(METHODS)} * {n_repeats} * {n_splits} = {len(regression_datasets) * len(METHODS) * n_repeats * n_splits}")
    print("=" * 80)

    # Note explicitly in log that Day 14 dry run records are cleared
    print("[LOG] Clearing Day 14 dry-run records from results.db for fresh Day 15 full regression execution.")
    store.clear()

    total_runs = len(regression_datasets) * len(METHODS) * n_repeats
    run_counter = 0
    t0_global = time.perf_counter()

    for ds_idx, dataset in enumerate(regression_datasets, start=1):
        print(f"\n[{ds_idx}/{len(regression_datasets)}] DATASET: {dataset.upper()}")
        print("-" * 70)

        for m_idx, method in enumerate(METHODS, start=1):
            m_start = time.perf_counter()
            fold_count_for_method = 0

            print(f"  [{m_idx}/{len(METHODS)}] {method:28s} (8 repeats): ", end="", flush=True)

            for rep_idx in range(n_repeats):
                run_counter += 1
                # Execute single repeat using ResearchExperimentRunner.run_single()
                records = ResearchExperimentRunner.run_single(
                    dataset_name=dataset,
                    method_name=method,
                    repeat_index=rep_idx,
                    n_splits=n_splits,
                    base_seed=BASE_SEED,
                    outer_seed=BASE_SEED,
                    alpha=ALPHA,
                    reference_model=REFERENCE_MODEL,
                    results_store=store,
                    save_results=True,
                )
                fold_count_for_method += len(records)
                print(".", end="", flush=True)

            elapsed = time.perf_counter() - m_start
            print(f" Done ({fold_count_for_method} folds in {elapsed:.2f}s)")

    total_time = time.perf_counter() - t0_global
    print("\n" + "=" * 80)
    print(f"ALL REGRESSION RUNS COMPLETED in {total_time:.2f}s ({total_time / 60:.2f} min)")
    print("=" * 80)

    # Export to runs.parquet
    store.export_to_parquet(RUNS_PARQUET)
    df_runs = pd.read_parquet(RUNS_PARQUET)
    print(f"Saved {len(df_runs)} rows to {RUNS_PARQUET}")
    return df_runs


# -----------------------------------------------------------------------------
# Step 2: Compute Summary Metrics and Selection Stability
# -----------------------------------------------------------------------------
def compute_regression_summary(
    df_runs: pd.DataFrame,
    regression_datasets: list[str],
) -> pd.DataFrame:
    print("\n" + "=" * 80)
    print("STEP 2: COMPUTING REGRESSION SUMMARY & SELECTION STABILITY")
    print("=" * 80)

    summary_rows = []

    for dataset in regression_datasets:
        # Load dataset to inspect feature names
        X, _, _ = load_dataset(dataset)
        all_features = list(X.columns)

        for method in METHODS:
            norm_ds = dataset.lower().strip().replace("-", "_").replace(" ", "_")
            norm_m = method.lower().strip().replace("-", "_").replace(" ", "_")

            mask = (
                (df_runs["dataset"].str.lower().str.replace("-", "_").str.replace(" ", "_") == norm_ds) &
                (df_runs["method"].str.lower().str.replace("-", "_").str.replace(" ", "_") == norm_m)
            )
            subset = df_runs[mask]

            if subset.empty:
                continue

            # 1. CV Performance (RMSE mean & std)
            mean_cv = float(subset["cv_metric_value"].mean())
            std_cv = float(subset["cv_metric_value"].std())

            # 2. Mean number of selected features
            def _count_feats(val):
                if isinstance(val, (list, tuple)):
                    return len(val)
                if isinstance(val, str):
                    try:
                        return len(json.loads(val))
                    except Exception:
                        return len(val.strip("[]").split(","))
                return 0

            mean_k = float(subset["selected_features"].apply(_count_feats).mean())

            # 3. Selection stability across the 8 repeats (40 folds)
            stab_dict = compute_selection_stability(
                runs_df=df_runs,
                dataset_name=dataset,
                method=method,
            )
            mean_stability = float(np.mean(list(stab_dict.values()))) if stab_dict else 0.0

            # 4. Mean runtime
            mean_runtime = float(subset["runtime_seconds"].mean())

            summary_rows.append({
                "dataset": dataset,
                "method": method,
                "mean_cv_score": mean_cv,
                "std_cv_score": std_cv,
                "mean_num_selected_features": mean_k,
                "mean_stability_score": mean_stability,
                "mean_runtime_seconds": mean_runtime,
            })

    summary_df = pd.DataFrame(summary_rows)
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    summary_df.to_parquet(REGRESSION_SUMMARY_PARQUET, index=False)
    print(f"Exported regression summary ({len(summary_df)} rows) to: {REGRESSION_SUMMARY_PARQUET}")

    print("\nSummary Table:")
    print(summary_df.to_string(index=False))
    return summary_df


# -----------------------------------------------------------------------------
# Step 3: Locked Test Evaluation (Strictly Bounded to Proposed Methods)
# -----------------------------------------------------------------------------
def evaluate_locked_test_regression(
    regression_datasets: list[str],
    df_runs: pd.DataFrame,
    tracker: LockedTestAccessTracker,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    print("\n" + "=" * 80)
    print("STEP 3: LOCKED TEST EVALUATION (PROPOSED METHODS ONLY)")
    print("=" * 80)

    locked_test_rows = []
    consumed_tracking: dict[str, Any] = {}

    for dataset in regression_datasets:
        print(f"\nProcessing Locked Test for dataset: {dataset.upper()}")
        consumed_tracking[dataset] = {}

        # 1. Load full dataset and create fixed outer split
        X, y, task_type = load_dataset(dataset)
        split_result = create_split(X, y, task_type, locked_test_pct=20, seed=BASE_SEED)
        (X_dev, y_dev), (X_test_raw, y_test_raw) = partition_data(X, y, split_result)
        feature_names = list(X_dev.columns)
        p = len(feature_names)
        k = _resolve_k(None, p)

        # ---------------------------------------------------------------------
        # Proposed Method A: RANK_AGGREGATION
        # ---------------------------------------------------------------------
        print("  -> Refitting RANK_AGGREGATION on full Development set...")
        sel_res_a = select_features(
            X=X_dev,
            y=y_dev,
            task_type=task_type,
            method="RANK_AGGREGATION",
            seed=BASE_SEED,
        )
        selected_a = sel_res_a.selected_features
        print(f"     Selected features ({len(selected_a)}): {selected_a}")

        # Fit reference model on full Dev set with selected features
        scaler_a = StandardScaler()
        X_dev_a = scaler_a.fit_transform(X_dev[selected_a].to_numpy(dtype=np.float64))
        model_a = RandomForestRegressor(n_estimators=50, max_depth=10, random_state=BASE_SEED, n_jobs=-1)
        model_a.fit(X_dev_a, y_dev)

        # ONE-TIME Locked Test Evaluation via audit tracker
        X_test_a, y_test_a = tracker.get_locked_test_data(dataset, "RANK_AGGREGATION", X_test_raw, y_test_raw)
        X_test_a_scaled = scaler_a.transform(X_test_a[selected_a].to_numpy(dtype=np.float64))
        y_pred_a = model_a.predict(X_test_a_scaled)
        rmse_a = float(np.sqrt(mean_squared_error(y_test_a, y_pred_a)))
        print(f"     Locked Test RMSE (RANK_AGGREGATION): {rmse_a:.4f}")

        locked_test_rows.append({
            "dataset": dataset,
            "method": "RANK_AGGREGATION",
            "locked_test_metric_value": rmse_a,
        })
        consumed_tracking[dataset]["RANK_AGGREGATION"] = {
            "consumed": True,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "metric_name": "RMSE",
            "locked_test_metric_value": rmse_a,
            "selected_features": selected_a,
            "dev_samples": len(X_dev),
            "test_samples": len(X_test_a),
        }

        # ---------------------------------------------------------------------
        # Proposed Method B: RANK_AGGREGATION_STABILITY
        # ---------------------------------------------------------------------
        print("  -> Refitting RANK_AGGREGATION_STABILITY on full Development set...")
        # Compute feature stability across all 40 CV folds from the 8-repeat CV runs
        stab_dict_b = compute_selection_stability(
            runs_df=df_runs,
            dataset_name=dataset,
            method="RANK_AGGREGATION",  # Base ensemble selections across CV folds
        )
        stab_vector = np.array([stab_dict_b.get(f, 0.0) for f in feature_names], dtype=np.float64)

        ens_score, _, _ = rank_aggregation_ensemble(X_dev, y_dev, task_type, seed=BASE_SEED)
        final_scores = ALPHA * ens_score + (1.0 - ALPHA) * stab_vector
        _, final_rank_scores = FeatureSelectionService.calculate_technique_rank_scores(final_scores)

        sorted_idx = np.argsort(-final_rank_scores, kind="stable")
        selected_b = [feature_names[i] for i in sorted_idx[:k]]
        print(f"     Selected features ({len(selected_b)}): {selected_b}")

        # Fit reference model on full Dev set with selected features
        scaler_b = StandardScaler()
        X_dev_b = scaler_b.fit_transform(X_dev[selected_b].to_numpy(dtype=np.float64))
        model_b = RandomForestRegressor(n_estimators=50, max_depth=10, random_state=BASE_SEED, n_jobs=-1)
        model_b.fit(X_dev_b, y_dev)

        # ONE-TIME Locked Test Evaluation via audit tracker
        X_test_b, y_test_b = tracker.get_locked_test_data(dataset, "RANK_AGGREGATION_STABILITY", X_test_raw, y_test_raw)
        X_test_b_scaled = scaler_b.transform(X_test_b[selected_b].to_numpy(dtype=np.float64))
        y_pred_b = model_b.predict(X_test_b_scaled)
        rmse_b = float(np.sqrt(mean_squared_error(y_test_b, y_pred_b)))
        print(f"     Locked Test RMSE (RANK_AGGREGATION_STABILITY): {rmse_b:.4f}")

        locked_test_rows.append({
            "dataset": dataset,
            "method": "RANK_AGGREGATION_STABILITY",
            "locked_test_metric_value": rmse_b,
        })
        consumed_tracking[dataset]["RANK_AGGREGATION_STABILITY"] = {
            "consumed": True,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "metric_name": "RMSE",
            "locked_test_metric_value": rmse_b,
            "selected_features": selected_b,
            "dev_samples": len(X_dev),
            "test_samples": len(X_test_b),
        }

    # Save to Parquet
    df_locked = pd.DataFrame(locked_test_rows)
    df_locked.to_parquet(LOCKED_TEST_REGRESSION_PARQUET, index=False)
    print(f"\nExported Locked Test results to: {LOCKED_TEST_REGRESSION_PARQUET}")

    # Save tracking JSON
    with open(LOCKED_TEST_CONSUMED_JSON, "w", encoding="utf-8") as f:
        json.dump(consumed_tracking, f, indent=2)
    print(f"Exported consumption tracking to: {LOCKED_TEST_CONSUMED_JSON}")

    return df_locked, consumed_tracking


# -----------------------------------------------------------------------------
# Step 4: Acceptance Verification Suite
# -----------------------------------------------------------------------------
def run_day15_acceptance_checks(
    df_runs: pd.DataFrame,
    summary_df: pd.DataFrame,
    df_locked: pd.DataFrame,
    tracker: LockedTestAccessTracker,
    regression_datasets: list[str],
) -> None:
    print("\n" + "=" * 80)
    print("DAY 15 ACCEPTANCE CHECKS")
    print("=" * 80)

    # Check a: Row count
    expected_rows = len(regression_datasets) * len(METHODS) * REPEATS * FOLDS
    actual_rows = len(df_runs)
    print(f"Check a) Full Row Count: Expected = {expected_rows}, Actual = {actual_rows}")
    assert actual_rows == expected_rows, f"Row count mismatch! Expected {expected_rows}, got {actual_rows}"
    print(">>> CHECK (a) PASSED: runs.parquet contains exactly 640 rows for regression portion.")

    # Check b: Locked test partition read count
    print("\nCheck b) Locked Test Access Limits:")
    tracker.verify_access_counts(regression_datasets)
    print(">>> CHECK (b) PASSED: Zero unauthorized access, at most 2 accesses per dataset.")

    # Check c: Spot-check stability score
    print("Check c) Stability Score Comparison:")
    for ds in regression_datasets:
        stab_exp_a = summary_df[(summary_df["dataset"] == ds) & (summary_df["method"] == "RANK_AGGREGATION")]["mean_stability_score"].values[0]
        stab_exp_b = summary_df[(summary_df["dataset"] == ds) & (summary_df["method"] == "RANK_AGGREGATION_STABILITY")]["mean_stability_score"].values[0]
        print(f"   [{ds}] RANK_AGGREGATION stability = {stab_exp_a:.4f} | RANK_AGGREGATION_STABILITY stability = {stab_exp_b:.4f}")
        assert stab_exp_b >= stab_exp_a, (
            f"Stability violation on {ds}: RANK_AGGREGATION_STABILITY ({stab_exp_b:.4f}) < RANK_AGGREGATION ({stab_exp_a:.4f})"
        )
    print(">>> CHECK (c) PASSED: RANK_AGGREGATION_STABILITY stability is >= RANK_AGGREGATION stability.")


def main():
    print("#" * 80)
    print("   ML STUDIO RESEARCH TRACK — DAY 15 FULL RUNS (REGRESSION DATASETS)")
    print("#" * 80)

    regression_datasets = ["california_housing", "bike_sharing"]
    store = ResultsStore(RESULTS_DB)
    tracker = LockedTestAccessTracker()

    # 1. Run all combinations
    df_runs = run_regression_experiments(regression_datasets, store, n_repeats=REPEATS, n_splits=FOLDS)

    # 2. Compute summary & stability
    summary_df = compute_regression_summary(df_runs, regression_datasets)

    # 3. Locked test evaluation
    df_locked, consumed = evaluate_locked_test_regression(regression_datasets, df_runs, tracker)

    # 4. Acceptance checks
    run_day15_acceptance_checks(df_runs, summary_df, df_locked, tracker, regression_datasets)

    print("\n" + "=" * 80)
    print("DAY 15 RESEARCH TRACK COMPLETED SUCCESSFULLY!")
    print("=" * 80)


if __name__ == "__main__":
    main()
