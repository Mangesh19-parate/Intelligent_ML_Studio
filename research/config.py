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
REPEATS = 8          # Within the spec's 5-10 range, fixed now
ALPHA = 0.5          # Stability weighting, fixed now
REFERENCE_MODEL = "RandomForest"    # Fixed across all methods for fair comparison
BASE_SEED = 1000     # Each repeat uses BASE_SEED + repeat_index, recorded per run

# Paths
RESEARCH_DIR = Path(__file__).resolve().parent
DATA_DIR = RESEARCH_DIR / "data"
RESULTS_DB = RESEARCH_DIR / "results.db"
RUNS_PARQUET = RESEARCH_DIR / "runs.parquet"
