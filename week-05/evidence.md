# Phase 5: Feature Engineering — Evidence & Verification Report

**Status:** GREEN  
**Phase:** 5 (Feature Engineering — Four Selectors, Rank Aggregation, Deterministic Tie-Break & Evidence Strength)  
**Date:** 2026-09-10  
**Repository:** ML Studio (`Mangesh19-parate/Intelligent_ML_Studio`)

---

## 1. Executive Summary

Phase 5 delivers the four-technique rank-aggregated feature selection ensemble and deterministic selection engine for **ML Studio (Stage 5: Feature Engineering)**:
- **Four Canonical Selectors:**
  1. `CORRELATION_SELECTOR`: Absolute Pearson / Spearman correlation with target.
  2. `LASSO_SELECTOR`: L1-regularized linear model feature importance ($|\text{coef}|$).
  3. `RANDOM_FOREST_IMPORTANCE_SELECTOR`: Gini impurity / MDI feature importances.
  4. `PERMUTATION_IMPORTANCE_SELECTOR`: Permutation importance over out-of-fold predictions.
- **Strict Per-Fold Fitting (Invariant 1 & 6):** Preprocessing and feature selection are fit strictly inside cross-validation training folds. Validation folds and the Locked Test partition are never exposed.
- **Mathematical Rank Aggregation Formula:**
  $$r_{j,T} = 1 - \frac{\text{rank}_{j,T} - 1}{p - 1} \quad (p > 1, \text{ ties resolved by average rank})$$
  $$\text{EnsembleScore}_j = \frac{1}{|T_{\text{applied}}|} \sum_{T \in T_{\text{applied}}} r_{j,T}$$
- **Proportional Selection (`TOP_K_PERCENT` — ADR-004):**
  $$K = \text{clamp}(\lceil p \times 0.25 \rceil, 5, 50)$$
- **Three-Tier Deterministic Tie-Break Rule:**
  1. Higher `EnsembleScore`
  2. Lower aggregate raw rank sum
  3. Lexicographic feature name ascending
- **Evidence Strength Bands:** Categorized as `STRONG` (4/4 techniques), `MODERATE` (3/4), `LIMITED` (2/4, meets `min_applied_methods`), or `INSUFFICIENT_EVIDENCE` (< 2).
- **Platform Scope Boundary (ADR-005):** `RANK_AGGREGATION_STABILITY` is restricted to the research track; requests to the platform API are rejected with HTTP `400 Bad Request`.

---

## 2. Definition of Done (DoD) Checklist

| Item | Requirement | Verification / Evidence | Status |
|---|---|---|---|
| **DoD-1** | Four selectors execute across classification and regression | `tests/test_feature_selection.py`, `tests/test_day1_selectors.py` | **PASS** |
| **DoD-2** | Rank aggregation formula handles ties via average ranking and $p=1$ edge case | `tests/test_feature_selection.py::test_rank_aggregation_ties_average_ranking` | **PASS** |
| **DoD-3** | Proportional `TOP_K_PERCENT` selection with $k_{\text{min}}=5$ and $k_{\text{max}}=50$ clamps | `tests/test_day3_selectors.py` | **PASS** |
| **DoD-4** | 3-tier deterministic tie-break guarantees byte-identical output across runs | `tests/test_day4_selectors.py` | **PASS** |
| **DoD-5** | Evidence strength correctly categorized (`STRONG`, `MODERATE`, `LIMITED`, `INSUFFICIENT_EVIDENCE`) | `tests/test_day2_selectors.py` | **PASS** |
| **DoD-6** | Platform API rejects `RANK_AGGREGATION_STABILITY` with HTTP 400 | `tests/test_day5_selectors.py` | **PASS** |
| **DoD-7** | Zero leakage across CV folds and 0% Locked Test access | `tests/test_feature_selection.py::test_cv_feature_selection_classification_end_to_end` | **PASS** |
| **DoD-8** | Full multi-vector test suite verifying numerical edge cases and zero-variance features | `tests/test_week5_vector_suite.py` | **PASS** |
| **DoD-9** | Feature selection importance scores live editable via API | `tests/test_feature_selection.py::test_api_feature_selection_endpoints` | **PASS** |
| **DoD-10**| Feature Engineering UI in Mastercard theme with interactive importance charts | `frontend/src/pages/FeatureEngineeringStage.jsx` | **PASS** |

---

## 3. Automated Test Suite Execution

```
============================= test session starts =============================
platform win32 -- Python 3.13.14, pytest-8.3.5, pluggy-1.6.0
rootdir: D:\Python\Data sets by campusx\Mangesh\backend
plugins: anyio-4.14.2, cov-7.1.0, flask-1.3.0
collected 79 items

tests\test_feature_selection.py ...........                              [ 13%]
tests\test_day1_selectors.py ..................                          [ 36%]
tests\test_day2_selectors.py .............                               [ 53%]
tests\test_day3_selectors.py ..............                              [ 70%]
tests\test_day4_selectors.py .....                                       [ 77%]
tests\test_day5_selectors.py ....                                        [ 82%]
tests\test_day6_selectors.py ......                                      [ 89%]
tests\test_week5_vector_suite.py ........                                [100%]

======================= 79 passed, 4 warnings in 36.37s =======================
```

---

## 4. Key Architectural Guarantees Established

1. **Deterministic Selection at the $K$ Boundary:**
   - Evaluates (1) `EnsembleScore` descending, (2) `rank_sum` ascending, and (3) `column_name` ASCII ascending.
   - Guaranteed byte-identical subset reproduction for identical seed and data.

2. **Platform Boundary Enforcement (ADR-005):**
   - The platform API strictly accepts `RANK_AGGREGATION`.
   - Stability-aware selection (`RANK_AGGREGATION_STABILITY`) requires a repeated-run population that only the Week 11 research runner generates.
