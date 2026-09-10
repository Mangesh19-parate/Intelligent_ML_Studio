# ML Studio - Decision Log (ADRs)

Every major architectural call made across this project's design process, with rationale, so nobody re-litigates a settled question without knowing why it was settled. Status of every entry below: **Accepted**.

---

**ADR-001: Collapse five roles to two (ADMIN, USER), with per-user permission overrides for separation of duties.**
Five named roles (ADMIN/ML_ENGINEER/DATA_STEWARD/DEPLOYMENT_MANAGER/VIEWER) added identity-taxonomy complexity without adding real access control beyond what permission bundles already express. Reducing to two roles plus per-user overrides keeps `require_permission(key)` as the sole authorization primitive, and still supports the deployment-approval separation-of-duties requirement without inventing a third role just for that one case.

**ADR-002: Retire "Intelligent"/"Intelligence" as a module or stage name; use "Diagnostics."**
Flagged independently across multiple review rounds. The word signals generic-AI-hype framing the project explicitly rejects (no chatbot, no "AI-powered" badge, rule-based evidence-backed recommendations only). "Diagnostics" describes the actual content (fit diagnosis, recommendations, decision trace) without the framing baggage.

**ADR-003: Fixed six algorithms, no algorithm zoo.**
Six controlled algorithms with strong evaluation methodology is more defensible in a technical review than a large algorithm menu. An early draft listed seven algorithms while claiming "six" - resolved to exactly Linear Regression, Random Forest Regressor, Gradient Boosting Regressor (regression) and Logistic Regression, Random Forest Classifier, Gradient Boosting Classifier (classification).

**ADR-004: `TOP_K_PERCENT` proportional selection, not a fixed `k=20`.**
A fixed K=20 means "keep everything" on a 20-feature dataset and "keep 4%" on a 500-feature one - wildly different selection pressure for the same configured number. `K = clamp(ceil(p * alpha), k_min, k_max)` normalizes across dataset sizes.

**ADR-005: `RANK_AGGREGATION_STABILITY` is research-only, blocked at the platform API.**
The stability formula needs a repeated-run population (`Stability_j` = selection frequency across repeated runs) that doesn't exist during a single ordinary platform experiment. Offering it as a platform option was underdefined by construction. Resolved by restricting it to the research runner, where the repeated-run protocol actually supplies the input it needs, executed as an explicit four-phase procedure (generate population -> compute stability -> combine score -> evaluate).

**ADR-006: Separate state-machine legality from deployment-gate eligibility.**
"Can this transition legally happen" (structural) and "should it happen" (business eligibility - six substantive conditions) were originally conflated in a single check. Splitting them means the state machine never encodes gate business rules, and the gate service never re-implements state legality - each is tested independently.

**ADR-007: `dataset_content_hash` computed before `row_uid` assignment.**
Two files with identical tabular content should produce the same content hash regardless of the per-upload UUIDs assigned to rows. Sequencing the hash before row_uid injection, and keeping `raw_upload_sha256` as a separate audit-only hash of the literal uploaded bytes, removes the ambiguity.

**ADR-008: Reproduce-Experiment is a non-mutating, CV-only diagnostic replay.**
Naively re-running the full canonical `run_experiment` for reproduction risked re-consuming the Locked Test or creating a second reportable evaluation - which would violate the test-consumption invariant in the name of proving reproducibility. Resolved: a restricted replay mode, Development/CV-only, producing a separate `reproducibility_run` record, never touching the source experiment's state or the Locked Test.

**ADR-009: `ModelState.DEPLOYABLE` is owned exclusively by the Gate Service's Model Eligibility Check, and is re-checkable.**
Ambiguity existed about who writes this transition and whether it was a permanent fact. Resolved: the five model-level gate conditions (excluding approval) are owned by one specific service, triggered on first deployment attempt, idempotent, and re-evaluated rather than fixed forever at first success (e.g. after an artifact replacement or a policy change).

**ADR-010: Admission-control features (pre-execution) formally separated from benchmark observations (post-execution).**
The runtime size guardrail must reject an oversized dataset before running anything expensive, which means it can only ever read cheap, predictable, pre-execution features (row/column counts, cardinality, estimated encoded dimensionality) - never a measured quantity like peak RAM, which requires having already run the expensive stage to know.

**ADR-011: Two-role model requires per-user `DEPLOY` overrides to preserve separation of duties in demos.**
Using an ADMIN account to demonstrate deployment approval would trivially satisfy the mechanism without exercising it meaningfully, since ADMIN gets DEPLOY by default. Two USER accounts, one with an explicit override, is the version that actually demonstrates the override mechanism.

**ADR-012: Rejected the "AI Copilot" chat panel, single readiness-score gauge, and algorithm-zoo UI pattern seen in a visual reference.**
A polished visual reference was reviewed for UI direction. Its layout/visual language (dark theme, card grid, sidebar-by-stage) was adopted; its substantive framing (persistent chat-style insights panel, single "91% Dataset Health" score, six-plus toggleable algorithms including deep-learning options, diagnostics claimed to run on raw upload) directly contradicted decisions in ADR-002, ADR-003, and the DQI's four-sub-score design, plus surfaced an actual leakage-boundary bug in the reference's own upload-page copy. Visual style adopted; substance rejected. See `Design.md`.

**ADR-013: Leakage Attack Lab's Definition of Done relaxed from "material inflation" to "attack confirmed and comparison recorded."**
Requiring a dramatic performance gap as the pass condition incentivizes cherry-picking datasets/attacks that produce impressive numbers. The actual claim being tested is that the attack path is real and the control blocks it - the magnitude of the resulting gap is reported honestly, not manufactured.

**ADR-014: Fixed-model controlled comparison is the primary research hypothesis test; full end-to-end model-selection comparison is secondary/illustrative only.**
If different feature-selection methods end up paired with different winning algorithms during evaluation, a measured performance difference conflates the feature-selection effect with a model-selection effect. Fixing the model across the comparison isolates the variable the hypothesis is actually about.

**ADR-015: Scientific Mode / Demo Mode UI toggle cut from scope; Counterfactual "what changed" view kept as an optional Week-12-only stretch.**
The two-mode toggle is a cross-cutting UI cost (two render states per page, across every page in all 8 stages) for value the Model Passport and Diagnostics stage already mostly deliver. The counterfactual diff view is cheap if attempted (a JSON diff of two stored configs) but not worth displacing critical-path work, and the source review that proposed it called it a stretch feature itself.

**ADR-016: Frontend on Vercel, backend + API on Render, with Render's persistent disk required for artifact storage.**
Render's default web service has ephemeral local disk; without a persistent mount, a redeploy silently invalidates every stored model artifact, breaking checksum verification and the deployment gate's `artifact_verified` condition without any loud failure at deploy time. The `StorageService` interface (an existing abstraction, not new scope) absorbs this without touching calling code.
