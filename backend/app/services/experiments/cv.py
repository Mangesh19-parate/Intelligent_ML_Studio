"""
Cross-Validation & Fold Splitting Module for ML Studio Experiments.

Enforces:
1. Strict StratifiedKFold for classification and KFold for regression on Development partition.
2. Deterministic seed management.
3. Cryptographic row hashing per fold (train_row_hash, validation_row_hash, test_row_hash).
"""

import hashlib
import numpy as np
import pandas as pd
from typing import Generator
from sklearn.model_selection import KFold, StratifiedKFold


def compute_partition_hash(df: pd.DataFrame) -> str:
    """Computes a deterministic SHA-256 hash of a dataframe's row contents."""
    if df.empty:
        return hashlib.sha256(b"").hexdigest()
    csv_bytes = df.to_csv(index=False).encode("utf-8")
    return hashlib.sha256(csv_bytes).hexdigest()


def generate_cv_folds(
    X: pd.DataFrame,
    y: pd.Series,
    task_type: str,
    n_splits: int = 5,
    seed: int = 42,
) -> list[tuple[np.ndarray, np.ndarray]]:
    """
    Generates deterministic train and validation indices for cross-validation.
    """
    if task_type == "CLASSIFICATION":
        cv = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=seed)
        return list(cv.split(X, y))
    else:
        cv = KFold(n_splits=n_splits, shuffle=True, random_state=seed)
        return list(cv.split(X, y))
