"""
ML Studio Research Track — Frozen Experimental Protocol (SRS §9).

This configuration module freezes all experimental hyperparameters for Days 14–16.
Deciding or altering the protocol after seeing partial results constitutes research-track
leakage. Day 15–16 execution only reads from this module.
"""

from pathlib import Path

# Datasets evaluated (2 regression + 2 classification from Day 13)
DATASETS = [
    "california_housing",
    "bike_sharing",
    "breast_cancer",
    "adult_income",
]

# 8 evaluated feature selection methods (6 baselines + 2 distinct proposed experiments)
# Experiment A = RANK_AGGREGATION (ensemble combining 4 selectors)
# Experiment B = RANK_AGGREGATION_STABILITY (ensemble + cross-fold selection stability)
METHODS = [
    "NO_SELECTION",
    "CORRELATION",
    "LASSO",
    "RANDOM_FOREST",
    "PERMUTATION",
    "RFE",
    "RANK_AGGREGATION",
    "RANK_AGGREGATION_STABILITY",
]

# Cross-Validation Protocol
FOLDS = 5
REPEATS = 8          # Within the spec's 5-10 range (SRS §9)
ALPHA = 0.7          # Stability weighting strictly frozen to 0.7 per SRS §9
REFERENCE_MODEL = "RandomForest"    # Fixed across all methods for fair comparison
BASE_SEED = 1000     # Seed base for deterministic hash expansion

def derive_run_seed(dataset_name: str, method_name: str, repeat_idx: int) -> int:
    """Deterministically derive a 32-bit seed via SHA-256 (SRS §9)."""
    import hashlib
    h = hashlib.sha256(f"{dataset_name}:{method_name}:{repeat_idx}:{BASE_SEED}".encode()).hexdigest()
    return int(h[:8], 16) % (2**31 - 1)

# Paths
RESEARCH_DIR = Path(__file__).resolve().parent
DATA_DIR = RESEARCH_DIR / "data"
RESULTS_DB = RESEARCH_DIR / "results.db"
RUNS_PARQUET = RESEARCH_DIR / "runs.parquet"
