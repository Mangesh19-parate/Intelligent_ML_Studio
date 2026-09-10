# ML Studio — Rules

Engineering rules the system must satisfy, distinct from `Agents.md` (which governs coding-agent behavior, not system behavior). Full derivation: `SRS_v10_Canonical.md`.

## The Six Invariants (never violated, structurally enforced)

1. No learned preprocessing outside training folds.
2. The Locked Test set is never touched for any data-dependent decision, and is permanently consumed after one use.
3. Every experiment is reproducible under its captured environment.
4. Every model has full lineage: Model → Experiment → Dataset version → Feature snapshot → Preprocessing snapshot → Evaluation protocol.
5. Deployment requires an explicit, multi-condition gate — never a single score threshold.
6. Test-set isolation covers data-dependent decisions, not just model fitting.

## Naming

No abbreviation ambiguity. Selectors: `CORRELATION_SELECTOR`, `LASSO_SELECTOR`, `RANDOM_FOREST_IMPORTANCE_SELECTOR`, `PERMUTATION_IMPORTANCE_SELECTOR`. Algorithms: `LINEAR_REGRESSION`, `RANDOM_FOREST_REGRESSOR`, `GRADIENT_BOOSTING_REGRESSOR`, `LOGISTIC_REGRESSION`, `RANDOM_FOREST_CLASSIFIER`, `GRADIENT_BOOSTING_CLASSIFIER`. State enums always fully qualified (`ExperimentState.CONFIGURED`, never bare `CONFIGURED`).

## Frozen Numeric Contracts

```
metric_absolute_tolerance = 1e-3
metric_relative_tolerance = 0.01
within_tolerance(expected, observed) := abs(observed-expected) <= max(abs_tol, rel_tol*abs(expected))

Feature selection: TOP_K_PERCENT, alpha=0.25, k_min=5, k_max=50, min_applied_methods=2
Stability formula (research-only): FinalScore_j = 0.7*BaseScore_j + 0.3*Stability_j
Dataset-size guardrail cap: derived from the STRESS benchmark dataset's worst case, never the mean
```

## Admission Control vs. Benchmark Observation

Runtime rejection reads only pre-execution, cheap-to-compute admission-control features (rows, raw_column_count, categorical_cardinality_max, estimated_encoded_dimensionality, configured_model, configured_selector_set). It never reads benchmark observations (peak_ram_mb, actual_shap_time_s, actual_artifact_size_mb, actual_cv_time_s) at runtime — those exist only to calibrate the admission-control thresholds offline.

## Concurrency

An experiment may have at most one active training job at a time, enforced via a DB-level unique constraint or advisory lock — not merely discouraged by the UI.

## Out-of-Fold Threshold Rule

Threshold optimization uses out-of-fold Development predictions only. A prediction used for threshold search must come from a fold that did not train on that row.

## Feature-Selection Determinism

Tie-break at the K boundary: (1) higher EnsembleScore, (2) lower aggregate raw rank sum, (3) lexicographic feature name ascending. Identical inputs/config/seed must produce byte-identical output across independent runs.

## Platform Scope Boundary

`RANK_AGGREGATION` is the only feature-selection method available through the platform API. `RANK_AGGREGATION_STABILITY` is research-only, rejected with an explicit 400 if requested through the platform.

## Dataset Hashing Order

`dataset_content_hash` = SHA-256 over the canonical parsed representation, computed before `row_uid` assignment. `row_uid` is lineage metadata, never part of content identity. `raw_upload_sha256` (over the literal uploaded bytes) is retained separately for audit.

## Transaction & Recovery Rules

```
Artifact save: write artifact -> verify checksum -> commit DB row (never the reverse)
DB-commit-failure (after artifact write succeeds): attempt cleanup -> log outcome ->
  mark ORPHANED_RECOVERABLE if cleanup itself fails
```

## Migration & Evidence Standards

Every schema change ships an Alembic migration; weekly regression includes `alembic upgrade head` against a fresh, empty database. Every phase's evidence lands in `week-NN/{evidence.md, test-report.txt, artifacts/, screenshots/, logs/}`.

## Retired Terms — Never Reintroduced

"AutoML," "Intelligent"/"Intelligence" as a module name, "Production Ready," "Dataset Health Score," "Readiness Score," "guaranteed leakage-free," `PROJECT_OWNER`/`COLLABORATOR`, `dataset_versions` as a table name.

## Role-Authorization Test — Framing

`test_no_role_name_authorization.py` is a regression heuristic, not a security guarantee. The real guarantee is `require_permission(key)` plus integration tests against it.
