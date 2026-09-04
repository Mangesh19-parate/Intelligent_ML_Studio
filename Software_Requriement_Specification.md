# ML Studio — Software Requirements Specification (SRS)
### v4 — Frozen. This document is the single canonical specification; v1–v3 and the review-response documents are superseded.

## Scope

ML Studio is a no-code, transparent tabular ML workbench that automates and records
the end-to-end experimentation lifecycle, enforcing reproducible, leakage-controlled
model evaluation. The platform (this document) is an engineering and integrative
contribution. A separate, explicitly scheduled research track (§11) evaluates a
specific feature-selection method as its own falsifiable hypothesis — the platform
does not itself claim research novelty.

Retired terms — never used in this document or its implementation: "AutoML,"
"Intelligent" (as a module name), "Production Ready," "Dataset Health Score,"
"Readiness Score," "guaranteed leakage-free," "PROJECT_OWNER"/"COLLABORATOR" (as
role names).

---

## 1. Core System Mechanics

### 1.1 Backend Architecture

```
FastAPI (Python)
│
├── API Layer            /api/v1/*
├── Service Layer         (OOP, one class per concern)
├── Repository Layer      SQLAlchemy ORM
├── Object Storage        StorageService interface, local FS for the prototype
└── PostgreSQL
```

### 1.2 Backend Stack

Python 3.11+, FastAPI, SQLAlchemy + Alembic, scikit-learn, pandas, NumPy, SHAP,
imbalanced-learn (constrained use, §2.6), PostgreSQL, JWT + bcrypt/passlib,
Pydantic v2, Docker + docker-compose. Frontend: React + Vite + Tailwind
(Modern Slate & Indigo theme), Plotly/Chart.js.

### 1.3 Authorization Model

Permission-based, never role-name-based in code. `require_permission(key)` is the
only authorization primitive used anywhere in the application.

**Canonical roles:** `ADMIN`, `ML_ENGINEER`, `DATA_STEWARD`, `DEPLOYMENT_MANAGER`, `VIEWER`

**Canonical permissions:** `READ`, `EDIT_DATA`, `TRAIN`, `DEPLOY`, `MANAGE_USERS`, `EXPORT`

| Role | READ | EDIT_DATA | TRAIN | DEPLOY | MANAGE_USERS | EXPORT |
|---|---|---|---|---|---|---|
| ADMIN | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| ML_ENGINEER | ✓ | ✓ | ✓ | ✗ | ✗ | ✓ |
| DATA_STEWARD | ✓ | ✓ | ✗ | ✗ | ✗ | ✗ |
| DEPLOYMENT_MANAGER | ✓ | ✗ | ✗ | ✓ | ✗ | ✓ |
| VIEWER | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ |

---

## 2. Core Processing Logic — Leakage-Safe Pipeline

### 2.0 Lifecycle Order (the Sixth Invariant)

Test-set isolation covers both model fitting and any data-dependent design decision.
Nothing distributional or target-aware runs before the outer split.

```
UPLOAD
  ↓  structural validation only — file parses, row/column counts, dtype
  ↓  inference (numeric/categorical/datetime/mixed). No correlation, no
  ↓  distribution shape, no target-aware logic yet.
LOCK OUTER SPLIT  (Development / Locked Test)
  ↓
DEVELOPMENT PROFILING  (Data Quality Index, correlation, distributions —
  ↓                      Development partition only, from here on)
DEVELOPMENT-ONLY RECOMMENDATIONS  (Diagnostics & Recommendations layer, §2.16)
  ↓
EXPERIMENT CONFIGURATION  (frozen: split/seed/CV/feature-selection method/
  ↓                         thresholds — §2.5)
LEAKAGE-SAFE TRAINING PIPELINE  (preprocessing + feature selection + model,
  ↓                               refit per fold — §2.6–2.8)
INNER CROSS-VALIDATION
  ↓
MODEL SELECTION  (primary metric authoritative — §2.9)
  ↓
FINAL REFIT ON DEVELOPMENT
  ↓
LOCKED TEST — ONE EVALUATION, THEN CONSUMED (§2.12)
  ↓
EXPERIMENT REGISTRY → DEPLOYMENT GATE (§2.13) → PREDICTION API (§2.14–2.15)
```

### 2.1 Dataset Registration & Structural Validation

`DatasetService.upload(project_id, file)` validates CSV/XLSX/JSON, saves via
`StorageService`, creates a `datasets` row (`stage=RAW`, next `version_number`).

`DatasetService.detect_structural_schema(dataset_id)` infers per-column dtype
(NUMERIC/CATEGORICAL/DATETIME/MIXED) and `missing_percentage`/`unique_count` from
dtype and null-count only — no correlation, no distribution shape, no target
awareness.

### 2.2 Outer Split: Development / Locked Test

Immediately after structural validation, before any profiling:

```
dataset_splits: split_type = DEVELOPMENT | LOCKED_TEST, split_seed, row_indices
```

The Locked Test partition is never passed into profiling, transformation fitting,
feature selection, or CV until the single final evaluation (§2.9, §2.12).

### 2.3 Data Quality Index (Development partition only)

```
Missingness Score        = 100 - (missing cells / total cells) * 100
Duplicate Rate Score     = 100 - (duplicate rows / total rows) * 100
Outlier Prevalence Score = 100 - (IQR-flagged numeric cells / total numeric cells) * 100
Type Consistency Score   = 100 - (mixed/ambiguous-dtype columns / total columns) * 100

Overall Data Quality Index = weighted average of the four sub-scores
  (default weights: Missingness 35%, Duplicate 25%, Outlier 20%, Type Consistency 20%
   — configurable per project, documented as a heuristic, not derived empirically)
```

If a dataset has no numeric columns, `Outlier Prevalence` = `N/A`, excluded from the
average, remaining weights renormalized. **The profiling API response always
includes the effective weights actually used**, not just the configured defaults, so
renormalization is never silent.

The Data Quality Index describes data *condition*, not fitness for a specific
modeling task — high outlier prevalence is not inherently bad (e.g. fraud detection).
This caveat is shown in the UI, not just this document.

### 2.4 Task-Type Detection

Split into two stages, matching the lifecycle order in §2.0:

**Stage A — structural (pre-split-safe):** target dtype only (numeric vs.
non-numeric).

**Stage B — distributional (Development-only, post-split):**

```
1. Non-numeric target → suggest CLASSIFICATION
2. Numeric target:
   a. unique_ratio = unique_values / row_count
   b. unique_count <= 20 AND unique_ratio < 0.05 → suggest CLASSIFICATION
   c. unique_count > 20 AND (non-integer values OR unique_ratio >= 0.05) → REGRESSION
   d. otherwise → AMBIGUOUS: show both options with supporting numbers, block
      silent auto-selection, require explicit user choice
```

`projects.task_type` allows `REGRESSION` / `CLASSIFICATION` / `UNDETERMINED`
(default until Stage B runs). `projects.task_type_confidence`:

```
HIGH      — unique_ratio more than 5 percentage points from the boundary in
            the rule above (5-point margin documented as a configurable heuristic)
MEDIUM    — within that 5-point margin
AMBIGUOUS — inside the rule's already-defined ambiguous band
```

### 2.5 Experiment Configuration (frozen at start, never edited after)

`experiments.experiment_config JSONB`:

```json
{
  "task_type": "CLASSIFICATION",
  "target": "churn",
  "split": {"seed": 42, "locked_test_pct": 20},
  "cv": {"strategy": "STRATIFIED_KFOLD", "folds": 5, "seed": 7},
  "preprocessing": {"snapshot_id": "..."},
  "feature_selection": {"method": "rank_aggregation_ensemble", "snapshot_id": "..."},
  "threshold_selection": {"objective": "F1", "search_range": [0.10, 0.90],
                            "resolution": 0.01, "tie_break": "closest_to_0.5"},
  "deployment_threshold": {"metric": "macro_f1", "min_value": 0.65}
}
```

Individually-queryable relational columns (`dataset_version_id`, `split_seed`,
`cv_strategy`, etc.) remain on `experiments` for fast lookups; `experiment_config`
is the single frozen source of truth.

### 2.6 Feature Transformation Engine

`TransformationService` (imputation, encoding, scaling, outlier handling) is
implemented as scikit-learn-compatible transformer steps, wrapped inside the same
`Pipeline` object as the estimator — refit per CV fold, never fit once on the whole
Development set before CV. Configuration is persisted (`transformation_configs`,
live/editable) and frozen per-experiment (`transformation_snapshots`, §2.17).
Learned state (actual medians, fitted vocabularies, fitted mean/std) is not
duplicated in the database — it lives in the serialized `.joblib` artifact, which is
authoritative for reproducing a prediction.

### 2.7 Feature Engineering: Rank-Aggregation Ensemble

Techniques: Correlation, Lasso (importance = `abs(coefficient)`), Random Forest,
Permutation, RFE, SHAP — implemented as available; **the 12-day build uses four**
(Correlation, Lasso, Random Forest, Permutation — §9).

```
For each technique T, rank features 1 (most important) .. p (least important),
based on |score|:

  p = 1  →  rank score = 1  (avoids the p-1 = 0 division)
  ties   →  average rank (e.g. two features tied at rank 2 and 3 both get 2.5)

  r_j,T = 1 - (rank_j,T - 1) / (p - 1)

EnsembleScore_j = (1 / T_applied) * Σ r_j,T     [T_applied, not the configured T —
                                                  see status handling below]
```

Each technique's status per fold is recorded, never silently dropped:

```
APPLIED  — ran and contributed
SKIPPED  — not applicable to this data shape (reason recorded, e.g.
           "RFE skipped: fewer than 3 candidate features")
FAILED   — raised an error (reason recorded, e.g. solver non-convergence);
           excluded from that fold's aggregation
```

This is explicitly a **heuristic rank-aggregation strategy**, not a claim of
mathematical optimality — its value is an empirical question, tested in §11.

### 2.8 Model Training Engine

`BaseModelTrainer` (abstract) → `RegressionTrainer`, `ClassificationTrainer`. Each
wraps the Day 2.6 `ColumnTransformer` + estimator inside one `Pipeline`.

**Algorithm set (fixed at six, no algorithm zoo):**

```
Regression:      Linear Regression (base), Ridge, Random Forest, Gradient Boosting
Classification:  Logistic Regression (base), Random Forest, Gradient Boosting
```

### 2.9 Evaluation Protocol

- Cross-validation runs on Development only (5-fold or Stratified 5-fold; **LOOCV
  removed** — disproportionate complexity for the value it adds here).
- Metrics: Regression — MAE, MSE, RMSE, R², Adjusted R². Classification — Accuracy,
  Precision, Recall, F1 (weighted + macro), ROC-AUC (OvR for multiclass), Confusion
  Matrix.
- **Leaderboard ranking is driven by a primary metric**, not a composite score:
  Regression primary = RMSE or MAE (configurable); Classification primary =
  macro-F1 (configurable to weighted-F1). Secondary metric (R² / ROC-AUC or PR-AUC)
  shown alongside.
- **Model Selection Score** (composite, formula below) is a **secondary UI
  convenience only** — never determines sort order:
  ```
  Regression:     normalize(R2) * 0.6 + (1 - normalize(RMSE)) * 0.4
  Classification: F1_weighted * 0.6 + ROC_AUC * 0.4
  ```
  Bands (visual aid only): 80–100 Strong Candidate, 60–79 Viable Candidate, 40–59
  Weak Candidate, <40 Poor Candidate.
- **Authoritative selection record** — independent of the composite score:
  `experiments.selection_metric`, `experiments.selection_direction`
  (MAXIMIZE/MINIMIZE), `experiments.selected_model_id`.
- Locked Test is evaluated exactly once per experiment generation, after the
  winning configuration is refit on all of Development (§2.12).

### 2.10 Diagnostics: Overfitting / Underfitting

Metric-direction-aware; comparison basis is always Train vs. CV-mean (never a single
fold, never the Locked Test):

```
Higher-is-better metrics (Accuracy, F1, R2, ROC-AUC):
   Gap = Train - CV_Mean;  "Potential overfitting" if Gap > threshold(metric)
Lower-is-better metrics (RMSE, MAE, MSE, Log Loss):
   Gap = CV_Mean - Train;  "Potential overfitting" if Gap > threshold(metric)

"Potential underfitting / weak predictive signal" if CV-mean performance is only
marginally above a naive baseline (mean-predictor for regression, majority-class
predictor for classification) AND train performance is also close to that baseline
— the margin is a configurable heuristic, not hard-coded; the label never asserts
certainty, since a low score may just mean the dataset is intrinsically hard.
```

`trained_models.fit_diagnosis`: `GOOD_FIT` / `POTENTIAL_OVERFIT` /
`POTENTIAL_UNDERFIT_WEAK_SIGNAL` / `INSUFFICIENT_DATA`.

### 2.11 Threshold Selection (binary classification only)

Selected using Development / inner-CV predictions only, never the Locked Test.
Search procedure is itself recorded (`experiment_config.threshold_selection`, §2.5)
including a deterministic tie-break rule (closest to 0.5 among tied-objective
thresholds). Frozen into `trained_models.decision_threshold` before Locked Test
evaluation. Multiclass uses standard argmax — no threshold-optimization UI.

### 2.12 Locked Test Consumption Rule

Once a model's Locked Test evaluation has run, that partition is **permanently
consumed** for that experiment generation. Reruns for debugging are stored with
`model_metrics.split = 'TEST_REUSED_DIAGNOSTIC'` and are **excluded from the
leaderboard, deployment_gates, and any reported model-selection evidence** — enforced
at the gate-check level, not just documented. A fresh, reportable evaluation requires
an **independent, previously unexposed test population** — a new file/version or a
new random split of substantially the same underlying observations does not create
independent evidence and must also be treated as `TEST_REUSED_DIAGNOSTIC`.

### 2.13 Deployment Gate

Deployment eligibility is an explicit multi-condition gate, never implied by a score
threshold:

```
deployment_gates: locked_test_evaluated (only accepts split='LOCKED_TEST' rows,
                     never TEST_REUSED_DIAGNOSTIC),
                   schema_locked, artifact_verified (checksum match),
                   lineage_complete, performance_threshold_passed (checked against
                     the FROZEN experiment_config.deployment_threshold — never an
                     editable post-hoc value), user_approved (explicit human
                     sign-off), gate_passed = AND of all above
```

### 2.14 Prediction & Explanation — Decoupled

```
POST /api/v1/predict/{deployment_id}           → fast path: prediction only
POST /api/v1/predict/{deployment_id}/explain   → prediction + local SHAP explanation
```

Deployed pipelines are cached in memory keyed by `deployment_id`. Global SHAP
summaries (explainability page) are cached, not recomputed per page load.

### 2.15 Prediction Logging & Privacy

```
prediction_logs: request_id, schema_hash, payload_mode (OFF/HASHED/REDACTED/FULL,
  default HASHED), input_payload (populated only if FULL/REDACTED),
  prediction_output, latency_ms, explanation_requested, explanation_latency_ms,
  status, requested_at
deployments.log_retention_days (default 30)
```

`HASHED` is labeled explicitly as **correlation/integrity, not anonymization** —
low-cardinality structured fields are brute-forceable even when hashed. `FULL`
requires explicit ADMIN/DEPLOYMENT_MANAGER opt-in with a visible warning.

### 2.16 Diagnostics & Recommendations Layer

Every surfaced recommendation carries a traceable structure — finding, evidence,
recommended action, risk, confidence — not a bare rule output:

```
recommendations: finding, evidence, recommended_action, risk_note,
  confidence (HIGH/MEDIUM/LOW), status (SUGGESTED/ACCEPTED/DISMISSED)
```

### 2.17 Reproducibility & Lineage

Reproducibility is **environment-qualified**, not absolute: "reproducible under the
captured software and execution environment," not "guaranteed identical results" —
numerical nondeterminism across hardware/library versions is real.

`experiments` captures: `dataset_version_id`, `dataset_content_hash` (SHA-256),
`split_seed`, `cv_seed`, `cv_strategy`, `fold_count`, `code_version` (git commit),
`python_version`, `sklearn_version`, `numpy_version`, `pandas_version`,
`model_library_versions` (JSONB).

`trained_models` gains `preprocessing_snapshot_id`, `feature_selection_snapshot_id`,
`artifact_checksum` (SHA-256, verified on load).

Fold-level vs. final feature selection are stored separately:

```
feature_selection_fold_results: experiment_id, fold_index, selected_features,
  technique_scores (raw + rank + status/status_reason per technique)
  Constraints: UNIQUE(experiment_id, fold_index); fold_index >= 0 AND < fold_count

feature_selection_snapshots: experiment_id, final_selected_features,
  final_selection_method
```

`transformation_snapshots`: `experiment_id`, `config_json` (frozen declared recipe —
not learned values, see §2.6).

---

## 3. The Six Invariants

1. **No learned preprocessing outside training folds.** Imputation, scaling,
   encoding, feature selection, augmentation fit only on training data.
2. **The Locked Test set is never touched** for feature selection, threshold
   selection, algorithm selection, or tuning, and is permanently consumed after one
   use (§2.12).
3. **Every experiment is reproducible under its captured environment**: dataset
   hash + seed + configuration + code version + recorded library versions (§2.17).
4. **Every model has full lineage**: Model → Experiment → Dataset version → Feature
   snapshot → Preprocessing snapshot → Evaluation protocol.
5. **Deployment requires an explicit, multi-condition gate** (§2.13), never a single
   score threshold.
6. **Test-set isolation covers data-dependent decisions, not just model fitting.**
   Profiling, DQI, task-type detection, and recommendations operate on Development
   only, after the outer split (§2.0).

---

## 4. Database Architecture

### 4.1 Entity Groups

```
USER MANAGEMENT        roles, permissions, role_permissions, users
PROJECT MANAGEMENT      projects
DATA                    datasets, dataset_columns, dataset_splits
PREPARATION             profiling_reports, cleaning_logs, transformation_configs,
                        transformation_snapshots
FEATURE ENGINEERING     feature_importance_scores, feature_selection_fold_results,
                        feature_selection_snapshots
EXPERIMENTATION         experiments, trained_models, model_metrics
DEPLOYMENT              deployment_gates, deployments, prediction_logs
DIAGNOSTICS             recommendations
AUDIT                   activity_logs
```

### 4.2 Key Tables Not Detailed Elsewhere in This Document

`users`, `roles`, `permissions`, `role_permissions` — §1.3.
`projects` — id, owner_id, project_name, task_type (REGRESSION/CLASSIFICATION/
UNDETERMINED), task_type_confidence, target_column, pipeline_stage,
data_quality_index, created_at, updated_at.
`datasets`, `dataset_columns`, `dataset_splits` — §2.1–2.2.
`profiling_reports` — id, dataset_split_id (Development split, not raw dataset_id),
report_json (includes `quality_breakdown` with effective weights), duplicate_row_count,
generated_at.
`cleaning_logs` — id, dataset_id, action_type, rows_before, rows_after,
performed_by, performed_at.
`transformation_configs` (live/editable), `transformation_snapshots` (frozen) — §2.6.
`feature_importance_scores` (live/editable current settings), plus the frozen
`feature_selection_fold_results` / `feature_selection_snapshots` — §2.7, §2.17.
`experiments`, `trained_models`, `model_metrics` — §2.5, §2.9, §2.17.
`deployment_gates`, `deployments`, `prediction_logs` — §2.13, §2.15.
`recommendations` — §2.16.
`activity_logs` — id, project_id, user_id, action, created_at.

### 4.3 Lineage Diagram

```
dataset_versions
   ├── dataset_splits (Development / Locked Test)
   └── experiments (experiment_config JSONB, env/library versions)
          ├── transformation_snapshots
          ├── feature_selection_fold_results (per fold)
          ├── feature_selection_snapshots (final)
          └── trained_models
                 ├── model_metrics (TRAIN / VALIDATION / CV_MEAN / LOCKED_TEST /
                 │                  TEST_REUSED_DIAGNOSTIC)
                 ├── deployment_gates
                 └── deployments
                        └── prediction_logs
```

### 4.4 Constraints & Indexes

```
task_type IN ('REGRESSION','CLASSIFICATION','UNDETERMINED')
UNIQUE(project_id, version_number) on datasets
UNIQUE(experiment_id, fold_index) on feature_selection_fold_results
fold_index >= 0 AND fold_index < fold_count
email UNIQUE
data_quality_index BETWEEN 0 AND 100 (or NULL pre-profiling)

Indexes: projects(owner_id), datasets(project_id), trained_models(experiment_id),
model_metrics(model_id), prediction_logs(deployment_id),
prediction_logs(requested_at), activity_logs(project_id)
```

---

## 5. Data Sourcing Strategy

Reference data (rarely changes): algorithm catalog, metric definitions, default
transformation strategies, two bundled sample datasets (one regression, one
classification — deferred to future work, §10). User-uploaded operational data:
raw dataset files, target/task declarations. System-generated derived data:
profiling reports, cleaning logs, feature scores, trained artifacts, prediction
logs. No live external API is required for core functionality.

---

## 6. API Responsibility Boundaries

```
/api/v1/auth
/api/v1/users, /api/v1/roles
/api/v1/projects
/api/v1/datasets            (upload = structural validation only, §2.1)
/api/v1/profiling           (Development split only, §2.3)
/api/v1/experiments         (configuration frozen at creation, §2.5)
/api/v1/feature-engineering
/api/v1/models               (leaderboard, download, explainability)
/api/v1/deployments
/api/v1/predict/{id}, /api/v1/predict/{id}/explain
/api/v1/analytics
```

---

## 7. MVP Scope — 12-Day Build

**"Documentation is not commitment."** No feature enters the 12-day build merely
because it is described in this document. Only the table below is built; everything
else is deferred by default (§10).

| Day | Focus |
|---|---|
| 1 | Foundation: FastAPI, PostgreSQL, RBAC (§1.3), dataset upload (structural validation only, §2.1), Docker, git-based code_version capture |
| 2 | Outer split + Locked Test storage (§2.2), dataset content hash |
| 3 | Profiling + Data Quality Index — Development partition only (§2.3) |
| 4 | Leakage-safe preprocessing pipeline (§2.6) |
| 5 | Feature selection: 4 methods (Correlation, Lasso, Random Forest, Permutation), rank aggregation (§2.7), fold-level storage |
| 6 | Training: 3 regression + 3 classification algorithms (§2.8) |
| 7 | Evaluation: 5-fold CV, one Locked Test pass, primary-metric leaderboard, fit diagnostics (§2.9–2.10) |
| 8 | Experiment lineage: experiment_config, seeds, library versions, snapshots, artifact checksum (§2.17) |
| 9 | Explainability: global + local SHAP, decoupled /predict vs /explain (§2.14) |
| 10 | Registry + deployment: artifact save/download, deployment gate (§2.13) |
| 11 | Frontend integration + monitoring dashboard |
| 12 | No new features. Adversarial/leakage tests (assert Locked Test indices never enter any training-fold), reproducibility test, artifact checksum test, demo rehearsal, documentation consistency pass against §1.3's canonical role table |

---

## 8. Deferred / Future Work (named explicitly, not silently dropped)

| Item | Reason deferred |
|---|---|
| Full 7-method feature-selection ensemble (RFE, SHAP added to the 4-method core) | Time cost vs. value for the 12-day core; architecture supports adding them later |
| Tier A modules (dataset versioning diff UI, report export, guided onboarding) | Not scheduled in the 12-day core |
| Tier B modules (constrained data augmentation, what-if simulator, notifications) | Not scheduled; augmentation specifically requires the numeric/encoded-dimension cap described below if ever built |
| Tier C modules (AutoML suggest-mode, champion–challenger, collaboration) | Not needed for this project's goals |
| Object-store lifecycle management, secret management, encryption at rest, rate limiting, durable job retry queues, full container/environment fingerprinting | Production-infrastructure hardening beyond an academic prototype's scope; `StorageService`'s interface-based design allows swapping later |
| Multiclass threshold optimization UI | Argmax is sufficient; not worth the added leakage-surface complexity |
| SMOTE / data augmentation, if built later | Constrained to numeric/encoded feature spaces below a configured dimensionality cap (default 50); disabled with a clear message otherwise, to avoid one-hot dimensionality explosions |

---

## 9. Research Track (Scheduled, Days 13–18 — Not Part of the 12-Day Platform Build)

### 9.1 Hypotheses

> **H1:** Rank aggregation combined with selection stability produces more stable
> feature subsets than individual feature-selection methods, while maintaining
> comparable predictive performance.
>
> **H0:** The proposed approach does not produce a meaningful improvement in
> feature-selection stability without unacceptable predictive-performance
> degradation.

These are two distinct experiments, not one:

| Method | Purpose |
|---|---|
| No selection | baseline |
| Correlation | baseline selector |
| Lasso | baseline selector |
| Random Forest importance | baseline selector |
| Permutation | baseline selector |
| RFE | baseline selector |
| **Rank aggregation (Experiment A)** | proposed ensemble — tests whether combining selectors works at all |
| **Rank aggregation + stability (Experiment B)** | proposed extension — tests whether incorporating selection frequency improves stability without unacceptable performance loss |

### 9.2 Schedule

```
Days 13–14   Research experiment infrastructure: standalone runner reusing the
             platform's training/evaluation services, not gated behind the UI
Days 15–16   Repeated experiments: >=2 regression + >=2 classification datasets,
             5-fold CV, 5–10 repeated runs per dataset per method. Stability
             uses repeated CV on the Development/training data only — the
             Locked Test stays completely outside the stability analysis; one
             final Locked Test evaluation per final configuration only.
Days 17–18   Statistical analysis, plots, research conclusion
```

Stability formula (Development-only):

```
Stability(feature j) = (number of runs where j is selected) / (total runs)
```

### 9.3 Statistical Protocol

Paired per-dataset performance differences between the proposed method and each
baseline. Report median difference, mean difference, 95% CI where feasible, effect
size. Use a **Wilcoxon signed-rank test** only where paired-observation assumptions
are met. With as few as 4 datasets, results are reported as "across the evaluated
benchmark datasets," never as a sweeping universal claim — small-N is an
undergraduate-appropriate empirical study, not grounds for strong generalization.

### 9.4 Outcome Framing

Written up as a genuine hypothesis test — either outcome is legitimate:

> **If supported:** "Experimental results support the proposed method under the
> evaluated datasets and protocol."
>
> **If not supported:** "The proposed method did not demonstrate consistent
> improvement over the evaluated baselines; the study contributes an empirical
> negative result and identifies conditions under which rank aggregation/stability
> is or is not beneficial."

No predetermined improvement target (e.g. "35%") drives the research design — that
number, if used at all, is an engineering/portfolio benchmark applied only after an
experiment supports it, never a research target set in advance.

---

## 10. Final Architectural Recommendation

```
                    ┌─────────────────────┐
                    │ Dataset Upload      │
                    │ Structural Valid.   │
                    └─────────┬───────────┘
                              ▼
                    ┌─────────────────────┐
                    │ Outer Split         │
                    │ Dev / Locked Test   │
                    └──────┬──────┬───────┘
                           │      │
                     Development  │
                           ▼      │
                ┌──────────────────────┐
                │ Profiling / DQI /    │
                │ Diagnostics (Dev)    │
                └──────────┬───────────┘
                           ▼
                ┌──────────────────────┐
                │ Experiment Config    │
                │ (frozen)              │
                └──────────┬───────────┘
                           ▼
                ┌──────────────────────┐
                │ Leakage-Safe Pipeline│
                │ preprocess/select/   │
                │ model — refit/fold   │
                └──────────┬───────────┘
                           ▼
                ┌──────────────────────┐
                │ Inner CV             │
                └──────────┬───────────┘
                           ▼
                ┌──────────────────────┐
                │ Evaluation           │
                │ primary metric first │
                └──────────┬───────────┘
                           ▼
                ┌──────────────────────┐
                │ Model Selection      │
                └──────────┬───────────┘
                           ▼
                ┌──────────────────────┐
                │ Final Dev Refit      │
                └──────────┬───────────┘
                           ▼
                ┌──────────────────────┐
                │ Locked Test          │
                │ ONE eval, consumed   │
                └──────────┬───────────┘
                           ▼
                ┌──────────────────────┐
                │ Experiment Registry  │
                │ full lineage         │
                └──────────┬───────────┘
                           ▼
                ┌──────────────────────┐
                │ Deployment Gate      │
                └──────────┬───────────┘
                           ▼
                ┌──────────────────────┐
                │ Prediction / Explain │
                │ privacy-aware logs   │
                └──────────┬───────────┘
                           ▼
                ┌──────────────────────┐
                │ Monitoring / Audit   │
                └──────────────────────┘
```

This architecture is production-**oriented** (schema validation, versioning, audit
logging, deployment gating — patterns a real production system needs) built on
prototype-**grade** infrastructure (local storage, synchronous background tasks) —
that distinction is stated explicitly in the final report, not glossed over.