"""
Day 16 — Research Track: Full Runs, Classification Datasets (SRS §9).

Executes the full experimental protocol on classification benchmark datasets:
- Datasets: Breast Cancer Wisconsin, Adult Census Income (Classification)
- 8 Methods: NO_SELECTION, CORRELATION, LASSO, RANDOM_FOREST, PERMUTATION, RFE,
             RANK_AGGREGATION, RANK_AGGREGATION_STABILITY
- 8 Repeats × 5 Stratified Folds = 40 folds per method per dataset (Total 640 rows)
- Seed: BASE_SEED + repeat_index (1000 to 1007)
- Computes CV metrics (Macro-F1, matching platform primary metric SRS §2.9), feature selection stability, and summary metrics.
- Evaluates Locked Test partition strictly ONCE each for proposed methods (RANK_AGGREGATION and RANK_AGGREGATION_STABILITY).
- Generates:
    * research/runs.parquet (1280 total rows: 640 regression + 640 classification)
    * research/results/classification_summary.parquet
    * research/results/locked_test_classification.parquet
    * research/results/locked_test_consumed.json (updated with classification partitions)
    * research/results/all_summary.parquet (consolidated 32-row dataset with task_type column)
"""

import sys
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import numpy as np
import pandas as pd
from sklearn.metrics import f1_score
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestClassifier

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
from research.stability import compute_selection_stability
from app.services.feature_selection_service import FeatureSelectionService

RESULTS_DIR = RESEARCH_DIR / "results"
REGRESSION_SUMMARY_PARQUET = RESULTS_DIR / "regression_summary.parquet"
CLASSIFICATION_SUMMARY_PARQUET = RESULTS_DIR / "classification_summary.parquet"
LOCKED_TEST_CLASSIFICATION_PARQUET = RESULTS_DIR / "locked_test_classification.parquet"
LOCKED_TEST_CONSUMED_JSON = RESULTS_DIR / "locked_test_consumed.json"
ALL_SUMMARY_PARQUET = RESULTS_DIR / "all_summary.parquet"


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

    def verify_access_counts(self, classification_datasets: list[str]) -> None:
        print("\n" + "=" * 80)
        print("LOCKED TEST ACCESS AUDIT VERIFICATION (CLASSIFICATION)")
        print("=" * 80)
        for ds in classification_datasets:
            ds_calls = [r for r in self.access_log if r["dataset"] == ds]
            print(f"Dataset '{ds}': Total Locked Test accesses = {len(ds_calls)}")
            for c in ds_calls:
                print(f"   - Method: {c['method']} at {c['timestamp']}")
            assert len(ds_calls) <= 2, f"VIOLATION: Dataset '{ds}' was accessed {len(ds_calls)} times (>2)!"
            assert len(ds_calls) == 2, f"WARNING: Dataset '{ds}' had {len(ds_calls)} accesses (expected 2)."
        print(">>> LOCKED TEST AUDIT PASSED: All accesses are within authorized limits.\n")


# -----------------------------------------------------------------------------
# Step 1: Run Full Repeated CV Experiments for Classification Datasets
# -----------------------------------------------------------------------------
def run_classification_experiments(
    classification_datasets: list[str],
    store: ResultsStore,
    n_repeats: int = REPEATS,
    n_splits: int = FOLDS,
) -> pd.DataFrame:
    print("=" * 80)
    print("STEP 1: EXECUTING FULL EXPERIMENTAL MATRIX ON CLASSIFICATION DATASETS")
    print("=" * 80)
    print(f"Classification Datasets ({len(classification_datasets)}): {classification_datasets}")
    print(f"Methods ({len(METHODS)}): {METHODS}")
    print(f"Repeats: {n_repeats}, Folds: {n_splits} (Stratified)")
    print(f"Total Expected New Rows: {len(classification_datasets)} * {len(METHODS)} * {n_repeats} * {n_splits} = {len(classification_datasets) * len(METHODS) * n_repeats * n_splits}")
    print("=" * 80)

    # Clear prior classification records if any, preserving regression records
    for ds in classification_datasets:
        deleted = store.clear(dataset=ds)
        if deleted > 0:
            print(f"[LOG] Cleared {deleted} existing records for dataset '{ds}'.")

    total_runs = len(classification_datasets) * len(METHODS) * n_repeats
    run_counter = 0
    t0_global = time.perf_counter()

    for ds_idx, dataset in enumerate(classification_datasets, start=1):
        print(f"\n[{ds_idx}/{len(classification_datasets)}] DATASET: {dataset.upper()}")
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
    print(f"ALL CLASSIFICATION RUNS COMPLETED in {total_time:.2f}s ({total_time / 60:.2f} min)")
    print("=" * 80)

    # Export consolidated runs table (regression + classification) to runs.parquet
    store.export_to_parquet(RUNS_PARQUET)
    df_runs = pd.read_parquet(RUNS_PARQUET)
    print(f"Exported all results ({len(df_runs)} rows) to: {RUNS_PARQUET}")
    return df_runs


# -----------------------------------------------------------------------------
# Step 2: Compute Summary Metrics and Selection Stability for Classification
# -----------------------------------------------------------------------------
def compute_classification_summary(
    df_runs: pd.DataFrame,
    classification_datasets: list[str],
) -> pd.DataFrame:
    print("\n" + "=" * 80)
    print("STEP 2: COMPUTING CLASSIFICATION SUMMARY & SELECTION STABILITY")
    print("=" * 80)

    summary_rows = []

    for dataset in classification_datasets:
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

            # 1. CV Performance (Macro-F1 mean & std)
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
    summary_df.to_parquet(CLASSIFICATION_SUMMARY_PARQUET, index=False)
    print(f"Exported classification summary ({len(summary_df)} rows) to: {CLASSIFICATION_SUMMARY_PARQUET}")

    print("\nClassification Summary Table:")
    print(summary_df.to_string(index=False))
    return summary_df


# -----------------------------------------------------------------------------
# Step 3: Locked Test Evaluation for Classification Datasets
# -----------------------------------------------------------------------------
def evaluate_locked_test_classification(
    classification_datasets: list[str],
    df_runs: pd.DataFrame,
    tracker: LockedTestAccessTracker,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    print("\n" + "=" * 80)
    print("STEP 3: LOCKED TEST EVALUATION (CLASSIFICATION PROPOSED METHODS ONLY)")
    print("=" * 80)

    locked_test_rows = []

    # Load existing consumed-partition tracking file
    if LOCKED_TEST_CONSUMED_JSON.exists():
        with open(LOCKED_TEST_CONSUMED_JSON, "r", encoding="utf-8") as f:
            consumed_tracking = json.load(f)
    else:
        consumed_tracking = {}

    for dataset in classification_datasets:
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
        model_a = RandomForestClassifier(n_estimators=50, max_depth=10, random_state=BASE_SEED, n_jobs=-1)
        model_a.fit(X_dev_a, y_dev)

        # ONE-TIME Locked Test Evaluation via audit tracker
        X_test_a, y_test_a = tracker.get_locked_test_data(dataset, "RANK_AGGREGATION", X_test_raw, y_test_raw)
        X_test_a_scaled = scaler_a.transform(X_test_a[selected_a].to_numpy(dtype=np.float64))
        y_pred_a = model_a.predict(X_test_a_scaled)
        f1_a = float(f1_score(y_test_a, y_pred_a, average="macro"))
        print(f"     Locked Test Macro-F1 (RANK_AGGREGATION): {f1_a:.4f}")

        locked_test_rows.append({
            "dataset": dataset,
            "method": "RANK_AGGREGATION",
            "locked_test_metric_value": f1_a,
        })
        consumed_tracking[dataset]["RANK_AGGREGATION"] = {
            "consumed": True,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "metric_name": "F1_MACRO",
            "locked_test_metric_value": f1_a,
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
            method="RANK_AGGREGATION",
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
        model_b = RandomForestClassifier(n_estimators=50, max_depth=10, random_state=BASE_SEED, n_jobs=-1)
        model_b.fit(X_dev_b, y_dev)

        # ONE-TIME Locked Test Evaluation via audit tracker
        X_test_b, y_test_b = tracker.get_locked_test_data(dataset, "RANK_AGGREGATION_STABILITY", X_test_raw, y_test_raw)
        X_test_b_scaled = scaler_b.transform(X_test_b[selected_b].to_numpy(dtype=np.float64))
        y_pred_b = model_b.predict(X_test_b_scaled)
        f1_b = float(f1_score(y_test_b, y_pred_b, average="macro"))
        print(f"     Locked Test Macro-F1 (RANK_AGGREGATION_STABILITY): {f1_b:.4f}")

        locked_test_rows.append({
            "dataset": dataset,
            "method": "RANK_AGGREGATION_STABILITY",
            "locked_test_metric_value": f1_b,
        })
        consumed_tracking[dataset]["RANK_AGGREGATION_STABILITY"] = {
            "consumed": True,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "metric_name": "F1_MACRO",
            "locked_test_metric_value": f1_b,
            "selected_features": selected_b,
            "dev_samples": len(X_dev),
            "test_samples": len(X_test_b),
        }

    # Save to Parquet
    df_locked = pd.DataFrame(locked_test_rows)
    df_locked.to_parquet(LOCKED_TEST_CLASSIFICATION_PARQUET, index=False)
    print(f"\nExported Classification Locked Test results to: {LOCKED_TEST_CLASSIFICATION_PARQUET}")

    # Update tracking JSON
    with open(LOCKED_TEST_CONSUMED_JSON, "w", encoding="utf-8") as f:
        json.dump(consumed_tracking, f, indent=2)
    print(f"Updated consumption tracking in: {LOCKED_TEST_CONSUMED_JSON}")

    return df_locked, consumed_tracking


# -----------------------------------------------------------------------------
# Step 4: Consolidated all_summary.parquet Creation
# -----------------------------------------------------------------------------
def create_consolidated_summary() -> pd.DataFrame:
    print("\n" + "=" * 80)
    print("STEP 4: PRODUCING CONSOLIDATED ALL_SUMMARY.PARQUET")
    print("=" * 80)

    if not REGRESSION_SUMMARY_PARQUET.exists():
        raise FileNotFoundError(f"Missing regression summary: {REGRESSION_SUMMARY_PARQUET}")
    if not CLASSIFICATION_SUMMARY_PARQUET.exists():
        raise FileNotFoundError(f"Missing classification summary: {CLASSIFICATION_SUMMARY_PARQUET}")

    df_reg = pd.read_parquet(REGRESSION_SUMMARY_PARQUET)
    df_cls = pd.read_parquet(CLASSIFICATION_SUMMARY_PARQUET)

    # Add task_type and metric_name qualifiers to guarantee no metric collision
    df_reg.insert(0, "task_type", "REGRESSION")
    df_reg.insert(3, "cv_metric_name", "RMSE")

    df_cls.insert(0, "task_type", "CLASSIFICATION")
    df_cls.insert(3, "cv_metric_name", "F1_MACRO")

    df_all = pd.concat([df_reg, df_cls], ignore_index=True)
    df_all.to_parquet(ALL_SUMMARY_PARQUET, index=False)
    print(f"Saved consolidated summary ({len(df_all)} rows) to: {ALL_SUMMARY_PARQUET}")

    return df_all


# -----------------------------------------------------------------------------
# Step 5: Acceptance Verification Suite
# -----------------------------------------------------------------------------
def run_day16_acceptance_checks(
    df_runs: pd.DataFrame,
    summary_df: pd.DataFrame,
    df_all: pd.DataFrame,
    tracker: LockedTestAccessTracker,
    classification_datasets: list[str],
) -> None:
    print("\n" + "=" * 80)
    print("DAY 16 ACCEPTANCE CHECKS")
    print("=" * 80)

    # Check a: Row counts & Locked Test calls
    expected_cls_rows = len(classification_datasets) * len(METHODS) * REPEATS * FOLDS
    actual_cls_rows = len(df_runs[df_runs["dataset"].isin(classification_datasets)])
    print(f"Check a) Classification Row Count: Expected = {expected_cls_rows}, Actual = {actual_cls_rows}")
    assert actual_cls_rows == expected_cls_rows, f"Row count mismatch! Expected {expected_cls_rows}, got {actual_cls_rows}"

    total_expected_runs = len(DATASETS) * len(METHODS) * REPEATS * FOLDS
    total_actual_runs = len(df_runs)
    print(f"         Total runs.parquet Row Count: Expected = {total_expected_runs}, Actual = {total_actual_runs}")
    assert total_actual_runs == total_expected_runs, f"Total row mismatch! Expected {total_expected_runs}, got {total_actual_runs}"

    print("\nCheck a.2) Locked Test Access Limits:")
    tracker.verify_access_counts(classification_datasets)
    print(">>> CHECK (a) PASSED: 640 classification rows recorded, 1280 total runs, exactly 2 Locked Test calls per dataset.")

    # Check b: all_summary.parquet separation by task_type
    print("\nCheck b) all_summary.parquet Task Type Separation:")
    print(f"   Total rows in all_summary: {len(df_all)}")
    assert len(df_all) == 32, f"Expected 32 rows in all_summary, got {len(df_all)}"
    reg_rows = df_all[df_all["task_type"] == "REGRESSION"]
    cls_rows = df_all[df_all["task_type"] == "CLASSIFICATION"]
    print(f"   Regression rows: {len(reg_rows)} (Metric: {reg_rows['cv_metric_name'].unique().tolist()})")
    print(f"   Classification rows: {len(cls_rows)} (Metric: {cls_rows['cv_metric_name'].unique().tolist()})")
    assert len(reg_rows) == 16, f"Expected 16 regression rows, got {len(reg_rows)}"
    assert len(cls_rows) == 16, f"Expected 16 classification rows, got {len(cls_rows)}"
    assert (reg_rows["cv_metric_name"] == "RMSE").all(), "Regression rows must have cv_metric_name == RMSE"
    assert (cls_rows["cv_metric_name"] == "F1_MACRO").all(), "Classification rows must have cv_metric_name == F1_MACRO"
    print(">>> CHECK (b) PASSED: all_summary.parquet unambiguously partitions regression vs classification metrics.")

    # Check c: Sanity check NO_SELECTION mean_num_selected_features == full feature count
    print("\nCheck c) NO_SELECTION Feature Count Sanity Check:")
    for ds in classification_datasets:
        X, _, _ = load_dataset(ds)
        p_full = X.shape[1]
        no_sel_row = summary_df[(summary_df["dataset"] == ds) & (summary_df["method"] == "NO_SELECTION")]
        k_no_sel = float(no_sel_row["mean_num_selected_features"].values[0])
        print(f"   [{ds}] Full Feature Count = {p_full} | NO_SELECTION mean_num_selected_features = {k_no_sel}")
        assert k_no_sel == float(p_full), (
            f"Sanity Check Failed for {ds}: NO_SELECTION mean_num_selected_features ({k_no_sel}) != full count ({p_full})"
        )
    print(">>> CHECK (c) PASSED: NO_SELECTION baseline matches full feature count for all classification datasets.")

    # Additional stability check
    print("\nStability Check (RANK_AGGREGATION_STABILITY >= RANK_AGGREGATION):")
    for ds in classification_datasets:
        stab_a = summary_df[(summary_df["dataset"] == ds) & (summary_df["method"] == "RANK_AGGREGATION")]["mean_stability_score"].values[0]
        stab_b = summary_df[(summary_df["dataset"] == ds) & (summary_df["method"] == "RANK_AGGREGATION_STABILITY")]["mean_stability_score"].values[0]
        print(f"   [{ds}] RANK_AGGREGATION stability = {stab_a:.4f} | RANK_AGGREGATION_STABILITY stability = {stab_b:.4f}")
        assert stab_b >= stab_a, (
            f"Stability violation on {ds}: RANK_AGGREGATION_STABILITY ({stab_b:.4f}) < RANK_AGGREGATION ({stab_a:.4f})"
        )
    print(">>> Stability Check PASSED.")


def main():
    print("#" * 80)
    print("   ML STUDIO RESEARCH TRACK — DAY 16 FULL RUNS (CLASSIFICATION DATASETS)")
    print("#" * 80)

    classification_datasets = ["breast_cancer", "adult_income"]
    store = ResultsStore(RESULTS_DB)
    tracker = LockedTestAccessTracker()

    # 1. Run all combinations
    df_runs = run_classification_experiments(classification_datasets, store, n_repeats=REPEATS, n_splits=FOLDS)

    # 2. Compute summary & stability
    summary_df = compute_classification_summary(df_runs, classification_datasets)

    # 3. Locked test evaluation
    df_locked, consumed = evaluate_locked_test_classification(classification_datasets, df_runs, tracker)

    # 4. Create consolidated summary
    df_all = create_consolidated_summary()

    # 5. Acceptance checks
    run_day16_acceptance_checks(df_runs, summary_df, df_all, tracker, classification_datasets)

    print("\n" + "=" * 80)
    print("DAY 16 RESEARCH TRACK COMPLETED SUCCESSFULLY!")
    print("=" * 80)


if __name__ == "__main__":
    main()
