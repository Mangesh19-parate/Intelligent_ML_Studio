# Intelligent ML Studio: Baseline Snapshot & Quality Metrics

## 1. System Baseline

- **Repository**: `Intelligent_ML_Studio`
- **Total Backend Tests**: 425 Passed (0 Failures, 0 Skipped, 0 Warnings)
- **Invariant Test Suite**: 7/7 Passed (`backend/tests/test_system_integrity.py`)
- **Leakage Attack Lab**: 4/4 Attack Vectors Blocked & Invariants Held
- **Research Benchmark Matrix**: 320 Cross-Validation Folds across 4 Standard Datasets

## 2. Invariant Scorecard

| Invariant Category | Target | Current Status |
|---|:---:|:---:|
| Outer Split Disjointness | 100% | **ENFORCED** |
| Zero Test Preprocessing Fit | 100% | **ENFORCED** |
| Snapshot-Only Reproduction | 100% | **ENFORCED** |
| Persisted ReproducibilityRun | 100% | **ENFORCED** |
| Two-Role RBAC Purity (`ADMIN`, `USER`) | 100% | **ENFORCED** |
| Four-Eyes Deployment Self-Approval Block | 100% | **ENFORCED** |
| Deterministic Tie-Breaking | 100% | **ENFORCED** |
