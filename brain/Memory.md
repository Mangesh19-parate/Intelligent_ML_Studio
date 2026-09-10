# ML Studio — Memory

Session-priming context. Read this before touching code in a new session — it exists so an agent (or a new contributor) doesn't re-derive, contradict, or accidentally re-litigate decisions already frozen.

## Frozen Contract Values (never invent alternatives)

```
Algorithms (six, fixed): LINEAR_REGRESSION, RANDOM_FOREST_REGRESSOR, GRADIENT_BOOSTING_REGRESSOR,
  LOGISTIC_REGRESSION, RANDOM_FOREST_CLASSIFIER, GRADIENT_BOOSTING_CLASSIFIER
Selectors (four, fixed): CORRELATION_SELECTOR, LASSO_SELECTOR,
  RANDOM_FOREST_IMPORTANCE_SELECTOR, PERMUTATION_IMPORTANCE_SELECTOR
Feature-selection defaults: TOP_K_PERCENT, alpha=0.25, k_min=5, k_max=50, min_applied_methods=2
Stability formula (research-only): FinalScore_j = 0.7*BaseScore_j + 0.3*Stability_j
Reproducibility tolerance: metric_absolute_tolerance=1e-3, metric_relative_tolerance=0.01
Hash algorithm: SHA-256, computed on the canonical parsed dataset BEFORE row_uid assignment
Roles: ADMIN, USER only. Permissions: READ, EDIT_DATA, TRAIN, DEPLOY, MANAGE_USERS, EXPORT.
```

## Things Already Decided — Do Not Re-Litigate

- "Intelligent" / "Intelligence" as a module name is retired. Use "Diagnostics." (Multiple rounds re-flagged this before it stuck — see Decision.md ADR-002.)
- Six algorithms, no zoo. Do not add XGBoost/LightGBM/CatBoost/TabNet/etc. even if a reference or a "nice to have" suggests it.
- `RANK_AGGREGATION_STABILITY` is research-only, blocked at the platform API. This was a genuine circular-dependency bug (stability needs a repeated-run population that doesn't exist during a single platform run) — not an oversight to "fix" by exposing it platform-side.
- The state machine answers legality only ("can this transition happen?"); the deployment gate answers eligibility ("should it?"). Never merge these two concerns into one check.
- `ModelState.DEPLOYABLE` is owned exclusively by the Gate Service's Model Eligibility Check, and is re-checkable — not a permanent fact set once and forgotten.
- Reproduce-Experiment never touches the Locked Test and never mutates the source experiment. It produces a separate `reproducibility_run` record.
- No chatbot, no "AI Copilot," no generative/LLM-based recommendation text. Everything in the Diagnostics/recommendations layer is rule-based with a recorded evidence trail.
- No single "Readiness Score" / "Dataset Health Score." The DQI is always shown as four sub-scores with effective weights.
- Two identity roles only (ADMIN, USER); separation of duties on deployment approval is enforced via per-user `DEPLOY` permission overrides, not a third role.

## Retired Terms (never reintroduce under a different name)

"AutoML," "Intelligent"/"Intelligence" as a module name, "Production Ready," "Dataset Health Score," "Readiness Score," "guaranteed leakage-free," `PROJECT_OWNER`/`COLLABORATOR` as role names, `dataset_versions` as a table name (use `datasets` + `version_number`).

## Evidence Directory Convention

```
week-NN/
  evidence.md
  test-report.txt
  artifacts/
  screenshots/
  logs/
```

## Where the Real Detail Lives

- Full spec: `SRS_v10_Canonical.md`
- Data flow / ownership: `DFD_v11.md`
- Day-by-day tasks: `84_Day_Antigravity_Prompts_v3.md`
- Why any of the above is true: `Decision.md`
- Agent operating rules: `Agents.md`

## If Something Here Seems Wrong

It might be — implementation sometimes surfaces a real problem in a "frozen" decision. The correct response is to flag it explicitly and add a new entry to `Decision.md` explaining what changed and why, not to silently work around it or quietly restore an earlier rejected pattern.
