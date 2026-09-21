"""
Unit & Integration Tests for Leakage Attack Lab (Phase 10 Assurance, Testing.md §52, ADR-013).

Validates that:
1. Attack Lab runs under manifest-identical conditions.
2. Manifest captures all required fields (dataset hash, outer split, metric, seed).
3. All 4 leakage attacks execute properly, measuring the generalization gap and proving the control holds.
4. Results file contains structured records (Attack, Expected effect, Observed, Control, Result).
"""

import json
from pathlib import Path
import pytest

from scripts.run_attack_lab import run_attack_lab


def test_attack_lab_execution_and_manifest_fidelity():
    """
    Executes Attack Lab and verifies:
    1. 4 distinct attacks evaluated.
    2. Shared manifest contains content_hash, seed, outer_split.
    3. Results are saved to week-10/artifacts.
    """
    report = run_attack_lab()

    assert "manifest" in report
    manifest = report["manifest"]
    assert manifest["dataset"]["content_hash"] is not None
    assert manifest["outer_split"]["type"] == "DEV_80_LOCKED_20"
    assert manifest["seed"] == 42
    assert manifest["cv_folds"] == 5

    attacks = report["attacks"]
    assert len(attacks) == 4

    attack_ids = [a["attack_id"] for a in attacks]
    assert attack_ids == ["ATK-01", "ATK-02", "ATK-03", "ATK-04"]

    for atk in attacks:
        assert atk["result"] == "ATTACK CONFIRMED & CONTROL HELD"
        assert "expected_effect" in atk
        assert "observed" in atk
        assert "control" in atk

    # Verify generated artifact files on disk
    artifacts_dir = Path(__file__).resolve().parent.parent.parent / "week-10" / "artifacts"
    manifest_file = artifacts_dir / "attack_lab_manifest.json"
    results_file = artifacts_dir / "attack_lab_results.json"

    assert manifest_file.exists()
    assert results_file.exists()

    disk_results = json.loads(results_file.read_text())
    assert len(disk_results["attacks"]) == 4
