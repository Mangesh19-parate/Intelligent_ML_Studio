# ML Studio — Agents.md (Antigravity Operating Contract)

This file governs how an autonomous coding agent (Antigravity) operates on this codebase. It applies to every task, not just the 84-Day Backlog — if a task isn't in the backlog, these rules still apply.

## Mode Selection

- **Plan mode:** any task touching more than one file, a shared invariant (leakage, gate, lineage, state machine), or a frozen contract value. Request a Plan Artifact before executing.
- **Fast mode:** small, contained work only — a single-file fix, a test run, a regression check.

If unsure which mode a task needs, default to Plan mode. The cost of an unnecessary plan is small; the cost of an under-planned multi-file change touching a state machine is not.

## Agent Change Boundary

The agent may not modify unrelated modules, schemas, APIs, state transitions, or frozen contract values (`backend/app/config/contract.py`, `state_machines.py`) unless:

1. required by the current task,
2. required to fix a failing test, or
3. explicitly named in that day's Plan Artifact.

"While implementing X I noticed Y could be improved" is never authorization to change Y. If the agent proposes this, decline it and ask it to open a separate, explicitly-scoped task instead.

## Agent Failure Protocol

A day or task is **incomplete**, not "mostly done," when any of the following happen:

- The required evidence artifact (test-run, screenshot, walkthrough) is missing.
- A test fails.
- A screenshot or walkthrough doesn't match the stated requirement.

None of these are resolved by moving on to the next task anyway. The agent continues the current task until the evidence actually exists and passes.

## Evidence Requirement

Never accept the agent's own "done" claim as sufficient. Every completed day produces a real artifact under `week-NN/{evidence.md, test-report.txt, artifacts/, screenshots/, logs/}` — open it and check it yourself before pulling the next task from the backlog.

## Naming Discipline

The agent must use full canonical names everywhere — code, tests, UI strings, logs, commit messages:

- Selectors: `CORRELATION_SELECTOR`, `LASSO_SELECTOR`, `RANDOM_FOREST_IMPORTANCE_SELECTOR`, `PERMUTATION_IMPORTANCE_SELECTOR`
- Algorithms: `LINEAR_REGRESSION`, `RANDOM_FOREST_REGRESSOR`, `GRADIENT_BOOSTING_REGRESSOR`, `LOGISTIC_REGRESSION`, `RANDOM_FOREST_CLASSIFIER`, `GRADIENT_BOOSTING_CLASSIFIER`
- State enums: fully qualified (`ExperimentState.CONFIGURED`, never bare `CONFIGURED`)

Never let the agent abbreviate "Random Forest" as bare "RF" — it's ambiguous between a selector and two different algorithms.

## Backlog Usage

The 84-Day Backlog (`ML_Studio_84_Day_Antigravity_Prompts_v3.md`) is an **ordered backlog, not a locked calendar**. Pull the next day's prompt only when the prior day's evidence artifact exists and passes. If a day is incomplete per the Failure Protocol, the agent stays on it — do not advance the calendar to "stay on schedule."

## What the Agent Should Never Do Without Being Asked

- Introduce a new dependency not already in the tech stack (see PRD.md) without flagging it first.
- Add a UI element, page, or feature not named in the current task or in Phases.md's current-week scope.
- Reintroduce anything on the retired-terms list (see Rules.md) under a different name.
- Treat a Plan mode task as Fast mode to save time.
- Silently expand `RANK_AGGREGATION_STABILITY` availability beyond the research-only module (see Rules.md) — this is a specific, previously-resolved circular-dependency fix, not an oversight to "helpfully" correct.

## Where to Look Things Up

- Fine-grained spec, invariants, formulas: `SRS_v10_Canonical.md`
- Data flow, process ownership: `DFD_v11.md`
- Day-by-day implementation tasks: `84_Day_Antigravity_Prompts_v3.md`
- Why a decision was made (don't re-litigate it — check here first): `Decision.md`
- Session-priming context: `Memory.md`
