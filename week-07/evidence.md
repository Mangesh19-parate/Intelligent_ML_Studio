# Phase 7: Evaluation — Evidence & Verification Report

**Status:** GREEN  
**Phase:** 7 (Evaluation — Metrics, Leaderboard, Out-of-Fold Threshold & Locked Test Consumption)  
**Date:** 2026-09-10  
**Repository:** ML Studio (`Mangesh19-parate/Intelligent_ML_Studio`)

---

## 1. Executive Summary

Phase 7 delivers the rigorous, leakage-safe model evaluation, diagnostic fit assessment, and single-use Locked Test evaluation protocol for **ML Studio (Stage 7: Evaluation)**:
- **Authoritative Metrics Engine:**
  - **Regression:** Default primary `rmse` (MINIMIZE), alternate `mae`, secondary `mse`, `r2`, `adjusted_r2`.
  - **Classification:** Default primary `macro_f1` (MAXIMIZE), alternate `weighted_f1`, secondary `accuracy`, `precision`, `recall`, `roc_auc`, `log_loss`, `confusion_matrix`.
- **Out-of-Fold Threshold Optimization (Invariant 6):**
  - Decision threshold tuning for binary classification operates strictly over **out-of-fold Development predictions**.
  - No prediction used in threshold search ever originates from a fold that was trained on that sample.
- **Sacred Locked Test Single-Consumption Invariant (Invariant 2):**
  - Winning model evaluates the Locked Test partition **exactly once** upon finalization.
  - The partition is permanently marked consumed. Repeat evaluation attempts return `TEST_REUSED_DIAGNOSTIC` and are banned from mutating authoritative scores.
- **Fit Diagnosis Engine (FR-8):**
  - Classifies models into `GOOD_FIT`, `POTENTIAL_OVERFIT`, `POTENTIAL_UNDERFIT_WEAK_SIGNAL`, or `INSUFFICIENT_DATA` based on cross-validation vs training discrepancy bounds.
- **State Progression:**
  - `ExperimentState.EVALUATED` $\rightarrow$ `TEST_CONSUMED` $\rightarrow$ `REGISTERED`.

---

## 2. Definition of Done (DoD) Checklist

| Item | Requirement | Verification / Evidence | Status |
|---|---|---|---|
| **DoD-1** | Metric computation accuracy across all regression & classification metrics | `tests/test_day1_metrics.py` | **PASS** |
| **DoD-2** | Adjusted $R^2$ formula respects sample size and feature count | `tests/test_evaluation_and_locked_test.py::test_acceptance_check_h_adjusted_r2_formula` | **PASS** |
| **DoD-3** | Out-of-fold threshold tuning uses only held-out fold predictions | `tests/test_day3_threshold_selection.py` | **PASS** |
| **DoD-4** | Single Locked Test evaluation on winning model with full Development refit | `tests/test_evaluation_and_locked_test.py::test_acceptance_check_a_d_e_single_locked_test_and_full_dev_refit` | **PASS** |
| **DoD-5** | Repeat Locked Test evaluation rejected with `TEST_REUSED_DIAGNOSTIC` (409 Conflict) | `tests/test_evaluation_and_locked_test.py::test_acceptance_check_b_finalize_twice_rejected` | **PASS** |
| **DoD-6** | Leaderboard sorting remains strictly dictated by the frozen primary metric | `tests/test_evaluation_and_locked_test.py::test_acceptance_check_g_model_selection_score_never_changes_sort_order` | **PASS** |
| **DoD-7** | Automated fit diagnosis flags overfit, underfit, and weak signals | `tests/test_evaluation_and_locked_test.py::test_acceptance_check_f_overfit_and_underfit_diagnostics` | **PASS** |
| **DoD-8** | Permanent Locked Test consumption tracking in database & state machine | `tests/test_day4_locked_test_consumption.py` | **PASS** |
| **DoD-9** | Leaderboard UI with metric cards, ROC curves, and confusion matrix visualizer | `frontend/src/pages/MLStage.jsx` | **PASS** |
| **DoD-10**| State transition: `EVALUATED` $\rightarrow$ `TEST_CONSUMED` $\rightarrow$ `REGISTERED` | `tests/test_day4_locked_test_consumption.py` | **PASS** |

---

## 3. Automated Test Suite Execution

```
============================= test session starts =============================
platform win32 -- Python 3.13.14, pytest-8.3.5, pluggy-1.6.0
rootdir: D:\Python\Data sets by campusx\Mangesh\backend
plugins: anyio-4.14.2, cov-7.1.0, flask-1.3.0
collected 34 items

tests\test_evaluation_and_locked_test.py ......                          [ 17%]
tests\test_day1_metrics.py .....                                         [ 32%]
tests\test_day2_leaderboard_and_diagnostics.py ..........                [ 61%]
tests\test_day3_threshold_selection.py ........                          [ 85%]
tests\test_day4_locked_test_consumption.py .....                         [100%]

============================= 34 passed in 22.78s =============================
```

---

## 4. Key Invariants & Architectural Proofs

1. **Sacred Locked Test Partition (Invariant 2):**
   - Locked Test partition is evaluated once and only once per experiment generation upon winning model finalization.
   - Any subsequent call receives `TEST_REUSED_DIAGNOSTIC` flag, preserving data isolation.

2. **Out-of-Fold Threshold Isolation (Invariant 6):**
   - Threshold sweep searches candidate cutoffs using out-of-fold validation predictions exclusively.
   - Training fold and test fold data never touch threshold optimization.
