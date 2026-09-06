# Week 2 Milestone: Vertical Slice #1 (Data Ingestion, Immutable Row Identification & Outer Split)

## 1. Executive Summary
Week 2 delivered the fundamental zero-leakage data ingestion and partition architecture for **ML Studio (Stage 2: Data)**. It establishes:
1. **Deterministic Data Ingestion & Storage**: Safe filesystem-backed dataset storage (`StorageService`) with monotonic version incrementing.
2. **Deterministic Identity Layer (`row_uid`)**: Persistent UUIDv5 assignment per row derived from content and row position, decoupling partition membership from raw indices.
3. **Cryptographic Integrity & Deduplication**: SHA-256 `content_hash` computation with strict `UNIQUE(project_id, dataset_content_hash)` guarantees.
4. **Leakage-Isolated Outer Split**: Membership table `dataset_splits` keyed strictly by `row_uid`, guaranteeing zero contamination of the Locked Test partition in any downstream exploratory queries.
5. **Interactive UI & Visual Verification**: Complete Data Stage interface with version history, Stage A schema inspector, outer split locking, and development preview.

---

## 2. Daily Implementations & Verification

### Day 1 — StorageService + Dataset Upload
- **Component**: `backend/app/services/storage_service.py` & `POST /api/v1/datasets/upload`.
- **Functionality**:
  - Validates and stores CSV, XLSX, and JSON files in isolated project storage.
  - Automatically calculates row and column counts.
  - Generates monotonically increasing version numbers (`v1`, `v2`, ...).
  - Creates dataset record with initial stage `RAW`.
- **Tests**: `backend/tests/test_day1_storage_and_upload.py` (6/6 passed).

### Day 2 — Structural Validation & `row_uid` Assignment
- **Component**: `backend/app/services/dataset_service.py` (`detect_structural_schema`, `assign_row_uids`).
- **Functionality**:
  - Infers Stage A data types (`NUMERIC`, `CATEGORICAL`, `DATETIME`, `MIXED`).
  - Computes missing percentage and unique value counts per column strictly without target-aware logic.
  - Generates and persists immutable UUIDv5 `row_uid`s attached to each row in the dataset file.
- **Tests**: `backend/tests/test_day2_structural_validation_and_row_uid.py` (3/3 passed).

### Day 3 — Outer Split via `row_uid` & Content Hashing
- **Component**: `backend/app/services/dataset_split_service.py` (`create_outer_split`, `get_development_data`).
- **Functionality**:
  - Computes 64-character SHA-256 `dataset_content_hash`.
  - Rejects duplicate uploads within the same project with `409 Conflict`.
  - Performs stratified or uniform split, inserting partition memberships (`DEVELOPMENT` vs `LOCKED_TEST`) keyed by `row_uid`.
  - Transitions `ProjectState` from `DATA_UPLOADED` to `SPLIT_LOCKED`.
- **Tests**: `backend/tests/test_day3_outer_split_and_content_hash.py` (7/7 passed).

### Day 4 — Zero-Leakage & Reordering Resilience Invariants
- **Component**: `backend/tests/test_day4_leakage_and_reordering.py`.
- **Key Proofs**:
  - `test_locked_test_indices`: Formally asserts that 0% of Locked Test `row_uids` ever leak into `get_development_data` query results.
  - `test_split_membership_survives_underlying_data_reordering`: Validates that partition memberships remain 100% stable even if raw underlying dataframe rows are randomly shuffled or re-indexed.
- **Tests**: `backend/tests/test_day4_leakage_and_reordering.py` (2/2 passed).

### Day 5 — Data Stage Frontend
- **Component**: `frontend/src/pages/DataStage.jsx` & `frontend/src/App.jsx`.
- **Features**:
  - Project switcher + modal for instant project creation.
  - Drag-and-drop tabular dataset uploader.
  - Version history table with Stage badges, timestamps, and SHA-256 hash copy button.
  - Stage A Structural Schema table with missing value meters and Target indicator.
  - Interactive Outer Split slider and deterministic random seed generator.
  - Real-time development partition preview table.
- **Verification**: Vite production build succeeded in 10.48s with 0 errors.

### Day 6 — Vertical Slice #1 Live Execution
- **Run Target**: `sample_customers.csv` (20 rows × 5 columns, target `churn`).
- **Live Flow Results**:
  1. Authenticated user and selected project `Customer Churn Live Slice`.
  2. Uploaded dataset `sample_customers.csv` (Version `v1`, Hash `21d36fa0ce3d0504...`).
  3. Inferred structural schema: `age` (5% nulls), `income` (10% nulls), `credit_score` (5% nulls), `city` (0% nulls), `churn` (Target).
  4. Locked Outer Split at 20% (`Seed: 42`, `Stratified: True`): 16 Development rows, 4 Locked Test rows.
  5. Verified development preview rendered sample rows with strict Locked Test row isolation.

### Day 7 — Fresh-DB Migration & Regression Verification
- **Alembic Fresh-DB Migration**:
  - Initialized clean SQLite database and executed `alembic upgrade head`.
  - All 10 migration revisions applied successfully from `001_initial_schema` through `010_add_user_permission_overrides`.
- **Regression Test Suite**:
  - Executed `pytest -v` across entire backend test suite.
  - **Result**: `128 passed, 0 failures` (Total test duration: 86.55s).
  - Complete output logged in `week-02/test-report.txt`.

---

## 3. Invariant Matrix

| Requirement | Contract Clause | Implementation Guarantee | Test Proof |
| :--- | :--- | :--- | :--- |
| Immutable Identity | SRS v9 §4 | UUIDv5 `row_uid` attached per row at ingestion | `test_immutable_row_uid_assignment_and_persistence` |
| Zero Contamination | SRS v9 §3 | `dataset_splits` maps `row_uid` to partition; dev queries exclude `LOCKED_TEST` | `test_locked_test_indices` |
| Permutation Resilience | SRS v9 §4 | Membership lookup is keyed by `row_uid`, never row index | `test_split_membership_survives_underlying_data_reordering` |
| Duplicate Rejection | SRS v9 §3 | SHA-256 hash + `UNIQUE(project_id, dataset_content_hash)` | `test_duplicate_dataset_same_project_rejected` |
| State Transition | SRS v9 §5 | `DATA_UPLOADED` $\rightarrow$ `SPLIT_LOCKED` gate enforced | `test_project_state_transitions_data_uploaded_to_split_locked` |
| Migration Completeness | Architecture §2 | All tables generated via reversible Alembic scripts | `alembic upgrade head` on fresh DB |
