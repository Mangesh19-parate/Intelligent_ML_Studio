"""
Outer Dataset Splitter for ML Studio Research Track (SRS §9).

Implements the outer split protocol (Development / Locked Test partition) with
rigorous methodological discipline:
- Stratified partition for classification datasets.
- Plain random partition for regression datasets.
- Deterministic seed management for exact experiment reproducibility.

NOTE ON EVALUATION DISCIPLINE:
Locked Test partitions from this split are used EXACTLY ONCE per dataset, at the end of
Days 15-16, to compare all 8 methods' final performance — this is a different use of
"one-time evaluation" than the platform's per-project rule: here, all 8 methods are fixed
in advance and evaluated once each against a shared benchmark, which is standard
comparative-study practice, not the iterative "peek and re-select" pattern the platform's
consumption rule exists to prevent.
"""

from dataclasses import dataclass
import secrets
from typing import Any
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split


@dataclass
class OuterSplitResult:
    """
    Encapsulates outer partition indices and metadata.
    """
    dev_indices: np.ndarray
    locked_test_indices: np.ndarray
    seed: int
    is_stratified: bool
    task_type: str
    locked_test_pct: int
    total_rows: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "dev_indices": self.dev_indices.tolist(),
            "locked_test_indices": self.locked_test_indices.tolist(),
            "seed": self.seed,
            "is_stratified": self.is_stratified,
            "task_type": self.task_type,
            "locked_test_pct": self.locked_test_pct,
            "total_rows": self.total_rows,
        }


def create_split(
    X: pd.DataFrame | np.ndarray,
    y: pd.Series | np.ndarray,
    task_type: str,
    locked_test_pct: int = 20,
    seed: int | None = None,
) -> OuterSplitResult:
    """
    Creates Development and Locked Test partitions.

    Args:
        X: Feature matrix.
        y: Target series or array.
        task_type: "CLASSIFICATION" or "REGRESSION".
        locked_test_pct: Percentage of data allocated to Locked Test partition (default 20%).
        seed: Random seed for deterministic reproducibility. Generated securely if None.

    Returns:
        OuterSplitResult containing dev/test index arrays, seed, and stratification flag.
    """
    if not (1 <= locked_test_pct <= 99):
        raise ValueError("locked_test_pct must be between 1 and 99 percent.")

    n_samples = len(X)
    if n_samples < 2:
        raise ValueError(f"Dataset must have at least 2 rows (got {n_samples}).")

    effective_seed = seed if seed is not None else secrets.randbelow(2_147_483_647)
    test_size = locked_test_pct / 100.0
    row_indices = np.arange(n_samples)

    norm_task = task_type.upper().strip()
    is_stratified = False

    if norm_task == "CLASSIFICATION":
        y_arr = np.asarray(y)
        unique_classes, counts = np.unique(y_arr, return_counts=True)
        # Stratification requires at least 2 samples per class
        if len(unique_classes) > 1 and (counts >= 2).all():
            dev_idx, test_idx = train_test_split(
                row_indices,
                test_size=test_size,
                random_state=effective_seed,
                stratify=y_arr,
            )
            is_stratified = True
        else:
            dev_idx, test_idx = train_test_split(
                row_indices,
                test_size=test_size,
                random_state=effective_seed,
            )
    elif norm_task == "REGRESSION":
        dev_idx, test_idx = train_test_split(
            row_indices,
            test_size=test_size,
            random_state=effective_seed,
        )
    else:
        raise ValueError(f"Unsupported task_type '{task_type}'. Must be 'CLASSIFICATION' or 'REGRESSION'.")

    return OuterSplitResult(
        dev_indices=dev_idx,
        locked_test_indices=test_idx,
        seed=effective_seed,
        is_stratified=is_stratified,
        task_type=norm_task,
        locked_test_pct=locked_test_pct,
        total_rows=n_samples,
    )


def partition_data(
    X: pd.DataFrame,
    y: pd.Series,
    split_result: OuterSplitResult,
) -> tuple[tuple[pd.DataFrame, pd.Series], tuple[pd.DataFrame, pd.Series]]:
    """
    Slices (X, y) into ((X_dev, y_dev), (X_test, y_test)) using an OuterSplitResult.
    """
    X_dev = X.iloc[split_result.dev_indices].reset_index(drop=True)
    y_dev = y.iloc[split_result.dev_indices].reset_index(drop=True)

    X_test = X.iloc[split_result.locked_test_indices].reset_index(drop=True)
    y_test = y.iloc[split_result.locked_test_indices].reset_index(drop=True)

    return (X_dev, y_dev), (X_test, y_test)
