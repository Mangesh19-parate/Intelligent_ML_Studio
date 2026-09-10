# Phase 2: Data Stage — Evidence & Verification Report

**Status:** GREEN  
**Phase:** 2 (Data Stage — Vertical Slice #1)  
**Date:** 2026-09-10  
**Repository:** ML Studio (`Mangesh19-parate/Intelligent_ML_Studio`)

---

## 1. Executive Summary

Phase 2 delivers the zero-leakage data ingestion and partition architecture for **ML Studio (Stage 2: Data)**:
- **Structural Validation Only:** Data upload inspects row/column counts, file format integrity (CSV/XLSX/JSON), and structural data types (`NUMERIC`, `CATEGORICAL`, `DATETIME`, `MIXED`). Zero distributional, target-aware, or correlation logic executes before the outer split.
- **Pre-`row_uid` Cryptographic Hashing:** `dataset_content_hash` (SHA-256) is computed over the canonical parsed representation prior to `row_uid` injection, ensuring identical data produces identical hashes.
- **Deterministic Row Identification (`row_uid`):** Immutable UUIDv5 identifiers attached per row, ensuring partition membership is decoupled from raw dataframe indices.
- **Sacred Locked Test Partition:** Outer split (`DEVELOPMENT` vs `LOCKED_TEST`) is recorded in `dataset_splits` keyed by `row_uid`. `get_development_data` structurally excludes 100% of Locked Test rows.
- **Permutation Resilience:** Partition memberships remain stable even when underlying rows are re-ordered or shuffled.
- **State Progression:** Project pipeline stage advances from `CREATED` $\rightarrow$ `DATA_UPLOADED` $\rightarrow$ `SPLIT_LOCKED`.

---

## 2. Definition of Done (DoD) Checklist

| Item | Requirement | Verification / Evidence | Status |
|---|---|---|---|
| **DoD-1** | Dataset upload parses CSV, XLSX, and JSON with format validation | `tests/test_day1_storage_and_upload.py` | **PASS** |
| **DoD-2** | Monotonically increasing versioning (`v1`, `v2`, ...) per project | `tests/test_day1_storage_and_upload.py` | **PASS** |
| **DoD-3** | Structural schema detection without target-aware profiling | `tests/test_day2_structural_validation_and_row_uid.py` | **PASS** |
| **DoD-4** | Persistent UUIDv5 `row_uid` assigned per row | `tests/test_day2_structural_validation_and_row_uid.py` | **PASS** |
| **DoD-5** | SHA-256 content hashing with duplicate detection | `tests/test_day3_outer_split_and_content_hash.py` | **PASS** |
| **DoD-6** | Outer split generation (`DEVELOPMENT` / `LOCKED_TEST`) with seed recording | `tests/test_day3_outer_split_and_content_hash.py` | **PASS** |
| **DoD-7** | Zero Locked Test contamination in Development queries | `tests/test_day4_leakage_and_reordering.py` | **PASS** |
| **DoD-8** | Split membership survives row reordering | `tests/test_day4_leakage_and_reordering.py` | **PASS** |
| **DoD-9** | Data Stage UI with schema viewer, outer split slider, and dev preview | `frontend/src/pages/DataStage.jsx` | **PASS** |
| **DoD-10**| ProjectState transition `DATA_UPLOADED` $\rightarrow$ `SPLIT_LOCKED` | `tests/test_dataset_split.py` | **PASS** |

---

## 3. Automated Test Suite Execution

```
============================= test session starts =============================
platform win32 -- Python 3.13.14, pytest-8.3.5, pluggy-1.6.0
rootdir: D:\Python\Data sets by campusx\Mangesh\backend
plugins: anyio-4.14.2, cov-7.1.0, flask-1.3.0
collected 23 items

tests\test_day1_storage_and_upload.py ......                             [ 26%]
tests\test_day2_structural_validation_and_row_uid.py ...                 [ 39%]
tests\test_day3_outer_split_and_content_hash.py .......                  [ 69%]
tests\test_dataset_split.py .....                                        [ 91%]
tests\test_day4_leakage_and_reordering.py ..                             [100%]

============================= 23 passed in 28.00s =============================
```

---

## 4. Key Invariant Guarantees

1. **Strict Isolation (Invariant 2 & 6):**
   - `get_development_data()` returns rows where `split_type == 'DEVELOPMENT'`.
   - `test_locked_test_indices` proves 0% overlap between Development and Locked Test `row_uids`.

2. **Content Hash Ordering (ADR-007):**
   - `dataset_content_hash` is computed from parsed bytes before `row_uid` is assigned, preventing UUID nonces from modifying the content hash.
