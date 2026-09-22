# Intelligent ML Studio: Architectural Claims Matrix

This matrix provides the single source of truth connecting every high-level architectural claim to its concrete codebase implementation, automated verification test, and empirical status.

| # | Architectural Claim | Technical Mechanism | Code Location | Verification Test / Script | Status |
|---|---|---|---|---|:---:|
| **1** | **Zero Test Partition Leakage Invariants Verified** | Preprocessing scalers, imputers, and selectors fit exclusively on training folds; non-learned / pre-fitted transforms on Locked Test | `apps/backend/app/services/experiment_service.py`<br>`apps/backend/app/services/transformation_service.py` | `apps/backend/tests/test_system_integrity.py`<br>`apps/backend/tests/test_day4_leakage_and_reordering.py` | **ZERO_LEAKAGE_INVARIANTS_VERIFIED** |
| **2** | **Deterministic Snapshot Reproduction** | Pipelines rebuilt strictly from immutable JSON snapshot configs rather than live project state | `apps/backend/app/services/transformation_service.py`<br>`apps/backend/app/services/experiment_service.py` | `apps/backend/tests/test_lineage_and_reproducibility.py`<br>`apps/backend/tests/test_system_integrity.py` | **VERIFIED** |
| **3** | **Persisted Reproducibility Audit** | Every deterministic replay creates an immutable `ReproducibilityRun` record without touching Locked Test or polluting Experiment tables | `apps/backend/app/models/reproducibility.py`<br>`apps/backend/app/services/experiment_service.py` | `apps/backend/tests/test_system_integrity.py` (`test_reproducibility_run_persists_audit_record`) | **VERIFIED** |
| **4** | **Two-Role Atomic RBAC** | Strict two-role architecture (`ADMIN`, `USER`) with granular `UserPermissionOverride` records; legacy roles purged | `apps/backend/app/models/role.py`<br>`apps/backend/app/models/user_permission_override.py`<br>`apps/backend/app/core/seeder.py` | `apps/backend/tests/test_system_integrity.py` (`test_stale_roles_absent_in_database`) | **VERIFIED** |
| **5** | **Four-Eyes Deployment Governance** | Model creators cannot approve their own models (`approved_by != created_by` enforced server-side; HTTP 403 on self-approval) | `apps/backend/app/services/deployment_gate_service.py`<br>`apps/backend/app/api/v1/deployments.py` | `apps/backend/tests/test_system_integrity.py` (`test_four_eyes_separation_of_duties_governance`) | **VERIFIED** |
| **6** | **Deterministic Tie-Breaking** | Ensemble feature selection resolves rank collisions via 3-tier ordering: `(-score, votes, column_name)` with `TOP_K_PERCENT` | `apps/backend/app/services/selectors.py`<br>`apps/backend/app/services/feature_selection_service.py` | `apps/backend/tests/test_system_integrity.py` (`test_deterministic_top_k_resolution_and_tie_breaking`) | **VERIFIED** |
| **7** | **Single Locked Test Consumption** | Locked Test partition evaluated at most once per experiment; subsequent accesses flagged as `TEST_REUSED_DIAGNOSTIC` | `apps/backend/app/services/experiment_service.py`<br>`apps/backend/app/services/evaluation_service.py` | `apps/backend/tests/test_day4_locked_test_consumption.py` | **VERIFIED** |
| **8** | **Out-of-Fold Threshold Tuning** | Classification decision threshold tuned exclusively on Out-of-Fold validation probabilities prior to Locked Test evaluation | `apps/backend/app/services/experiment_service.py`<br>`apps/backend/app/services/trainers.py` | `apps/backend/tests/test_day3_threshold_selection.py` | **VERIFIED** |
| **9** | **Cryptographic Model Passport** | Read-only passport retrieval verifying dataset SHA-256, pipeline hash, and artifact checksum with zero SQL mutations | `apps/backend/app/services/model_passport_service.py` | `apps/backend/tests/test_system_integrity.py` (`test_model_passport_zero_mutation_guarantee`) | **VERIFIED** |
| **10** | **Preregistered Research Protocol** | Stability-aware feature selection evaluated across 320 CV runs with frozen $\alpha=0.7$ and meaningful $\Delta S \ge 0.05$ threshold | `research/config/protocol.yaml`<br>`research/statistical_analysis.py` | `research/acceptance_check.py` | **VERIFIED** |
| **11** | **Durable Asynchronous Execution** | Database-backed task records (`durable_tasks`) surviving worker crashes, with active timeout execution termination and idempotent submission | `apps/backend/app/models/durable_task.py`<br>`apps/backend/app/tasks/experiment_tasks.py` | `apps/backend/tests/test_durable_tasks.py` | **VERIFIED** |
| **12** | **Persisted Per-Fold Provenance** | Every fold execution logs cryptographic SHA-256 row hashes and verifies zero locked-test access at the database boundary | `apps/backend/app/models/feature_selection_fold_result.py`<br>`apps/backend/app/repositories/experiment_repository.py` | `apps/backend/tests/test_feature_selection_isolation.py` | **VERIFIED** |

---

### Test Suite Execution Methodology

- **Total Backend Test Cases**: 422 unique test functions executing 490 parametrized cases.
- **Total Frontend Test Cases**: 51 component & flow tests.
- **Execution Command**: `cd apps/backend && pytest -v` / `cd apps/frontend && npm test`
