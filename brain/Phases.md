# ML Studio — Phases

12 phases, one per week. Full day-by-day detail: `84_Day_Antigravity_Prompts_v3.md`. This document is the phase-level summary for planning and status tracking.

## Critical Path

Phases 1, 2, 4, 5, 6, 7, 8, 9 are critical path — a slip here delays everything downstream. Phases 10, 11, 12 are the only elastic ones, in that order of expendability.

## Weekly Rule: Red / Yellow / Green

```
GREEN  — all Definition-of-Done items pass + evidence artifact captured → continue
YELLOW — core works, one or more DoD items failed → next phase starts by fixing them
RED    — a P0 invariant is broken → STOP, freeze new feature work until fixed and retested
```

## Phase Summary

| # | Phase | Goal | Checkpoint |
|---|---|---|---|
| 0 | Spec Freeze | Contract, state machines, algorithm/selector naming, tolerances all frozen before any feature code | Architecture Contract exists |
| 1 | Foundation | Auth, permissions, bootstrap, Docker, 8-stage nav shell, demo accounts | — |
| 2 | Data Stage | Upload, structural validation, row_uid, outer split, content hash | Vertical Slice #1 |
| 3 | Data Analysis | DQI, profiling, task-type detection, recommendations | — |
| 4 | Feature Transformation | Transformation service, preview contract, benchmark (timing + memory), admission-control guardrail | **Checkpoint 1** |
| 5 | Feature Engineering | Four selectors, rank aggregation, tie-break, determinism, evidence strength, platform excludes stability method | — |
| 6 | Canonical Runner | State wiring, concurrency lock, `run_experiment`, six algorithms, full CV run | — |
| 7 | Evaluation | Metrics, leaderboard, out-of-fold threshold, Locked Test consumption | — |
| 8 | Lineage & Diagnostics | Lineage, checksum, DB-failure recovery, non-mutating Reproduce-Experiment, SHAP, Diagnostics stage, Model Passport | **Checkpoint 2 — MVP complete** |
| 9 | Production | Deployment gate (8a/8b split), predict/explain, monitoring, admin pages, Experiment Health Report | Live gate demo (self-approval rejected, then approved) |
| 10 | Assurance | Invariant test consolidation, Attack Lab (manifest-gated), research runner dry-run | — |
| 11 | Research | Pre-registration, phased stability execution, primary comparison, statistics | Pre-registered before first run |
| 12 | Integration & Demo | Full regression, spec reconciliation, three demo recordings, viva rehearsal | Final submission |

## Priority Tiers (apply within every phase)

**P0** — leakage-safe lifecycle, RBAC + separation of duties, all 8 stages functional end-to-end, deployment gate, core invariant tests. Never traded away.
**P1** — research track, Attack Lab, Model Passport, Experiment Health Report, Reproduce-Experiment's comparison surface. Cut second.
**P2** — drift monitoring, full selector ensemble, UI polish beyond functional, Counterfactual view. Cut first.
