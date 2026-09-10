# ML Studio - Testing

## Test Categories

**Invariant tests** (written incrementally as each invariant is implemented, not batched at the end):

```
test_locked_test_indices           - Locked Test row_uids never appear in Development queries
test_transformer_fit_scope         - transformer unfit until called inside CV
test_selector_fit_scope-equivalent - same, for feature selectors
test_tie_break_determinism         - identical inputs/config/seed -> byte-identical output
test_stability_method_rejection    - platform API rejects RANK_AGGREGATION_STABILITY (400)
test_out_of_fold_threshold         - no threshold-search prediction from a training fold
test_test_reuse                    - repeat Locked Test evaluation -> TEST_REUSED_DIAGNOSTIC
test_threshold_not_from_test       - frozen threshold never changes based on Locked Test data
test_concurrency_lock              - second simultaneous TRAINING start on one experiment rejected
test_no_role_name_authorization    - static scan, regression heuristic (not a security proof)
test_dataset_hash_ordering         - identical content -> identical hash regardless of row_uid
test_state_legality_vs_gate        - state machine and gate service tested independently
```

**Reproducibility tests:**

```
test_same_config_same_result  - Reproduce-Experiment diff within the frozen tolerance
                                 (metric_absolute_tolerance=1e-3, metric_relative_tolerance=0.01)
test_reproduce_non_mutating   - source experiment's state/metrics unchanged after /reproduce
test_dataset_hash_validation  - artifact checksum verified on load
```

**Transaction/failure tests:**

```
test_artifact_write_failure         - no DB row without a matching artifact
test_db_commit_failure_after_write  - orphaned artifact cleanup, or ORPHANED_RECOVERABLE logged
```

**Governance tests:**

```
test_self_approval_rejected     - approved_by == created_by blocked, server-side, no ADMIN bypass
test_model_eligibility_blocks   - forcing one of the five gate conditions to fail blocks DEPLOYABLE
```

**Migration tests:**

```
alembic upgrade head against a freshly created, empty database - not the long-running dev DB -
run at minimum at the end of Phases 1, 2, 6, 9, 12
```

## Adversarial Testing - the Leakage Attack Lab

Not a unit-test suite; a comparative evaluation instrument. Every attack variant and the correct-pipeline comparator share an `attack_lab_manifest.json` (dataset id/version/hash, target, outer split, metric, seed) - only the leakage mechanism differs between compared runs. Reported format: Attack / Expected effect / Observed (CV metric, Test metric, gap) / Control (which invariant blocks it) / Result. The actual gap is reported regardless of magnitude - a small or near-zero gap is still valid evidence that the attack was real and the control held; the pass condition is "attack confirmed and comparison recorded," not "dramatic inflation observed" (see `Decision.md` ADR-013).

## Research Statistical Testing

Paired per-dataset performance differences (median, mean, 95% CI where feasible) between the proposed method and each baseline, computed only from the primary fixed-model comparison (see `Decision.md` ADR-014). Wilcoxon signed-rank applied only where paired-observation assumptions hold. Conclusions reported as "across the evaluated benchmark datasets," never as a universal claim, given the small dataset count. Either outcome (supported / not supported) is reported honestly.

## Evidence Standard

Every phase's evidence lands in a standard directory, checked by a human before the next phase begins - never accepted on the agent's own "done" claim:

```
week-NN/
  evidence.md
  test-report.txt
  artifacts/
  screenshots/
  logs/
```

## Weekly Regression Discipline

```
GREEN  - DoD passed + automated test exists + evidence artifact captured
YELLOW - core works, one or more DoD items failed - next phase starts by fixing them first
RED    - a P0 invariant is broken - stop all new feature work until fixed and retested
```

A failing test or a missing/mismatched evidence artifact means the current task is incomplete, per `Agents.md`'s Agent Failure Protocol - work does not proceed to the next day's or phase's tasks regardless.
