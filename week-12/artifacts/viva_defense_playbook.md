# Intelligent ML Studio — Adversarial Viva Defense Playbook

**Milestone:** Phase 12 (Week 12) — Technical Viva & Defense Guide  
**Target:** Oral Examination, Defense Committee & Technical Audit Panel  
**Repository:** `Intelligent_ML_Studio`

---

## 1. "How do you structurally guarantee zero data leakage during preprocessing and feature selection?"

**Examiner Attack:** *"Many platforms claim they don't leak data, but scalers and encoders still observe global statistics before splitting. How does your architecture enforce isolation?"*

**Defense Answer:**
1. **Outer Split Barrier:** Partitioning into Development (80%) and Locked Test (20%) occurs at ingestion (`outer_split.py`) before any preprocessing, imputation, scaling, or selection can execute.
2. **Fit-Transform Scoping:** Every transformer (imputer, scaler, one-hot encoder) and feature selector implements a strict Scikit-Learn `Pipeline` fitted **exclusively inside individual training folds** (`X_train_fold`). Validation fold slices (`X_val_fold`) and the Locked Test partition (`X_locked_test`) only ever invoke `.transform()`, never `.fit()`.
3. **Automated Verification:** Verified in our Consolidated Invariant Suite (**Domain 2**, `test_consolidated_invariants.py`) and Attack Lab (**ATK-01** and **ATK-02**), where attempting to fit outside folds is structurally blocked.

---

## 2. "Why does the platform reject `RANK_AGGREGATION_STABILITY` if your research track proves it works?"

**Examiner Attack:** *"If your research track showed a +14% improvement in feature stability with RANK_AGGREGATION_STABILITY, why does the platform API reject it with HTTP 400? Isn't that a bug or missing feature?"*

**Defense Answer:**
1. **Circular Dependency Problem (ADR-005, SRS §2):** Computing selection stability ($S_j = \frac{\text{count}(j \text{ selected})}{\text{total runs}}$) requires an existing population of repeated cross-validation runs. In an ordinary, single platform experiment run, this population does not yet exist. Exposing it on the platform would create an impossible circular dependency (needing to know future selection frequencies to perform the initial selection).
2. **Four-Phase Research Protocol:** In the research runner, we execute an explicit 4-phase protocol (Generate Population $\rightarrow$ Compute Stability $\rightarrow$ Combine Scores $\rightarrow$ Downstream Evaluation). 
3. **Clean Architectural Separation:** Rather than creating a flawed or pseudo-stability heuristic on the platform, we maintain strict engineering integrity: the platform offers plain `RANK_AGGREGATION`, while `RANK_AGGREGATION_STABILITY` is restricted to the research module where repeated-run populations actually exist.

---

## 3. "Why can't a user re-run evaluation against the Locked Test partition?"

**Examiner Attack:** *"Why not allow users to evaluate multiple candidate models against the Locked Test set to see which one performs best?"*

**Defense Answer:**
1. **Preventing Test Set Overfitting (Goodhart's Law / Adaptive Overfitting):** In traditional ML workflows, evaluating multiple candidate models on the test set degrades the test partition into a second validation partition. Repeatedly picking the highest test score creates post-hoc optimism bias.
2. **Single Consumption Invariant (Domain 6, ADR-008):** In Intelligent ML Studio, model selection is decided **exclusively on Development Cross-Validation**. The winning model is evaluated against the Locked Test partition **exactly once** to provide an unbiased generalization estimate.
3. **Diagnostic Flagging:** If an operator re-evaluates the test set for debugging purposes, the system records it but permanently tags the metric as `TEST_REUSED_DIAGNOSTIC`, preventing it from being used for deployment qualification.

---

## 4. "How does Reproduce-Experiment prove reproducibility without touching the Locked Test partition?"

**Examiner Attack:** *"If your reproduce endpoint doesn't evaluate the test partition, how can you claim the experiment was reproduced?"*

**Defense Answer:**
1. **SRS §1 Redefinition (ADR-008):** Re-running the full canonical pipeline to reproduce an experiment risked either re-consuming the Locked Test partition or creating a second reportable evaluation, violating the test-consumption invariant.
2. **Diagnostic Replay Mode:** `POST /experiments/{id}/reproduce` executes a non-mutating Development-only replay: using the identical dataset content hash, frozen feature snapshot, CV splits, and seeds, it re-executes the cross-validation portion.
3. **Tolerance Assertion:** It creates an isolated `REPRODUCIBILITY_RUN` record comparing the newly observed CV metric against the originally recorded metric within float tolerance ($10^{-5}$), confirming reproducibility without mutating the source experiment or touching the test partition.

---

## 5. "How is separation of duties enforced to prevent an engineer from approving their own model?"

**Examiner Attack:** *"In a startup or small team, what prevents an engineer who trains a model from simply deploying it themselves?"*

**Defense Answer:**
1. **Model-Level vs. Deployment-Level Separation (SRS §4, ADR-006):** We split gate conditions into two phases:
   - **Model Eligibility (5 conditions):** Automated checks owned by the Gate Service (`locked_test_evaluated`, `schema_locked`, `artifact_verified`, `lineage_complete`, `performance_threshold_passed`).
   - **Deployment Approval (1 condition):** Explicit human sign-off owned by the Deployment Service.
2. **Structural Inequality Constraint:** The gate check explicitly validates `deployment.approved_by != trained_model.created_by`. Even if a user has the `DEPLOY` permission, attempting to approve their own model is rejected by the service and recorded as a failed gate condition in the audit log.
3. **Audited Permission Overrides (ADR-011):** Granular user-level overrides allow designated peer reviewers to approve deployments without requiring broad global admin access.

---

## 6. "Why does dataset content hashing occur before row_uid injection?"

**Examiner Attack:** *"Why compute two hashes (raw_upload_sha256 and dataset_content_hash)? Why not just hash the final dataframe?"*

**Defense Answer:**
1. **Deduplication & Content Identity (ADR-007, SRS §3):** `row_uid`s are freshly generated UUIDs assigned per upload. If identical CSV files are uploaded by different users or projects, hashing after `row_uid` injection would produce different hashes for identical tabular data.
2. **Four-Step Sequence:**
   1. `raw_upload_sha256`: Hash of literal upload byte stream (for raw audit provenance).
   2. Tabular parsing and validation.
   3. `dataset_content_hash`: SHA-256 over the parsed canonical dataframe before adding row UIDs.
   4. `row_uid` assignment: Injected purely as partition and split tracking metadata.

---

## 7. "Why are admission-control features separated from benchmark observations?"

**Examiner Attack:** *"Why not just measure peak RAM during execution to decide whether to stop an experiment?"*

**Defense Answer:**
1. **Preventing Out-of-Memory Crashes (ADR-010, SRS §5):** Measuring peak RAM requires having *already* executed the expensive operation. If a dataset is 100x larger than memory capacity, waiting to measure peak RAM causes worker OOM crashes and corrupts server state.
2. **Pre-Execution Guardrails:** Admission control evaluates only cheap, pre-execution structural metadata: row count, raw column count, categorical cardinality, and estimated encoded dimensionality.
3. **Offline Calibration:** The post-execution benchmark observations (peak RAM, actual CV time, SHAP runtime) collected during Week 4 are used offline to calibrate admission thresholds, not at runtime.

---

## 8. "How do you defend research validity with only 4 benchmark datasets?"

**Examiner Attack:** *"Can you really claim rank aggregation is superior based on only 4 datasets?"*

**Defense Answer:**
1. **Honest Small-N Framing (SRS §9.3, ADR-014):** We explicitly disclaim universal generalization claims. Our conclusion is formally framed as *"across the evaluated benchmark datasets and fixed-model protocol"*.
2. **High Statistical Power Per Dataset:** While dataset count is 4, each dataset was evaluated over **8 repeats of 5-fold cross-validation** (40 paired folds per method, 320 runs per dataset, 1,280 total CV evaluations).
3. **Controlled Parity (ADR-014):** We fixed the downstream reference estimator (`RandomForest`) across all 8 methods, strictly isolating the feature selection variable from algorithm-selection variance.
4. **Boundary Discovery:** The study demonstrated clear operating boundaries: stability weighting provides strong gains (+13% to +14%) on higher-dimensional datasets ($p \ge 30$), while lower-dimensional datasets ($p \le 12$) naturally reach stability ceilings.

---

## 9. "Why is there only one canonical `run_experiment()` execution path?"

**Examiner Attack:** *"Why not have separate lightweight training functions for fast testing or prototyping?"*

**Defense Answer:**
1. **Parity and Architectural Contract:** Having a separate 'fast' or 'prototype' training path is the #1 source of architectural drift and hidden leakage in commercial ML tools.
2. **Single Canonical Path:** In Intelligent ML Studio, the platform's Machine Learning stage and the research runner's experimental harnesses execute through the exact same canonical CV execution logic.
3. **Zero Divergence:** What is tested in research and audited in QA is 100% identical to what executes in production.

---

## 10. "What happens if a database commit fails midway through experiment training?"

**Examiner Attack:** *"If your model finishes training and saves an artifact to disk, but the database crashes before committing the status, how does the system recover?"*

**Defense Answer:**
1. **Transactional Boundaries (Domain 6, `test_lineage_and_reproducibility.py`):** Artifact writes and database state transitions are sequenced with cleanup handlers. If a DB commit fails during model finalization, the transaction rolls back, and any orphaned temporary artifact files on disk are cleaned up.
2. **Safe State Recovery:** The experiment status remains `TRAINING` or moves to `FAILED` with explicit error logging, preventing 'ghost' models or corrupt database pointers.
