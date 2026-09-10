# ML Studio

A leakage-controlled, reproducible, evidence-driven machine learning experimentation platform for tabular data.

Most no-code ML tools optimize for speed from upload to trained model - and that speed is exactly what produces invalid results: preprocessing fit before cross-validation, test sets reused across model-selection decisions, deployment gated on a single score with no record of who approved what. ML Studio is built around the opposite premise: every data-dependent decision is structurally confined to a Development partition, a Locked Test partition is evaluated exactly once, every model carries full lineage back to a hashed dataset and pinned environment, and deployment requires an explicit multi-condition gate with enforced separation of duties.

## Live Deployment

```
Frontend (Vercel):  <add production URL>
Backend API (Render): <add production URL>
```

See `Deployment.md` for required environment configuration before deploying either side - in particular, Render's persistent disk add-on is required, not optional (see that document for why).

## What It Does

- Eight-stage pipeline: **Workspace -> Data -> Data Analysis -> Feature Transformation -> Feature Engineering -> Diagnostics -> Machine Learning -> Production**
- One canonical experiment execution path, used identically by the platform and the research track
- A fixed six-algorithm training engine (no algorithm zoo) with a five-fold cross-validated leaderboard
- A four-technique rank-aggregated feature selector with a proportional, clamped selection rule and an explicit evidence-strength rating
- A six-condition deployment gate, split into model-level eligibility and a separately-approved deployment action with enforced separation of duties
- A non-mutating experiment-replay endpoint for demonstrating reproducibility live
- A Leakage Attack Lab that runs deliberately broken pipelines against manifest-identical conditions and reports the real, measured gap
- A separate research module evaluating rank-aggregated feature selection (plain and stability-aware) against baselines under a fixed-model, parity-controlled protocol

## Tech Stack

**Backend:** Python 3.11+, FastAPI, SQLAlchemy + Alembic, scikit-learn, SHAP, PostgreSQL, JWT + bcrypt, Pydantic v2, Docker.
**Frontend:** React + Vite + Tailwind.
**Hosting:** Vercel (frontend), Render (backend + database).

## Project Structure - Documentation

This project is planned and built entirely from the documents in this repository. Read them in roughly this order:

| Document | What it answers |
|---|---|
| `PRD.md` | What problem this solves and what "done" looks like |
| `Project_Requirements.md` | Functional/non-functional requirements, traced back to the problem statement |
| `SRS_v10_Canonical.md` | The full technical specification - formulas, invariants, frozen contracts |
| `DFD_v11.md` | Data flow, process ownership, state-machine/gate decomposition |
| `Architecture.md` | Condensed structural reference |
| `Design.md` | UI/visual design language and what was deliberately rejected from a reference mockup, and why |
| `Roles.md` | RBAC model, permissions, separation of duties |
| `Rules.md` | Engineering rules and frozen numeric contracts |
| `Deployment.md` | Infra deployment (Vercel/Render) and ML deployment governance (the gate) |
| `Phases.md` | 12-phase plan, critical path, priority tiers |
| `84_Day_Antigravity_Prompts_v3.md` | Day-by-day implementation backlog for the coding agent |
| `Agents.md` | Operating contract for the coding agent (Antigravity) |
| `Memory.md` | Session-priming context - frozen values, settled decisions, retired terms |
| `Decision.md` | The ADR log - every major call made and why |
| `Testing.md` | Test strategy, evidence standard, adversarial testing (the Attack Lab) |

## The 12 Phases

The build runs as 12 phases (one per week, 84 total implementation days). Phases 1, 2, 4, 5, 6, 7, 8, 9 are the critical path; Phases 10-12 are the only elastic ones. Full detail: `Phases.md`.

## Local Development

```bash
docker-compose up
```

Brings up Postgres, the API, and the frontend dev server in one command. See `Agents.md` and `Rules.md` before making any change to a shared invariant, state machine, or frozen contract value - most of what looks like a small tweak in this codebase is a decision that was already made deliberately, once, with a documented reason in `Decision.md`.

## What This Project Deliberately Does Not Do

No chatbot or generative "AI Copilot." No single collapsed "readiness score." No algorithm zoo. No claim of guaranteed leakage-free training - only a structurally enforced one, demonstrated adversarially in the Attack Lab. See `Memory.md`'s retired-terms list before reintroducing anything that sounds like one of these under a different name.
