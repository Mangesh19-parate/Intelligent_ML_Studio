"""
Day 4 — Comprehensive Unit & Determinism Tests:
Deterministic 3-tier tie-breaking at K boundary (higher EnsembleScore -> lower raw rank sum -> lexicographical name).
Cold-process byte-identical determinism test across isolated Python processes (SRS §2.7).
"""

import json
import subprocess
import sys
import numpy as np
import pytest

from app.services.selectors import (
    sort_features_with_tie_break,
    apply_top_k_percent_selection,
    calculate_srs_rank_scores,
    aggregate_ensemble_scores,
    CORRELATION_SELECTOR,
    LASSO_SELECTOR,
    RANDOM_FOREST_IMPORTANCE_SELECTOR,
    PERMUTATION_IMPORTANCE_SELECTOR,
)


# =============================================================================
# 1. 3-Tier Tie-Breaking Tests at the K Boundary
# =============================================================================

def test_tie_break_priority_1_higher_ensemble_score():
    """
    Tier 1: Higher EnsembleScore strictly takes priority over rank sums or names.
    - feat_a: score = 0.90, rank_sum = 10.0
    - feat_b: score = 0.85, rank_sum = 2.0 (even though rank_sum is much lower)
    """
    feature_names = ["feat_b", "feat_a"]
    scores = {"feat_a": 0.90, "feat_b": 0.85}
    rank_sums = {"feat_a": 10.0, "feat_b": 2.0}

    sorted_res = sort_features_with_tie_break(feature_names, scores, rank_sums)
    assert sorted_res[0][0] == "feat_a"
    assert sorted_res[1][0] == "feat_b"

    # Selection at K = 1
    sel = apply_top_k_percent_selection(
        feature_names, scores, rank_sums=rank_sums, k_min=1, k_max=1, alpha=0.5
    )
    assert sel["selected_features"] == ["feat_a"]


def test_tie_break_priority_2_lower_raw_rank_sum():
    """
    Tier 2: When EnsembleScores are exactly tied, lower aggregate raw rank sum wins.
    - feat_x: score = 0.75, rank_sum = 3.0 (e.g. ranks 1, 2 across 2 techniques)
    - feat_y: score = 0.75, rank_sum = 4.0 (e.g. ranks 2, 2 across 2 techniques)
    feat_x must be ranked higher and selected at K = 1 boundary.
    """
    feature_names = ["feat_y", "feat_x"]
    scores = {"feat_x": 0.75, "feat_y": 0.75}
    rank_sums = {"feat_x": 3.0, "feat_y": 4.0}

    sorted_res = sort_features_with_tie_break(feature_names, scores, rank_sums)
    assert sorted_res[0][0] == "feat_x"
    assert sorted_res[1][0] == "feat_y"

    sel = apply_top_k_percent_selection(
        feature_names, scores, rank_sums=rank_sums, k_min=1, k_max=1, alpha=0.5
    )
    assert sel["selected_features"] == ["feat_x"]


def test_tie_break_priority_3_lexicographical_name():
    """
    Tier 3: When EnsembleScore AND raw rank sum are tied, lexicographical column name wins.
    - feat_alpha: score = 0.60, rank_sum = 5.0
    - feat_beta:  score = 0.60, rank_sum = 5.0
    - feat_gamma: score = 0.60, rank_sum = 5.0
    Lexicographical order 'feat_alpha' < 'feat_beta' < 'feat_gamma'.
    At K = 2, selected must be ['feat_alpha', 'feat_beta'].
    """
    feature_names = ["feat_gamma", "feat_beta", "feat_alpha"]
    scores = {"feat_alpha": 0.60, "feat_beta": 0.60, "feat_gamma": 0.60}
    rank_sums = {"feat_alpha": 5.0, "feat_beta": 5.0, "feat_gamma": 5.0}

    sorted_res = sort_features_with_tie_break(feature_names, scores, rank_sums)
    assert [item[0] for item in sorted_res] == ["feat_alpha", "feat_beta", "feat_gamma"]

    sel = apply_top_k_percent_selection(
        feature_names, scores, rank_sums=rank_sums, k_min=2, k_max=2, alpha=0.66
    )
    assert sel["selected_features"] == ["feat_alpha", "feat_beta"]
    assert sel["is_selected_map"]["feat_alpha"] is True
    assert sel["is_selected_map"]["feat_beta"] is True
    assert sel["is_selected_map"]["feat_gamma"] is False


def test_complex_multi_tier_tie_break_ordering():
    """
    Tests full 3-tier ordering with mixed candidate profiles:
    - feat_1: score 0.80, rank_sum 2.0 -> Tier 1 rank 1
    - feat_2: score 0.70, rank_sum 3.0 -> Tier 2 rank 2 (beats feat_3 due to lower rank_sum)
    - feat_3: score 0.70, rank_sum 4.0 -> Tier 2 rank 3
    - feat_4: score 0.50, rank_sum 6.0, name "a_col" -> Tier 3 rank 4 (beats b_col on name)
    - feat_5: score 0.50, rank_sum 6.0, name "b_col" -> Tier 3 rank 5
    """
    feature_names = ["b_col", "feat_2", "feat_3", "feat_1", "a_col"]
    scores = {
        "feat_1": 0.80,
        "feat_2": 0.70,
        "feat_3": 0.70,
        "a_col": 0.50,
        "b_col": 0.50,
    }
    rank_sums = {
        "feat_1": 2.0,
        "feat_2": 3.0,
        "feat_3": 4.0,
        "a_col": 6.0,
        "b_col": 6.0,
    }

    sorted_res = sort_features_with_tie_break(feature_names, scores, rank_sums)
    ordered_names = [item[0] for item in sorted_res]
    assert ordered_names == ["feat_1", "feat_2", "feat_3", "a_col", "b_col"]


# =============================================================================
# 2. Cold-Process Byte-Identical Determinism Test
# =============================================================================

from pathlib import Path
import os

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent.parent
BACKEND_ROOT = WORKSPACE_ROOT / "backend"

COLD_PROCESS_SCRIPT = f"""
import sys
import json
import numpy as np
from pathlib import Path

# Add project root and backend to sys.path
for p in [r"{WORKSPACE_ROOT}", r"{BACKEND_ROOT}"]:
    if p not in sys.path:
        sys.path.insert(0, p)

from app.services.selectors import (
    CORRELATION_SELECTOR,
    LASSO_SELECTOR,
    RANDOM_FOREST_IMPORTANCE_SELECTOR,
    PERMUTATION_IMPORTANCE_SELECTOR,
    aggregate_ensemble_scores,
    apply_top_k_percent_selection,
)

def run_isolated_pipeline(seed=42):
    np.random.seed(seed)
    n, p = 80, 8
    feature_names = [f"col_{{i:02d}}" for i in range(p)]
    X = np.random.normal(0, 1, (n, p))
    y = 3.0 * X[:, 0] + 1.5 * X[:, 1] + 0.8 * X[:, 2] + np.random.normal(0, 0.2, n)

    # 1. Run all 4 selectors
    out_corr = CORRELATION_SELECTOR.select(X, y, "REGRESSION", feature_names)
    out_lasso = LASSO_SELECTOR.select(X, y, "REGRESSION", feature_names, seed=seed)
    out_rf = RANDOM_FOREST_IMPORTANCE_SELECTOR.select(X, y, "REGRESSION", feature_names, seed=seed)
    out_perm = PERMUTATION_IMPORTANCE_SELECTOR.select(X, y, "REGRESSION", feature_names, seed=seed)

    applied_rank_scores = [
        out_corr.rank_scores,
        out_lasso.rank_scores,
        out_rf.rank_scores,
        out_perm.rank_scores,
    ]
    applied_ranks = [
        out_corr.ranks,
        out_lasso.ranks,
        out_rf.ranks,
        out_perm.ranks,
    ]

    ensemble_scores = aggregate_ensemble_scores(applied_rank_scores, p)
    rank_sums = np.sum(np.vstack(applied_ranks), axis=0)

    # 2. Apply selection with 3-tier tie-break
    sel = apply_top_k_percent_selection(
        feature_names=feature_names,
        scores=ensemble_scores,
        rank_sums=rank_sums,
        alpha=0.35,
        k_min=3,
        k_max=10,
    )

    result_payload = {{
        "feature_names": feature_names,
        "raw_scores": {{
            "corr": [round(float(x), 8) for x in out_corr.raw_scores],
            "lasso": [round(float(x), 8) for x in out_lasso.raw_scores],
            "rf": [round(float(x), 8) for x in out_rf.raw_scores],
            "perm": [round(float(x), 8) for x in out_perm.raw_scores],
        }},
        "ensemble_scores": [round(float(x), 8) for x in ensemble_scores],
        "rank_sums": [round(float(x), 8) for x in rank_sums],
        "selected_features": sel["selected_features"],
        "k_selected": sel["k_selected"],
        "is_selected_map": sel["is_selected_map"],
    }}
    # Canonical deterministic JSON string with sorted keys
    return json.dumps(result_payload, sort_keys=True, separators=(',', ':'))

if __name__ == "__main__":
    output_json = run_isolated_pipeline(seed=42)
    sys.stdout.write(output_json)
"""


def test_cold_process_byte_identical_determinism(tmp_path):
    """
    Cold-Process Determinism Test:
    Spawns two separate, isolated Python interpreter processes running identical
    feature selection pipelines and configurations with fixed seed 42.
    Asserts that the stdout byte streams from both processes are 100% byte-identical.
    """
    script_path = tmp_path / "cold_determinism_worker.py"
    script_path.write_text(COLD_PROCESS_SCRIPT, encoding="utf-8")

    env = dict(os.environ)
    env["PYTHONPATH"] = f"{WORKSPACE_ROOT};{BACKEND_ROOT}"

    # Run Cold Process 1
    proc1 = subprocess.run(
        [sys.executable, str(script_path)],
        capture_output=True,
        text=False,  # capture raw bytes
        env=env,
        check=True,
    )
    bytes_run1 = proc1.stdout

    # Run Cold Process 2 (Fresh sub-process)
    proc2 = subprocess.run(
        [sys.executable, str(script_path)],
        capture_output=True,
        text=False,  # capture raw bytes
        env=env,
        check=True,
    )
    bytes_run2 = proc2.stdout

    # 1. Byte-level exact equality
    assert len(bytes_run1) > 0, "Cold process 1 returned empty output"
    assert bytes_run1 == bytes_run2, f"Byte divergence detected! Run 1 len={len(bytes_run1)}, Run 2 len={len(bytes_run2)}"

    # 2. Verify payload correctness
    parsed = json.loads(bytes_run1.decode("utf-8"))
    assert parsed["k_selected"] == 3
    assert len(parsed["selected_features"]) == 3
    assert parsed["selected_features"][0] == "col_00"  # strongest signal
