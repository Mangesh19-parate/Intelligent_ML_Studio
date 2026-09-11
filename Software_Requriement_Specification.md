# ML Studio — SRS v10 (Terminal Canonical Specification)
### Supersedes v4 through v9 in full. This is the final specification revision. Further changes should come only from implementation discovering an actual defect against this document — not from further design review.

---

## 0. Changelog from v9

| Fix | Section |
|---|---|
| Reproduce-Experiment redefined as a non-mutating, CV-only diagnostic replay — never touches Locked Test, never creates a new reportable model-selection event | §1 |
| `RANK_AGGREGATION_STABILITY` given explicit four-phase execution order | §2 |
| Dataset hashing sequenced explicitly relative to `row_uid` assignment | §3 |
| `ModelState.DEPLOYABLE` ownership made explicit — split gate conditions into model-level eligibility (owned by the gate service) vs. deployment-specific approval | §4 |
| Admission-control (pre-execution, predictable) features formally separated from benchmark observations (post-execution, measured) | §5 |
| Role-authorization test reframed as a regression heuristic, not a security guarantee | §6 |
| DFD wording: state/transition legality is not a Diagnostics responsibility | (see DFD v10) |

---

## 1. Reproduce-Experiment — Non-Mutating Diagnostic Replay (redefined)

`run_experiment()` is the canonical full lifecycle runner (CV → model selection → refit → Locked Test → registration). Calling it naively for reproduction risked re-consuming the Locked Test, creating a second reportable evaluation, or mutating the original experiment — all of which would violate the test-consumption invariant in the name of proving reproducibility.

**Fixed: Reproduce-Experiment runs a distinct, restricted mode — CV-only, Development-only, non-mutating:**

```
POST /experiments/{id}/reproduce
  → creates a REPRODUCIBILITY_RUN record (a new entity, not a new Experiment):
      reproducibility_run_id, source_experiment_id, expected_metric, observed_metric,
      difference, tolerance_used, status (REPRODUCIBLE_WITHIN_TOLERANCE / NOT_REPRODUCIBLE)
  → internally: re-executes ONLY the CV portion of run_experiment — same dataset,
    same frozen config, same Development partition, same CV splits, same seeds —
    and compares the resulting CV-mean primary metric to the originally recorded one
  → does NOT touch the Locked Test partition
  → does NOT change source_experiment's ExperimentState, metrics, or artifact
  → does NOT create a second leaderboard entry or a second reportable evaluation
```

This is a read-adjacent diagnostic action, not a re-run of the production lifecycle. `REPRODUCIBILITY_RUN` rows are their own table, never confused with `experiments` rows.

---

## 2. `RANK_AGGREGATION_STABILITY` — Explicit Four-Phase Execution (was implicit)

v9 defined the formula but left the research runner's Day 3→4 ordering implying the stability value could exist before the repeated-run population that produces it. Made explicit:

```
Phase 1 — Generate the population:
  Run repeated selections (5-10 repeats per dataset) using RANK_AGGREGATION
  (BaseScore only) across the pre-registered datasets. This produces the raw
  material stability is computed from.

Phase 2 — Compute stability from Phase 1's output:
  Stability_j = selection frequency for feature j across Phase 1's completed runs.
  This cannot run before Phase 1 finishes — it is a straightforward aggregation
  over already-completed results, not a live/online computation.

Phase 3 — Apply the combined score:
  FinalScore_j = α · BaseScore_j + (1−α) · Stability_j,  α = 0.7 (frozen default).
  BaseScore_j here is recomputed on a fresh run (or reuses a Phase 1 run's
  BaseScore — pick one and state it: reusing is cheaper and equally valid since
  BaseScore doesn't depend on the repeated population).

Phase 4 — Evaluate RANK_AGGREGATION_STABILITY as a method:
  Select Top-K by FinalScore_j, then run the actual predictive-performance
  evaluation (through run_experiment) using that subset, for comparison against
  the other methods in the primary research comparison.
```

`RANK_AGGREGATION_STABILITY` is therefore a legitimate two-stage procedure — measure, then select — not a method that mysteriously knows future selection frequencies in advance.

---

## 3. Dataset Hashing vs. `row_uid` — Explicit Ordering (was ambiguous)

```
1. Raw upload arrives → compute raw_upload_sha256 over the literal uploaded file bytes.
2. Parse into the canonical tabular representation (structural validation, §Data).
3. Compute dataset_content_hash = SHA-256 over the canonical parsed representation
   — BEFORE any row_uid column is added. This is the identity used everywhere
   else in the system (UNIQUE(project_id, dataset_content_hash), lineage, the
   research benchmark manifest).
4. Assign row_uid (UUID) per row. row_uid is lineage/split metadata, added AFTER
   the content identity is fixed — it is never part of dataset_content_hash.
```

Two different files with identical tabular content produce the same `dataset_content_hash` regardless of `row_uid` values, which are freshly generated per upload. `raw_upload_sha256` is retained separately (e.g. for audit — proving exactly which uploaded file produced a given dataset), distinct from the content identity used for deduplication and lineage.

---

## 4. `ModelState.DEPLOYABLE` — Explicit Ownership (was implicit)

The six deployment-gate conditions from v9 §2 split cleanly into two groups with different owners and different timing:

```
MODEL-LEVEL ELIGIBILITY (five conditions, evaluated once per model, owned by the
  gate service's Model Eligibility Check — not by any deployment attempt):
    locked_test_evaluated, schema_locked, artifact_verified, lineage_complete,
    performance_threshold_passed

DEPLOYMENT-SPECIFIC APPROVAL (one condition, evaluated per deployment attempt,
  since approval is tied to a specific deployment action, not inherent to the
  model itself):
    user_approved (approved_by ≠ trained_models.created_by)
```

**Transition ownership, made explicit:**

```
ModelState:
  TRAINED → (artifact checksum verified) → ARTIFACT_VERIFIED
  ARTIFACT_VERIFIED → (Gate Service: Model Eligibility Check evaluates the five
    model-level conditions) → DEPLOYABLE
    - Triggered when a deployment attempt is first initiated for this model
      (not a background job) — the check runs, and if all five pass, ModelState
      flips to DEPLOYABLE as a side effect of that check.
    - If any condition fails, ModelState remains ARTIFACT_VERIFIED, the specific
      failing condition(s) are recorded and surfaced (e.g. in the Experiment
      Health Report), and the deployment attempt is rejected with reasons.
    - The check is idempotent: re-running it with unchanged underlying data
      produces the same result — it may be safely re-invoked (e.g. a manual
      "recheck eligibility" action) without side effects beyond the state write.

DeploymentState (for an attempt against an already-DEPLOYABLE model):
  CREATED → GATE_PENDING
    → (state legality, per §Lifecycle-Legality-vs-Eligibility: model.status=
       DEPLOYABLE AND experiment.status=REGISTERED — this is what Week 6's test
       checks)
    AND (deployment-specific approval, the sixth condition, evaluated fresh per
       attempt — this is what Week 9's gate-service test checks)
    → APPROVED → DEPLOYED
```

This means: the gate service owns writing `ModelState.DEPLOYABLE` (a one-time-per-model transition gated on the five model-level conditions), while the state machine's own legality check (Week 6) only ever *reads* that already-decided value — it never re-evaluates the five conditions itself. The separation from v9 §2 (state legality vs. gate eligibility) still holds; this fix only clarifies *which* eligibility check writes *which* state field, and when.

---

## 5. Admission Control vs. Benchmark Observation (was conflated)

The Week 4 resource guardrail needs to reject an oversized dataset *before* running anything expensive — which means the runtime check can only use information available cheaply, in advance.

```
ADMISSION-CONTROL FEATURES (computed cheaply from structural metadata + config
  alone, used for the actual runtime early-rejection decision):
    rows, raw_column_count, categorical_cardinality_max,
    estimated_encoded_dimensionality, configured_model, configured_selector_set

BENCHMARK OBSERVATIONS (measured by actually running the pipeline during the
  Week 4 benchmarking exercise — used OFFLINE to calibrate the admission-control
  thresholds, never read at runtime to decide whether to reject a given dataset):
    peak_ram_mb, actual_shap_time_s, actual_artifact_size_mb, actual_cv_time_s
```

The runtime guardrail evaluates only admission-control features against thresholds chosen using the benchmark observations — it never has to partially run an expensive stage to decide whether to reject the dataset. This is the same cap-derivation process already described in v9 §10, made precise about which side of the calculation is "the number checked at runtime" versus "the number used to choose the threshold."

---

## 6. Role-Authorization Test — Reframed (terminology fix only)

`test_no_role_name_authorization.py` (v9 §9) is a **role-authorization regression heuristic**, not a security guarantee — a pattern scan can be evaded by superficially different code (`roles = [...]`) or produce a false positive on a legitimate line. The actual authorization guarantee remains `require_permission(key)` plus integration tests against it. Document and refer to the scan as a heuristic regression guard everywhere it's mentioned, never as proof of the permission-based claim.

---

## 7. Everything else

Unchanged from v9: scope, roles/permissions/six invariants, stage map, Data/Data Analysis/Transformation mechanics, feature-selection formula/tie-break/determinism (§5.1 of v8, carried), evaluation protocol, out-of-fold threshold definition, concurrency protection, naming disambiguation, the expanded architecture contract, benchmark manifest fields, DB-commit-failure recovery, Model Passport constraint, Attack Lab manifest, migration invariant, evidence directory standard, and agent operating rules. Nothing about them changed.