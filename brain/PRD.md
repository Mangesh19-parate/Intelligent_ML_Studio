# ML Studio — Product Requirements Document (PRD)

## Problem Statement

No-code ML tools optimize for a fast path from upload to a trained model, and that speed is exactly what produces invalid results: preprocessing and feature selection fit before cross-validation, test sets reused across model-selection decisions, and deployment gated on a single score with no record of who approved what or why. The reported accuracy is frequently an artifact of leakage, not a measure of generalization — and most tools give the user no way to tell the difference.

ML Studio is a tabular ML workbench built around the opposite premise: every data-dependent decision (profiling, feature selection, threshold tuning, model selection) is structurally confined to a Development partition, a Locked Test partition is evaluated exactly once and then consumed, every experiment carries full lineage back to a hashed dataset and a pinned code/library environment, and deployment requires an explicit multi-condition gate with separation of duties — not a score threshold anyone can click past. A separate, clearly-labeled research track evaluates whether rank-aggregated feature selection improves subset stability, as its own falsifiable hypothesis; the platform itself claims engineering rigor, not research novelty.

## Core Features (MVP, P0 — the 12-week/84-day build)

- 8-stage pipeline: Workspace → Data → Data Analysis → Feature Transformation → Feature Engineering → Diagnostics → Machine Learning → Production
- Two-role RBAC (ADMIN/USER) with per-user permission overrides and enforced separation of duties on deployment approval
- A single canonical `run_experiment` execution path (no second training path, ever — this is what makes the research track's parity claim real)
- Six leakage/reproducibility invariants, enforced structurally, not just documented
- Deployment Gate split into Model Eligibility (5 conditions) + Deployment Approval (1 condition, per-attempt)
- Leakage Attack Lab — deliberately broken pipelines compared against the real one, manifest-gated to identical conditions
- Reproduce-Experiment — non-mutating, CV-only diagnostic replay against a frozen tolerance
- Model Passport (read-only lineage card) and Experiment Health Report (structural guarantees vs. per-experiment signals)
- Fixed six-algorithm training engine (three regression, three classification, no algorithm zoo)
- Research track: fixed-model controlled comparison of rank-aggregated feature selection vs. baselines, with a formally-defined stability-aware variant

## Future / Deferred Features (explicitly named, not silently dropped)

| Feature | Status | Reason |
|---|---|---|
| Full 7-method selector ensemble (add RFE, SHAP-based selection) | Deferred | Time cost vs. value for the 12-week core; architecture supports adding later |
| Drift / prediction monitoring (PSI, performance drift) | Deferred (P2) | Real scope, cut to protect the critical path |
| Counterfactual "what changed" experiment diff view | Optional stretch, Week 12 only | Cheap if attempted, not worth displacing critical-path work |
| Scientific Mode / Demo Mode UI toggle | Cut from scope | Cross-cutting cost across every page for marginal value already covered by the Model Passport + Diagnostics stage |
| Multiclass threshold optimization UI | Deferred | Argmax is sufficient; not worth the added leakage-surface complexity |

## Tech Stack & Constraints

**Backend:** Python 3.11+, FastAPI, SQLAlchemy + Alembic, scikit-learn, SHAP, PostgreSQL, JWT + bcrypt/passlib, Pydantic v2, Docker + docker-compose.
**Frontend:** React + Vite + Tailwind.
**Build constraint:** solo developer, ~15–18 hrs/week, 12 weeks (84 days), zero-slack schedule outside Weeks 10–11.
**Algorithm constraint:** fixed six algorithms — Linear Regression, Random Forest Regressor, Gradient Boosting Regressor, Logistic Regression, Random Forest Classifier, Gradient Boosting Classifier. No zoo, ever.
**Dataset-size constraint:** admission-control guardrail (rows/columns/cardinality/estimated encoded dimensionality), threshold calibrated from measured benchmark observations, never a guessed number.

## Success Metrics & Validation

- Every invariant test passes (Locked Test isolation, fold-scoped fitting, out-of-fold thresholding, one-time test consumption, concurrency lock, role-authorization regression heuristic).
- The Attack Lab produces a real, recorded CV-vs-Test gap for at least two attack types, and the real pipeline demonstrably prevents the same path.
- Reproduce-Experiment returns `REPRODUCIBLE_WITHIN_TOLERANCE` against the frozen tolerance on the demo dataset, without mutating the source experiment.
- The deployment gate live-rejects a self-approval attempt and live-accepts a correctly independent one.
- The research track reports an honest either-outcome result (supported or not) from a pre-registered, parity-controlled comparison — never a result shaped after the fact.
- Three independent demo narratives (Trust / Experimentation / Governance) each rehearsed and deliverable standalone.
