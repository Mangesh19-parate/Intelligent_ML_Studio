# Data Leakage Prevention Architecture

## Core Invariants

1. **Immutable Partition Isolation**:
   - Tabular datasets are partitioned deterministically into an 80% Development set and a 20% Locked Holdout Test set.
   - The partition is sealed via row-hash verification and persisted to `dataset_splits`.
   - Estimators, scalers, imputers, and feature selectors **never** receive the Locked Holdout partition during CV or hyperparameter search.

2. **Fold-Isolated Feature Engineering & Selection**:
   - All transformations and feature selectors fit **strictly on fold-train slices** ($k-1$ folds).
   - Validation folds are transformed using the estimators fitted on the corresponding training slice.
   - Target columns are excluded from feature matrices.

3. **Locked Test Single-Consumption Invariant**:
   - Evaluation on the locked holdout test partition is permitted **strictly once** per champion model upon experiment finalization.
   - The token is atomically consumed (`locked_test_consumed = true`). Subsequent evaluation requests fail with HTTP 400 Bad Request.

4. **Mathematical SHAP Additivity**:
   - Model predictions equal the sum of local feature contributions plus the expected base value:
     $$\sum_{i=1}^{M} \phi_i(x) = f(x) - E[f(x)]$$
   - Verified by automated regression tests.
