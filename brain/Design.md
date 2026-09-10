# ML Studio — Design

UI/visual design language. Backend behavior is unaffected by anything in this document — this governs presentation only.

## Origin and Constraint

A visual reference was reviewed (a polished dark-theme SaaS mockup) and evaluated against the project's architecture. The verdict: adopt the **visual/layout language**, reject the **substantive framing** that conflicted with decisions already made and defended across multiple review rounds. See `Decision.md` ADR-012 for the full reasoning.

## Adopt

- **Theme:** dark background, purple/violet accent, card-grid layout.
- **Header:** breadcrumb (project name) + a pipeline-stage stepper showing progress across the 8 stages.
- **Sidebar:** grouped by stage, with section headers and icons — maps directly onto the 8-stage architecture.
- **Evidence-card pattern:** a card format (title / evidence line / confidence badge / action button) for surfacing findings — visually similar to the reference's insight panel, but rendering the actual `recommendations` table (finding/evidence/action/risk/confidence), not free-text generation.
- **Sparkline / progress-bar visualizations**, drop-zone upload UI, timeline feeds for experiment history.

## Reject / Adapt

| Reference pattern | Why rejected | What ML Studio does instead |
|---|---|---|
| "AI Copilot" persistent chat panel | No chatbot, no generative/LLM commentary (decided and defended repeatedly) | Same panel position, same card visual style, rendering stored `recommendations` — no chat input, no free-text generation |
| Single "91% Dataset Health" gauge | Retired-terms list has banned "Readiness Score"/"Dataset Health Score" since the first SRS draft | DQI's four sub-scores (Missingness, Duplicate Rate, Outlier Prevalence, Type Consistency) shown as a card cluster with effective weights, never collapsed to one number |
| "INTELLIGENCE" nav section label | Retired for the same reason as "Intelligent" — avoids AI-hype framing | "Diagnostics" |
| Algorithm-zoo toggle switches (6+ trendy algorithms) | Contradicts the fixed-six, no-zoo decision defended in every review round | Same toggle-switch visual pattern, constrained to exactly the six canonical algorithms |
| Diagnostics running immediately on raw upload | Actual leakage bug — violates Invariant 6 | Same "automatic" framing in copy, but diagnostics only run after the outer split, Development-only |
| Numeric confidence percentages (94%, 98%) presented as an oracle | False precision; the project's own recommendation schema uses HIGH/MEDIUM/LOW bands | Confidence shown as HIGH/MEDIUM/LOW badges, never a bare percentage |
| Full drift-monitoring (PSI charts) as core Monitoring | Explicitly deferred to P2 to protect the critical path | Monitoring stage ships volume/latency only in the MVP; PSI charts are named future work, not silently absent |

## Key Component Layouts

**Model Passport:** a compact identity card — model/dataset/hash/task/target, CV + Locked Test metric, feature-selection method + evidence strength, environment versions, git commit, artifact checksum, gate status. Read-only, no interactive elements beyond a copy/export action.

**Experiment Health Report:** two visually distinct sections — a static "structural guarantees" block (statements, not checkboxes, since these hold by construction) and a "per-experiment signals" block (fit diagnosis, evidence strength, checksum, Locked Test status, the five model-eligibility conditions individually, deployment approval status), summarized as "N risks flagged," never a score.

**Deployment Gate checklist:** shows all six conditions individually, visually grouped into the 5 model-eligibility conditions (§8a) and the 1 approval condition (§8b), with a specific failure reason surfaced inline when blocked — never a silent block.

**Attack Lab card:** Attack / Expected effect / Observed (CV metric, Test metric, gap) / Control (which invariant blocks it) / Result — the same structured format for every attack, real numbers only.

## Explicitly Out of Scope

Scientific Mode / Demo Mode toggle — cut from committed scope (cross-cutting cost across every page for marginal value already covered by the Model Passport + Diagnostics stage). Counterfactual "what changed" diff view — optional Week 12 stretch only, no committed design.
