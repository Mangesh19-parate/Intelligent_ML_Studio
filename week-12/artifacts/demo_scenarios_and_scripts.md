# Intelligent ML Studio — Demo Walkthrough Scripts & Scenarios

**Milestone:** Phase 12 (Week 12) — Final Demonstration & Presentation Package  
**Platform:** Intelligent ML Studio  
**Target Audience:** Technical Examiners, Viva Committee, Enterprise ML Auditors

---

## Overview of Demonstration Scenarios

Three scripted, repeatable demonstration scenarios are designed to showcase the complete engineering and research capabilities of Intelligent ML Studio:

1. **Demo 1: The 8-Stage Leak-Free ML Workflow** — End-to-end traversal from raw data upload to cryptographic Model Passport.
2. **Demo 2: Enterprise Governance & Deployment Gate with Separation of Duties** — Automated model eligibility checks, self-approval prevention, deployer override, and real-time inference monitoring.
3. **Demo 3: Leakage Attack Lab & Empirical Research Track** — Adversarial verification of 4 leakage vectors and empirical presentation of the 4-phase feature stability research track.

---

## Demo 1: The 8-Stage Leak-Free Tabular ML Workflow

### Objective
Demonstrate how Intelligent ML Studio prevents methodological leakage at every stage of the tabular ML lifecycle while delivering comprehensive lineage.

### Step-by-Step Script

#### Stage 1: Data Upload & Structural Validation
- **Action:** Upload `california_housing.csv` (20,640 rows, 8 numeric features).
- **Under the Hood:** 
  1. Computes `raw_upload_sha256` on uploaded bytes.
  2. Parses CSV and validates schema (zero empty column names, no infinite values).
  3. Computes `dataset_content_hash` on canonical dataframe.
  4. Generates unique UUID `row_uid` per row.
- **Presenter Talking Point:** *"Notice that dataset content hashing happens before row_uid injection. If an identical file is uploaded under another project, its content identity is identical, guaranteeing clean deduplication and lineage."*

#### Stage 2: Outer Partitioning (Development vs. Locked Test)
- **Action:** Configure 80/20 outer split. Click **Lock Partition**.
- **Under the Hood:** 16,512 rows allocated to Development; 4,128 rows allocated to Locked Test. The Locked Test partition is cryptographically isolated.
- **Presenter Talking Point:** *"All subsequent profiling, transformations, feature selections, and model training occur exclusively on the Development slice. The Locked Test partition cannot be accessed by any preprocessing or training code."*

#### Stage 3: Data Analysis & Profiling (DQI)
- **Action:** Open Data Analysis stage. Review Data Quality Index (DQI: 98.5/100).
- **Under the Hood:** Evaluates 4 orthogonal sub-scores (Completeness, Validity, Uniqueness, Consistency). Automatically detects task type as `REGRESSION` with 100% confidence.

#### Stage 4: Feature Transformation & Pre-Execution Benchmark
- **Action:** Configure Log Transformer on skewed features (`MedInc`, `Population`) and Standard Scaler. Review live transformation preview and memory footprint estimate.
- **Under the Hood:** Admission control guardrail confirms dataset dimensionality and row counts are well within safe bounds before execution.

#### Stage 5: Feature Engineering & Rank Aggregation
- **Action:** Run 5-fold CV feature selection using `RANK_AGGREGATION`.
- **Under the Hood:** Executes 4 base selectors (Correlation, Lasso, Random Forest, Permutation) strictly inside training folds. Combines rank scores via reciprocal rank aggregation with deterministic tie-breaking.

#### Stage 6: Canonical Model Training & Full CV Run
- **Action:** Launch training across 6 algorithms (Linear Regression, Ridge, Random Forest, Extra Trees, Gradient Boosting, LightGBM) with 5-Fold CV.
- **Under the Hood:** Atomic concurrency mutex prevents concurrent runs. All algorithms fit on identical cross-validation folds.

#### Stage 7: Evaluation & Single Locked Test Consumption
- **Action:** Leaderboard ranks models by CV RMSE. `RandomForest` wins with CV RMSE `0.5374`. Click **Evaluate Locked Test**.
- **Under the Hood:** Evaluates winning model on Locked Test partition (Test RMSE: `0.5130`). Flips `locked_test_consumed = True`. Subsequent requests are tagged `TEST_REUSED_DIAGNOSTIC`.
- **Presenter Talking Point:** *"The platform enforces single test consumption. You cannot tune hyperparameters against the test set or iteratively peek at test performance."*

#### Stage 8: Lineage, Diagnostics & Model Passport
- **Action:** View SHAP Summary Plot, Permutation Importance, and open the **Model Passport**.
- **Under the Hood:** Generates tamper-proof Passport detailing dataset SHA-256, pinned package versions (`scikit-learn==1.4.2`, `numpy==1.26.4`), 5-fold validation metrics, locked test score, and artifact checksum.

---

## Demo 2: Enterprise Governance & Deployment Gate

### Objective
Demonstrate multi-condition automated model eligibility, separation of duties, deployment approvals, and live prediction monitoring.

### Step-by-Step Script

#### Part 1: Automated Model Eligibility Check (5 Model-Level Conditions)
- **Actor:** `alice_engineer` (Role: `ML_ENGINEER`, Permissions: `[DATA_UPLOAD, DATA_TRANSFORM, TRAIN, EVALUATE, READ]`).
- **Action:** Alice navigates to Model Registry and requests deployment of `Model-RF-Housing`.
- **Under the Hood:** Deployment Gate Service runs `check_model_eligibility()` verifying:
  1. `locked_test_evaluated`: PASSED (Score: 0.5130)
  2. `schema_locked`: PASSED (8 features locked)
  3. `artifact_verified`: PASSED (SHA-256 verified on disk)
  4. `lineage_complete`: PASSED (Dataset hash + pinned environment present)
  5. `performance_threshold_passed`: PASSED (RMSE < 0.60 threshold)
- **Result:** `ModelState` automatically transitions from `ARTIFACT_VERIFIED` to `DEPLOYABLE`.

#### Part 2: Separation of Duties Enforcement (Self-Approval Rejection)
- **Action:** Alice attempts to approve her own deployment request.
- **Under the Hood:** Gate check evaluates `approved_by != model.created_by`.
- **Result:** **REJECTED with HTTP 403 / Gate Condition Failed: `user_approved: FAILED (Self-approval prohibited)`**.
- **Presenter Talking Point:** *"Even an admin or engineer with approval rights cannot approve their own model. Separation of duties is structurally enforced at the database and service layer."*

#### Part 3: Secondary Reviewer Approval & Deployment
- **Actor:** `bob_lead` (Role: `ML_ENGINEER` with explicit `DEPLOY` permission override).
- **Action:** Bob logs in, reviews the Experiment Health Report and Model Passport, and approves deployment.
- **Result:** Deployment transitions to `APPROVED` $\rightarrow$ `DEPLOYED`. Active endpoint: `/api/v1/deployments/{id}/predict`.

#### Part 4: Live Prediction & Drift Monitoring
- **Action:** Send 10 inference requests via `/predict`. Send 5 corrupted outlier samples. Open Monitoring Dashboard.
- **Under the Hood:** Tracks prediction latency (< 40ms) and computes Kolmogorov-Smirnov drift test comparing incoming feature distributions against training baseline.

---

## Demo 3: Leakage Attack Lab & Empirical Research Track

### Objective
Demonstrate adversarial leakage verification and present the empirical 4-phase research track findings.

### Step-by-Step Script

#### Part 1: Leakage Attack Lab Execution
- **Action:** Open Leakage Attack Lab view (`backend/tests/test_attack_lab.py`).
- **Demonstrate ATK-01 (Global Preprocessing Scaling):**
  - *Broken Pipeline:* Scaler fit over full dataset prior to CV. CV RMSE appears inflated/optimistic.
  - *Studio Control:* Scaler fit strictly inside folds. Result: Control held.
- **Demonstrate ATK-02 (Supervised Feature Selection Pre-CV):**
  - *Broken Pipeline:* Selectors peek at target variables across validation folds. CV RMSE falsely deflated from 0.5432 to 0.4954 (optimism bias: +0.0617 gap).
  - *Studio Control:* Feature selection fit inside CV loop. Result: Control held.
- **Demonstrate ATK-03 (Decision Threshold Test Peeking):**
  - *Broken Pipeline:* Threshold tuned on test partition creates post-hoc optimism bias (+0.0250 F1).
  - *Studio Control:* Threshold tuned strictly on Out-of-Fold (OOF) predictions. Result: Control held.
- **Demonstrate ATK-04 (Test Split Model Selection Reuse):**
  - *Broken Pipeline:* Test set reused across multiple model iterations.
  - *Studio Control:* Single test consumption rule tags re-evaluations as `TEST_REUSED_DIAGNOSTIC`. Result: Control held.

#### Part 2: Empirical Research Track Results (SRS §9, ADR-014)
- **Presenter Script:**
  1. *"We pre-registered hypotheses H1 vs H0 freezing 4 datasets, 8 methods, and 1,280 CV runs."*
  2. *"Executed the 4-phase stability protocol (SRS §2) on Development CV data only."*
  3. *"Results: On higher-dimensional datasets (`breast_cancer`, `adult_income`), stability-aware rank aggregation improves feature selection stability by **+13.3% to +14.3%** over plain rank aggregation."*
  4. *"Statistical significance testing across 160 paired folds confirms predictive performance differences are statistically non-significant ($p > 0.25$), confirming H1: robustness is gained without accuracy sacrifice."*
