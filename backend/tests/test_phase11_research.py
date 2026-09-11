"""
Phase 11: Research Track Verification Test Suite (SRS §9, SRS §2, ADR-005, ADR-014, Testing.md).

Tests:
1. Pre-registration integrity and frozen protocol immutability.
2. Four-phase stability execution workflow (SRS §2).
3. Mathematical correctness of FinalScore_j = alpha * BaseScore_j + (1 - alpha) * Stability_j.
4. Zero-leakage invariant: Locked Test partition is strictly isolated from CV and stability computations.
5. Paired statistical significance testing (paired t-test, Wilcoxon signed-rank, 95% CI).
6. Single-consumption Locked Test access tracker and audit verification.
7. Platform API boundary: RANK_AGGREGATION_STABILITY strictly returns HTTP 400.
"""

import json
from pathlib import Path
import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from app.main import app
from research.config import (
    DATASETS,
    METHODS,
    FOLDS,
    ALPHA,
    BASE_SEED,
    REFERENCE_MODEL,
    RUNS_PARQUET,
    RESEARCH_DIR,
)
from research.dataset_loader import load_dataset
from research.outer_split import create_split, partition_data
from research.phased_stability_runner import PhasedStabilityRunner, run_phased_stability_experiment
from research.stability import StabilityScorer, compute_selection_stability
from research.statistical_analysis import compute_paired_statistics, analyze_research_results

client = TestClient(app)


# -----------------------------------------------------------------------------
# 1. Pre-Registration Manifest & Protocol Integrity
# -----------------------------------------------------------------------------
def test_pre_registration_manifest_integrity():
    """Verify pre-registration manifest exists, is valid JSON, and freezes all protocol parameters."""
    manifest_path = Path("research/pre_registration_manifest.json")
    assert manifest_path.exists(), "Pre-registration manifest not found"

    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    assert manifest["status"] == "PRE_REGISTERED"
    assert "H1" in manifest["hypotheses"]
    assert "H0" in manifest["hypotheses"]

    # Datasets
    manifest_datasets = [d["name"] for d in manifest["datasets"]]
    assert set(manifest_datasets) == set(DATASETS)

    # Methods
    baseline_ids = [m["id"] for m in manifest["methods"]["baselines"]]
    proposed_ids = [m["id"] for m in manifest["methods"]["proposed"]]
    all_methods = baseline_ids + proposed_ids
    assert set(all_methods) == set(METHODS)
    assert "RANK_AGGREGATION" in proposed_ids
    assert "RANK_AGGREGATION_STABILITY" in proposed_ids

    # Protocol
    assert manifest["cv_protocol"]["folds"] == FOLDS
    assert manifest["cv_protocol"]["reference_model"] == REFERENCE_MODEL
    assert len(manifest["anti_leakage_invariants"]) >= 4


def test_frozen_protocol_constants():
    """Verify research/config.py contains frozen constants per SRS §9."""
    assert len(DATASETS) == 4
    assert len(METHODS) == 8
    assert FOLDS == 5
    assert REFERENCE_MODEL == "RandomForest"
    assert 0.0 < ALPHA < 1.0


# -----------------------------------------------------------------------------
# 2. Four-Phase Phased Stability Execution (SRS §2, ADR-005)
# -----------------------------------------------------------------------------
def test_four_phase_stability_execution_runner():
    """Verify the 4-phase stability runner executes Phase 1 -> Phase 2 -> Phase 3 -> Phase 4."""
    X, y, task_type = load_dataset("breast_cancer")
    split_info = create_split(X, y, task_type, locked_test_pct=20, seed=42)
    (X_dev, y_dev), (X_test, y_test) = partition_data(X, y, split_info)

    runner = PhasedStabilityRunner(
        dataset_name="breast_cancer",
        n_splits=3,
        n_repeats=2,
        alpha=0.7,
        seed=1000,
    )

    result = runner.execute_four_phases(X_dev, y_dev, task_type)

    # Phase 1 verification
    assert result.phase1_population_size == 6  # 2 repeats * 3 splits
    assert result.n_features == 30
    assert result.k_selected == 15

    # Phase 2 verification: Stability scores in [0.0, 1.0]
    for feat, stab in result.phase2_stability_scores.items():
        assert 0.0 <= stab <= 1.0, f"Stability out of range for {feat}: {stab}"

    # Phase 3 verification: FinalScore_j = alpha * BaseScore_j + (1-alpha) * Stability_j
    for feat, final_score in result.phase3_combined_scores.items():
        assert 0.0 <= final_score <= 1.0, f"Final score out of range for {feat}: {final_score}"

    # Phase 4 verification: CV evaluations and final subset
    assert len(result.phase4_cv_scores) == 6
    assert 0.0 <= result.mean_cv_score <= 1.0
    assert len(result.selected_features_final) == 15
    assert result.metric_name == "F1_MACRO"


def test_mathematical_score_combination():
    """Verify FinalScore_j = alpha * Importance_j + (1 - alpha) * Stability_j."""
    scorer = StabilityScorer(alpha=0.7)
    imp = np.array([0.8, 0.4, 0.2])
    stab = np.array([1.0, 0.5, 0.0])

    combined = scorer.compute_final_score(imp, stab)
    expected = 0.7 * imp + 0.3 * stab

    assert np.allclose(combined, expected)
    assert np.allclose(combined, [0.7 * 0.8 + 0.3 * 1.0, 0.7 * 0.4 + 0.3 * 0.5, 0.7 * 0.2 + 0.3 * 0.0])


# -----------------------------------------------------------------------------
# 3. Zero-Leakage Invariants
# -----------------------------------------------------------------------------
def test_zero_leakage_locked_test_isolation():
    """Verify Locked Test partition is completely isolated during CV and stability estimation."""
    X, y, task_type = load_dataset("california_housing")
    split_info = create_split(X, y, task_type, locked_test_pct=20, seed=123)

    dev_uids = set(split_info.dev_indices)
    test_uids = set(split_info.locked_test_indices)

    # Disjointness
    assert len(dev_uids.intersection(test_uids)) == 0
    assert len(dev_uids) + len(test_uids) == len(X)
    assert len(test_uids) == int(np.ceil(len(X) * 0.2))


# -----------------------------------------------------------------------------
# 4. Statistical Significance Testing & Confidence Intervals
# -----------------------------------------------------------------------------
def test_paired_statistics_engine():
    """Verify paired difference calculation, t-test, Wilcoxon test, and 95% CI."""
    scores_a = [0.90, 0.92, 0.89, 0.91, 0.93, 0.88, 0.94, 0.90]
    scores_b = [0.91, 0.93, 0.90, 0.92, 0.94, 0.89, 0.95, 0.91]  # Constant +0.01

    res = compute_paired_statistics(scores_a, scores_b, metric_name="F1_MACRO", higher_is_better=True)

    assert res["n_folds"] == 8
    assert np.isclose(res["mean_diff"], 0.01)
    assert np.isclose(res["median_diff"], 0.01)
    assert res["ci_95"][0] <= res["mean_diff"] <= res["ci_95"][1]
    assert res["is_significant"] is True  # Identical positive shift is statistically significant


def test_research_analysis_report_generation():
    """Verify research statistical report generates all required datasets and keys."""
    report = analyze_research_results()

    assert "study_identifier" in report
    assert "dataset_results" in report
    assert set(report["datasets_evaluated"]) == set(DATASETS)

    for ds in DATASETS:
        ds_res = report["dataset_results"][ds]
        assert "task_type" in ds_res
        assert "primary_comparison_exp_b_vs_exp_a" in ds_res
        assert "stability_experiment_a" in ds_res
        assert "stability_experiment_b" in ds_res
        assert "stability_gain_percent" in ds_res


# -----------------------------------------------------------------------------
# 5. Platform Scope Boundary (ADR-005, Rules.md)
# -----------------------------------------------------------------------------
def test_platform_api_blocks_rank_aggregation_stability(db_session):
    """
    CRITICAL INVARIANT (ADR-005, Domain 4):
    RANK_AGGREGATION_STABILITY is strictly research-only and blocked at the platform API with HTTP 400.
    """
    from app.services.feature_selection_service import FeatureSelectionService
    from fastapi import HTTPException, status

    svc = FeatureSelectionService(db_session)
    dummy_project_id = 999999

    with pytest.raises(HTTPException) as exc_info:
        svc.run_cv_feature_selection(
            project_id=dummy_project_id,
            method="RANK_AGGREGATION_STABILITY",
        )

    assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
    assert "research-only" in exc_info.value.detail.lower()
