# ML Studio - Project Requirements

This document exists to answer one question directly: does the solution cover every aspect the problem statement actually asks for, and nothing invented on top of it that isn't traceable back to it? Full narrative version of the problem: `PRD.md`.

## Problem Statement (restated exactly)

No-code ML tools optimize for a fast path from upload to a trained model, and that speed is exactly what produces invalid results: preprocessing and feature selection fit before cross-validation, test sets reused across model-selection decisions, and deployment gated on a single score with no record of who approved what or why. ML Studio must instead confine every data-dependent decision to a Development partition, evaluate a Locked Test partition exactly once and then consume it, carry full lineage from a hashed dataset through a pinned environment to a deployed model, and require an explicit multi-condition deployment gate with separation of duties - never a score threshold anyone can click past. A separate, clearly-labeled research track evaluates whether rank-aggregated feature selection improves subset stability, as its own falsifiable hypothesis, distinct from the platform's own engineering claim.

## Functional Requirements

| ID | Requirement | Satisfied by |
|---|---|---|
| FR-1 | Users upload tabular datasets (CSV/XLSX/JSON); the system performs structural validation only (dtype, missing%, unique count) - no distributional or target-aware logic before the split | Data stage, `Architecture.md` |
| FR-2 | The system automatically locks a Development/Locked Test split immediately after structural validation, before any profiling | Data stage, Invariant 2 |
| FR-3 | The system computes a Data Quality Index (four sub-scores + effective weights) and correlation/distribution profiling, Development-only | Data Analysis stage |
| FR-4 | The system suggests a task type (regression/classification) with a stated confidence band, and requires explicit user choice when ambiguous | Data Analysis stage |
| FR-5 | Users configure imputation/encoding/scaling; the system previews a deterministic Development-only sample without letting the preview influence fitting | Feature Transformation stage |
| FR-6 | The system runs four feature-selection techniques, aggregates them by rank, and reports both a selected subset and an evidence-strength band, never a bare pass/fail | Feature Engineering stage |
| FR-7 | The system trains six fixed algorithms (three regression, three classification) via one canonical execution path, with 5-fold cross-validation | Machine Learning stage, `run_experiment` |
| FR-8 | The system ranks models by a primary metric, shows a secondary composite score labeled as non-authoritative, and flags fit diagnosis (overfit/underfit/insufficient data) | Machine Learning stage |
| FR-9 | The system evaluates the Locked Test exactly once per experiment generation and permanently marks it consumed | Invariant 2, ExperimentState |
| FR-10 | The system requires an explicit six-condition deployment gate, split into model-level eligibility and a separately-evaluated, independently-approved deployment action | Production stage, Deployment Gate |
| FR-11 | The deployment gate rejects a deployment where the approver is the same account that trained the model, with no exception for administrators | Roles.md, ADR-001/ADR-011 |
| FR-12 | The system exposes decoupled prediction and explanation endpoints, with configurable, privacy-labeled prediction logging | Production stage |
| FR-13 | The system can non-destructively replay an experiment's cross-validation to verify reproducibility, without touching the Locked Test or mutating the original experiment | Reproduce-Experiment, ADR-008 |
| FR-14 | The system provides a read-only lineage summary per model and a per-experiment risk/evidence report distinguishing structural guarantees from variable signals | Model Passport, Experiment Health Report |
| FR-15 | The system supports two identity roles with permission-based (not role-name-based) authorization, with per-user permission overrides | Roles.md |
| FR-16 | A separate research module evaluates rank-aggregated feature selection (with and without a stability-aware variant) against baselines under a fixed-model, parity-controlled protocol | Research track, ADR-005/ADR-014 |
| FR-17 | The system demonstrates, via deliberately reproduced broken pipelines under identical conditions, that its real pipeline prevents the leakage patterns it claims to prevent | Leakage Attack Lab |

## Non-Functional Requirements

| ID | Requirement | Satisfied by |
|---|---|---|
| NFR-1 | No learned preprocessing or feature selection may execute outside a training fold, under any configuration | Invariant 1, stage-execution invariant |
| NFR-2 | Every trained model must carry lineage sufficient to reproduce it under its captured environment (dataset hash, seeds, code/library versions, artifact checksum) | Invariant 3-4 |
| NFR-3 | Reproducibility is evaluated against a frozen numeric tolerance, not an ad hoc per-run judgment | `metric_absolute_tolerance=1e-3`, `metric_relative_tolerance=0.01` |
| NFR-4 | Authorization must be permission-based in code, with a regression test guarding against role-name checks creeping back in | `require_permission(key)`, `test_no_role_name_authorization.py` |
| NFR-5 | The system must reject oversized datasets before running expensive computation, using only cheaply-computed pre-execution signals | Admission-control vs. benchmark-observation split, ADR-010 |
| NFR-6 | An experiment may have at most one active training job at a time | Concurrency protection |
| NFR-7 | Every schema change must be verifiable against a freshly created, empty database, not only a long-lived development database | Migration invariant |
| NFR-8 | Artifact storage must survive a deploy/restart cycle in the hosted environment | Render persistent disk, `Deployment.md` |
| NFR-9 | The solution must be buildable by a single developer within a fixed 12-phase/84-day schedule without silently dropping any P0 requirement | `Phases.md`, priority tiers |
| NFR-10 | The platform's engineering claims and the research track's empirical claims must remain clearly separated in both code and reporting | ADR-014, scope statement in `PRD.md` |

## Assumptions

- The person operating the system understands basic ML terminology (target column, cross-validation, feature) - the platform is a workbench for practitioners, not a lay-user AutoML product.
- Dataset sizes stay within the admission-control caps calibrated during Phase 4's benchmark; datasets exceeding them are explicitly rejected, not silently degraded.
- A single production deployment target (Vercel + Render) is sufficient for the project's demonstration purposes; multi-region or high-availability hosting is out of scope.

## Explicitly Out of Scope (see `PRD.md` for the full deferred-features table)

Full 7-method selector ensemble, drift/prediction monitoring, the Counterfactual diff view (except as an optional Phase-12 stretch), a Scientific/Demo Mode UI toggle, multiclass threshold optimization UI.
