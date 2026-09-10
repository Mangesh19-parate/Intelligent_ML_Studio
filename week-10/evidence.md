# Phase 10: Assurance — Consolidated Invariants, Attack Lab & Research Dry-Run

**Milestone:** Phase 10 (Week 10) — Assurance Stage  
**Status:** COMPLETE & VERIFIED  
**Date:** September 10, 2026  
**Repository:** `Intelligent_ML_Studio`  

---

## 1. Executive Summary

Phase 10 provides full architectural assurance and adversarial verification for Intelligent ML Studio across three core pillars:
1. **Consolidated Invariant Test Suite:** Unified verification across all 8 core platform invariant domains (SRS §1, §2, §5, §6, §13).
2. **Leakage Attack Lab:** Manifest-gated comparative evaluation instrument demonstrating 4 distinct leakage attack vectors against identical conditions, proving the platform's controls hold and prevent leakage (Testing.md §52, ADR-013).
3. **Research Runner Dry-Run:** Full-matrix dry run of the pre-registered research runner across 4 benchmark datasets, 8 feature selection methods, 2 repeats, and 5 folds (320 runs exported to SQLite and Parquet).

---

## 2. Consolidated Invariant Verification Domains

| Domain | Invariant | Description | Test Status |
|---|---|---|---|
| **Domain 1** | Locked-Test Disjointness & Reordering | Row UIDs strictly separated; arbitrary physical row shuffling preserves split integrity | PASSED |
| **Domain 2** | Fit Scope Isolation | Transformers & feature selectors fit strictly within training fold / development slices | PASSED |
| **Domain 3** | Deterministic Tie-Breaks | 3-tier sort (`-score` $\rightarrow$ `+rank_sum` $\rightarrow$ `+name`) & threshold distance to 0.5 | PASSED |
| **Domain 4** | Platform Scope Boundary | API strictly returns HTTP 400 for `RANK_AGGREGATION_STABILITY` (research-only) | PASSED |
| **Domain 5** | Out-of-Fold Decision Threshold | Optimal decision threshold tuned strictly on OOF predictions and frozen pre-test | PASSED |
| **Domain 6** | Locked Test Consumption | Single authoritative test evaluation; subsequent calls tagged `TEST_REUSED_DIAGNOSTIC` | PASSED |
| **Domain 7** | Concurrency Lock Mutex | Atomic state check; simultaneous training attempts rejected with HTTP 409 Conflict | PASSED |
| **Domain 8** | State Legality vs Gate Eligibility | Pure architectural separation between state machine legality and substantive gate checks | PASSED |

---

## 3. Leakage Attack Lab — Comparative Evaluation (§52, ADR-013)

### Shared Experiment Manifest (`week-10/artifacts/attack_lab_manifest.json`)
- **Dataset:** Synthetic Leakage Benchmark ($N=200, D=20$, Content Hash: `81829e...`)
- **Outer Split:** 80% Development ($N=160$), 20% Locked Test ($N=40$)
- **CV Configuration:** 5-Fold Cross-Validation, Base Seed: `42`

### Structured Attack Results Summary

| Attack ID | Attack Name | Expected Effect | Broken Pipeline (CV / Test) | Studio Control Result | Result |
|---|---|---|---|---|---|
| **ATK-01** | Global Preprocessing Scaling | Test set distribution statistics contaminate training folds | CV RMSE: `0.5423`<br>Test RMSE: `0.6186`<br>Gap: `0.0763` | Scaler fit strictly inside folds<br>Clean CV RMSE: `0.5423`<br>Clean Test RMSE: `0.6183` | **ATTACK CONFIRMED & CONTROL HELD** |
| **ATK-02** | Supervised Feature Selection Pre-CV | Selection bias deflates CV error by peeking at validation/test targets | CV RMSE: `0.4954`<br>Test RMSE: `0.5571`<br>Gap: `0.0617` | Selectors fit strictly inside folds<br>Clean CV RMSE: `0.5432` | **ATTACK CONFIRMED & CONTROL HELD** |
| **ATK-03** | Decision Threshold Test Peeking | Tuning classification threshold on test split creates post-hoc optimism bias | Leaked Test Thresh: `0.38`<br>Inflated Test F1: `0.9250` | Frozen OOF Thresh: `0.50`<br>Honest Test F1: `0.9000`<br>Optimism Inflation: `+0.0250` | **ATTACK CONFIRMED & CONTROL HELD** |
| **ATK-04** | Test Split Model Selection Reuse | Iterative peeking on test split degrades test set into validation set | Multiple test finalizations accepted unchecked | Single consumption rule;<br>Repeat evaluations tagged `TEST_REUSED_DIAGNOSTIC` | **ATTACK CONFIRMED & CONTROL HELD** |

---

## 4. Research Runner Dry-Run Verification

- **Datasets:** California Housing, Bike Sharing, Breast Cancer, Adult Income (4 datasets)
- **Methods:** `NO_SELECTION`, `CORRELATION`, `LASSO`, `RANDOM_FOREST`, `PERMUTATION`, `RFE`, `RANK_AGGREGATION`, `RANK_AGGREGATION_STABILITY` (8 methods)
- **Folds & Repeats:** 5 Folds $\times$ 2 Repeats = 10 runs per dataset/method
- **Total Executions:** 320 runs
- **Output Storage:** `research/results.db` (SQLite) and `research/runs.parquet`

---

## 5. Automated Test Verification Results

```bash
pytest tests/test_attack_lab.py tests/test_consolidated_invariants.py -v
```

**Outcome:** `11 passed in 4.41s` (0 failed, 0 warnings).
