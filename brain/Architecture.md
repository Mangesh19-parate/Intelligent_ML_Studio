# ML Studio — Architecture

Full spec: `SRS_v10_Canonical.md`. This document is the condensed structural reference.

## Layered Backend

```
FastAPI (Python)
│
├── API Layer            /api/v1/*
├── Service Layer         (OOP, one class per concern)
├── Repository Layer      SQLAlchemy ORM
├── Object Storage        StorageService interface, local FS
└── PostgreSQL
```

## Cross-Cutting Services (not numbered pipeline stages)

```
State/Transition Service   — structural legality only ("is this transition legal?")
Authorization Service      — require_permission(key), never role-name checks
```

## The 8-Stage Pipeline

Workspace → Data → Data Analysis → Feature Transformation → Feature Engineering → Diagnostics → Machine Learning → Production.

**Stage-execution invariant:** stage adjacency in the UI is organizational, not an execution order. Transformation and feature selection execute only inside the fold-level CV loop inside Machine Learning — never globally before it.

## The Canonical Experiment Runner

```
run_experiment(experiment_id):
  load frozen config → load Development data (by row_uid) → create CV splits
  → construct Pipeline (transform + selection + estimator) → fit each fold
  → collect metrics + feature-selection evidence → select winner
  → refit winner on full Development → persist artifacts + lineage
```

This is the **only** training path — used by the platform (Machine Learning stage) and the research runner (Week 11) alike. A second training path anywhere is a regression against the whole architecture.

## Four Independent State Machines

```
ProjectState:     CREATED → DATA_UPLOADED → SPLIT_LOCKED → PROFILED → TRANSFORMATION_CONFIGURED
ExperimentState:  CREATED → CONFIGURED → TRAINING → EVALUATED → TEST_CONSUMED → REGISTERED
                    (+ TRAINING_FAILED, ARTIFACT_WRITE_FAILED retry side-states)
ModelState:       TRAINED → ARTIFACT_VERIFIED → DEPLOYABLE (+ ARTIFACT_INVALID)
DeploymentState:  CREATED → GATE_PENDING → GATE_PASSED|GATE_BLOCKED → APPROVED → DEPLOYED → PAUSED → RETIRED
```

No single `status` column represents all of this — a project can have many experiments simultaneously at different states.

## Deployment Gate — Two-Part Decomposition

```
8a Model Eligibility Check (5 conditions, owns ModelState.DEPLOYABLE, re-checkable —
   not a permanent fact): locked_test_evaluated, schema_locked, artifact_verified,
   lineage_complete, performance_threshold_passed

8b Deployment Approval Check (1 condition, evaluated fresh per deployment attempt):
   user_approved, approved_by ≠ trained_models.created_by
```

## Data Stores

```
D1 Projects | D2 Datasets | D3 Dataset Splits | D4 Profiling Reports
D5 Transformation Configs/Snapshots | D6 Recommendations
D7 Feature Selection Results | D8 Experiments | D9 Models
D10 Metrics | D11 Deployments | D12 Prediction Logs / Audit Logs
```

## Lineage & Reproducibility Chain

```
dataset_content_hash (pre-row_uid) + split_seed + cv_seed + code_version +
python/sklearn/numpy/pandas versions + artifact_checksum
```

captured on every `trained_models` row. `Reproduce-Experiment` is a **non-mutating, CV-only, Development-only replay** — never touches the Locked Test, never mutates the source experiment, produces a separate `reproducibility_run` record.

## The Six Invariants

1. No learned preprocessing outside training folds.
2. The Locked Test set is never touched for any data-dependent decision, and is permanently consumed after one use.
3. Every experiment is reproducible under its captured environment.
4. Every model has full lineage: Model → Experiment → Dataset version → Feature snapshot → Preprocessing snapshot → Evaluation protocol.
5. Deployment requires an explicit, multi-condition gate — never a single score threshold.
6. Test-set isolation covers data-dependent decisions, not just model fitting.

## Ownership Table (prevents responsibility drift)

| Component | Decides | Writes |
|---|---|---|
| State/Transition Service | Structural legality | State fields |
| Deployment Gate Service (8a+8b) | Business eligibility | `ModelState.DEPLOYABLE`, gate records |
| Diagnostics | Model/data evidence | Diagnostic findings |
| Authorization Service | Permission | No lifecycle state |
| Experiment Runner | Training/evaluation execution | Experiment/model/metric artifacts |
