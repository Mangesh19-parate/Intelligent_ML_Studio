# ML Studio — Data Flow Diagram v11
### Supersedes DFD v10 in full. Formal-DFD corrections only — no business-process or architecture change. This is the version to include in the report.

---

## 0. Changelog from v10

| Fix | Applied |
|---|---|
| Formal Level-1 DFD now includes explicit data stores (D1–D12) | §3 |
| State/Transition Service flows are named (transition request / legality decision), not just described in prose | §2, §3 |
| Production's gate visually split into Model Eligibility Check and Deployment Approval Check, with two distinct outputs | §4 |
| State/Transition Service and Authorization Service kept as cross-cutting services, never renumbered as a 9th process | §2 |
| "Evaluated once per model" reworded — model eligibility can be rechecked, it is not a permanently immutable fact | §4 |
| Two-diagram structure adopted: a business-facing simplified pipeline (Diagram A, for demo/report intro) and a formal Level-1 DFD with stores and flows (Diagram B, for systems-analysis defensibility) | §1 |
| Attack Lab kept as an auxiliary assurance flow, redrawn with explicit branch/merge | §5 |

**Also fixes a wording inconsistency in SRS v10 §4:** that document's phrase "evaluated once per model" should read "evaluated per eligibility check — the check may be re-run (e.g. after an artifact change or a policy update) and is not a permanently immutable fact." This is a one-line wording correction to SRS v10, not a new SRS revision; the underlying behavior (the check is idempotent and re-runnable) was already specified correctly — only the summary phrase in the table row was ambiguous.

---

## 1. Diagram A — Business-Facing Simplified Pipeline (unchanged from v10, kept for demo/report framing)

```
USERS
  │  Dataset (structural validation only)
  ▼
Workspace → Data → Outer Split ──────► Locked Test (set aside, untouched)
                       │  Development
                       ▼
              Data Analysis (Dev only)
                       ▼
              Feature Transformation
                       ▼
              Feature Engineering
                       ▼
                  Diagnostics
                       ▼
              Machine Learning (config freeze → CV → Locked Test, once)
                       ▼
                   Production
                       ▼
             USERS / API CONSUMERS
```

This diagram is for orientation — the demo narratives and the report's introduction use this one. It intentionally omits data stores and cross-cutting services for readability. Diagram B below is the one that should answer a systems-analysis challenge.

---

## 2. Cross-Cutting Services (not numbered processes)

```
                CROSS-CUTTING SERVICES
                         │
          ┌──────────────┴──────────────┐
          │                              │
  State/Transition Service      Authorization Service
  (structural legality only)    (require_permission(key))
```

Neither is a business process — they don't appear as P1–P8. They are read by multiple processes via named flows (below), never folded into any single numbered process, and never renumbered as a "P9."

---

## 3. Diagram B — Formal Level 1 DFD (new — with data stores and named flows)

### Data stores

```
D1  Projects              D7  Feature Selection Results
D2  Datasets               D8  Experiments
D3  Dataset Splits          D9  Models (trained_models)
D4  Profiling Reports       D10 Metrics
D5  Transformation Configs/Snapshots   D11 Deployments
D6  Recommendations         D12 Prediction Logs / Audit Logs
```

### Processes, stores, and named flows

```
P1 Workspace ──creates──► D1 Projects

P2 Data ──validates & splits──► D2 Datasets, D3 Dataset Splits
   P2 ──transition request──► State/Transition Service ──legality decision──► P2

P3 Data Analysis ◄──reads (Development only)── D3 Dataset Splits
   P3 ──writes──► D4 Profiling Reports, D6 Recommendations

P4 Feature Transformation ◄──reads── D3
   P4 ──writes──► D5 Transformation Configs/Snapshots

P5 Feature Engineering ◄──reads── D5
   P5 ──writes──► D7 Feature Selection Results

P6 Diagnostics ◄──reads── D9 Models, D10 Metrics, D7
   P6 ──writes──► D6 Recommendations (diagnostic findings)
   (P6 never reads or writes state-machine fields — see §2)

P7 Machine Learning ◄──reads── D3, D5, D7, frozen config from D8
   P7 ──transition request──► State/Transition Service ──legality decision──► P7
   P7 ──writes──► D8 Experiments, D9 Models, D10 Metrics
   P7 ──failure event──► D12 Audit Logs   (TRAINING_FAILED, ARTIFACT_WRITE_FAILED)

P8 Production ◄──reads── D9 Models, D8 Experiments
   P8 ──transition request──► State/Transition Service ──legality decision──► P8
   P8 splits internally into two named sub-flows — see §4
   P8 ──writes──► D11 Deployments, D12 Prediction Logs
```

Every process that needs a state-machine answer sends a **transition request** and receives a **legality decision** — that's the named flow pair to use throughout, replacing the vaguer "reads ProjectState" phrasing from v10.

---

## 4. Production — Gate Split, Explicit Two-Output Diagram (new — closes the muddled decomposition from v10)

```
                    P8 — PRODUCTION
                          │
                          ▼
              ┌─────────────────────────┐
              │  8a MODEL ELIGIBILITY   │
              │        CHECK            │
              │ (five conditions:       │
              │  locked_test_evaluated, │
              │  schema_locked,         │
              │  artifact_verified,     │
              │  lineage_complete,      │
              │  performance_threshold_ │
              │  passed)                │
              └────────────┬────────────┘
                    ┌───────┴───────┐
                    ▼               ▼
          ModelState =        Failure reasons
          DEPLOYABLE          (recorded, surfaced
                │              in Health Report;
                │              ModelState stays
                │              ARTIFACT_VERIFIED)
                ▼
              ┌─────────────────────────┐
              │  8b DEPLOYMENT          │
              │     APPROVAL CHECK      │
              │ (sixth condition:       │
              │  user_approved,         │
              │  approved_by ≠          │
              │  created_by)            │
              └────────────┬────────────┘
                    ┌───────┴───────┐
                    ▼               ▼
          DeploymentState=     DeploymentState
          APPROVED             stays GATE_PENDING
                │              (rejection reason
                ▼              shown in UI)
              DEPLOYED
```

**Important, corrects v10's "once per model" phrasing:** 8a is not a one-time permanent fact about a model. It is **evaluated per eligibility check** — re-runnable (e.g. after an artifact is replaced, or a deployment_threshold policy changes), idempotent given unchanged inputs, and `ModelState.DEPLOYABLE` reflects the *most recent* check's result, not a fact fixed forever at first success. 8b is always evaluated fresh, per deployment attempt — it never reuses a prior attempt's approval decision. `DEPLOYABLE` is never itself equivalent to deployment approval — this diagram exists specifically so that question can't be misread from the prose alone.

---

## 5. Attack Lab — Auxiliary Assurance Flow (unchanged in substance from v10, redrawn)

```
                 ASSURANCE / RESEARCH (not part of normal system operation)
                              │
                    Attack Lab Manifest
                    (dataset, version, hash,
                     target, split, metric,
                     seed — frozen)
                              │
                 ┌────────────┴────────────┐
                 ▼                         ▼
          Leaky Pipeline Variant     Correct Pipeline
          (leakage mechanism         (Processes 4–7,
           injected)                  unmodified)
                 │                         │
                 └────────────┬────────────┘
                              ▼
                        Comparison
                  (CV metric, Test metric, gap)
                              ▼
                     Evidence Artifact
```

Not numbered as a process — the system does not run the leaky variant during normal operation. It's an evaluation instrument that exercises the real pipeline (P4–P7) alongside a deliberately broken one, gated by the same manifest so only the leakage mechanism differs between the two runs being compared.

---

## 6. Ownership Table (new — freezes responsibility boundaries against future drift)

| Component | Decides | Writes |
|---|---|---|
| State/Transition Service | Structural legality | State fields (ProjectState, ExperimentState, ModelState, DeploymentState) |
| Deployment Gate Service (8a + 8b) | Business eligibility (model-level + deployment-specific) | `ModelState.DEPLOYABLE` (8a only), gate condition records |
| Diagnostics (P6) | Model/data evidence | Diagnostic findings, recommendations |
| Authorization Service | Permission | No lifecycle state |
| Experiment Runner (P7's `run_experiment`) | Training/evaluation execution | Experiment/model/metric artifacts |

No component listed here writes another's column. If a future change would make one of these write outside its listed column, that's the signal to stop and reconsider before implementing it, not after.

---

## 7. Everything else — carried forward from v10 unchanged

Level 0 context diagram, the permission-gated page table, the navigation architecture, and the three-demo final recommendation are all unchanged. Not restated here since nothing about them changed.

---

## 8. Freeze note

Per the review that produced this revision: this is the last DFD iteration expected to add value. Further diagram changes should come from an actual discrepancy discovered during implementation, not from another documentation pass.