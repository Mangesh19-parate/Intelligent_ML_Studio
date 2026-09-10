# Phase 8: Lineage & Diagnostics — Evidence & Verification Report

**Status:** GREEN  
**Phase:** 8 (Lineage, Diagnostics, Reproduce-Experiment, SHAP & Model Passport — Checkpoint 2: MVP Complete)  
**Date:** 2026-09-10  
**Repository:** ML Studio (`Mangesh19-parate/Intelligent_ML_Studio`)

---

## 1. Executive Summary

Phase 8 delivers the end-to-end model governance, cryptographic lineage tracking, non-mutating reproducibility engine, and explainability layer for **ML Studio (Stage 6: Diagnostics & Checkpoint 2 — MVP Complete)**:
- **Immutable Cryptographic Lineage Chain (Invariants 3 & 4):**
  Every model captured on `trained_models` carries the deterministic tuple:
  $$\text{Model} \longrightarrow \text{Experiment} \longrightarrow \text{Dataset Hash} \longrightarrow \text{Seeds} \longrightarrow \text{Library Versions} \longrightarrow \text{Artifact Checksum}$$
- **Non-Mutating `Reproduce-Experiment` Engine (ADR-008):**
  - Replays cross-validation strictly on the `DEVELOPMENT` partition.
  - Zero access to the Locked Test partition; zero mutation of the original experiment record.
  - Evaluates metric discrepancy against frozen tolerances:
    $$\text{within\_tolerance}(E, O) \iff |O - E| \le \max(10^{-3}, 0.01 \times |E|)$$
- **SHAP Diagnostics & Explainability:**
  - Computes global feature importance summaries (`TreeExplainer` / `KernelExplainer`) cached under object storage.
  - Evaluates strictly over Development partition samples; 0% test set contamination.
- **Model Passport Card (Design.md):**
  - Read-only governance identity card displaying model identity, dataset hash, task, evaluation metrics, feature selection evidence strength, environment versions, git commit, artifact checksum, and gate readiness.
- **Experiment Health Report (Design.md):**
  - Distinguishes structural guarantees (held by construction) from per-experiment risk signals (fit diagnosis, evidence strength, Locked Test status, checksum verification).
- **Checkpoint 2 (MVP Complete):** All core workbench stages functional end-to-end with verified zero leakage.

---

## 2. Definition of Done (DoD) Checklist

| Item | Requirement | Verification / Evidence | Status |
|---|---|---|---|
| **DoD-1** | Lineage capture records real system library versions (Python, sklearn, numpy, pandas) | `tests/test_lineage_and_reproducibility.py::test_acceptance_check_a_live_capture_and_real_versions` | **PASS** |
| **DoD-2** | SHA-256 artifact checksum verification & tamper detection | `tests/test_lineage_and_reproducibility.py::test_acceptance_check_b_artifact_checksum_and_tamper_detection` | **PASS** |
| **DoD-3** | Immutability of transformation and feature selection snapshots | `tests/test_lineage_and_reproducibility.py::test_acceptance_check_c_transformation_snapshot_immutability` | **PASS** |
| **DoD-4** | Non-mutating `Reproduce-Experiment` verifies reproducibility within frozen tolerance | `tests/test_lineage_and_reproducibility.py::test_lineage_api_endpoint` | **PASS** |
| **DoD-5** | Global SHAP summary values computed on Development data and cached | `tests/test_explainability.py::test_acceptance_check_a_global_shap_summary_and_caching` | **PASS** |
| **DoD-6** | Tampered artifact rejection during explainability computation | `tests/test_explainability.py::test_acceptance_check_f_tampered_artifact_rejection` | **PASS** |
| **DoD-7** | Model Passport renders complete lineage without recomputing models | `tests/test_checkpoint2_model_passport_and_e2e.py::test_model_passport_strict_select_and_zero_recomputation` | **PASS** |
| **DoD-8** | Experiment Health Report formats structural guarantees vs variable risk signals | `tests/test_day7_experiment_health_report.py` | **PASS** |
| **DoD-9** | Checkpoint 2 full live pipeline end-to-end execution | `tests/test_checkpoint2_model_passport_and_e2e.py::test_checkpoint2_full_pipeline_live_and_invariants` | **PASS** |
| **DoD-10**| Diagnostics & Model Passport UI in Mastercard design theme | `frontend/src/pages/DiagnosticsStage.jsx` | **PASS** |

---

## 3. Automated Test Suite Execution

```
============================= test session starts =============================
platform win32 -- Python 3.13.14, pytest-8.3.5, pluggy-1.6.0
rootdir: D:\Python\Data sets by campusx\Mangesh\backend
plugins: anyio-4.14.2, cov-7.1.0, flask-1.3.0
collected 30 items

tests\test_lineage_and_reproducibility.py ................               [ 53%]
tests\test_explainability.py ........                                    [ 80%]
tests\test_checkpoint2_model_passport_and_e2e.py ...                     [ 90%]
tests\test_day7_experiment_health_report.py ...                          [100%]

====================== 30 passed, 16 warnings in 41.06s =======================
```

---

## 4. Key Architectural Guarantees Established

1. **Non-Mutating Replay (ADR-008):**
   - `POST /api/v1/experiments/{id}/reproduce` creates an isolated `reproducibility_runs` record.
   - Evaluates CV folds against the frozen numerical tolerance without modifying the source experiment state or accessing the Locked Test partition.

2. **Transaction Integrity (Rules.md):**
   - Artifacts are saved to disk and SHA-256 verified before the database row is committed.
   - Prevents orphaned database records pointing to invalid or missing joblib binaries.
