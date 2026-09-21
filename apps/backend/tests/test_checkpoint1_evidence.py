import pytest
from backend.scripts.run_checkpoint1_verification import run_live_checkpoint_1

def test_checkpoint1_zero_test_leakage_and_isolation():
    """
    Test Day 7 Checkpoint 1:
    Verifies that the live end-to-end pipeline:
    Upload -> Split -> Profile -> Transform Live
    strictly isolates the Locked Test partition and guarantees:
    1. Zero test partition reads during profiling, transformation config, or preview.
    2. Zero intersection between accessed row IDs and Locked Test partition.
    3. Pipeline skeleton remains completely unfitted prior to cross-validation.
    """
    result = run_live_checkpoint_1()
    
    assert result["all_invariants_passed"] is True
    assert result["audit"]["get_locked_test_data_calls"] == 0
    assert result["audit"]["accessed_test_rows_count"] == 0
    assert result["audit"]["preview_test_overlap_count"] == 0
    assert result["pipeline_unfitted"] is True
    assert result["development_rows"] + result["locked_test_rows"] == result["total_rows"]
