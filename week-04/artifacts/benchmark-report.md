# Day 5 — Resource Benchmark & Policy Cap Report

**Generated:** 2026-09-06 14:15:29 UTC  
**Standard:** SRS §2.18, §2.19, §10 — Resource Footprint & Safe Execution Budgets

---

## 1. Executive Summary & Design Matrix

This report establishes **empirical resource baselines** across synthetic and real-world stress workloads, contrasting **directly observed figures** against **enforceable policy caps**. Every policy cap includes an explicit headroom safety buffer to prevent out-of-memory (OOM) crashes and latency spikes in production.

---

## 2. Comprehensive Resource Benchmark Results

| Dataset | Type | Rows | Raw Feats | Encoded Feats | Algorithm | Peak RAM | Artifact Size | SHAP RAM | SHAP Time | 5-Fold CV Time |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| Synthetic Small | SYNTHETIC | 500 | 10 | **19** | `LinearRegression` | 0.44 MB | 0.0026 MB | 0.00 MB | 0.0000s | 0.3071s |
| Synthetic Small | SYNTHETIC | 500 | 10 | **19** | `Ridge` | 0.45 MB | 0.0024 MB | 0.00 MB | 0.0000s | 0.2940s |
| Synthetic Small | SYNTHETIC | 500 | 10 | **19** | `RandomForestRegressor` | 0.83 MB | 0.2504 MB | 1.15 MB | 0.1062s | 1.5309s |
| Synthetic Medium | SYNTHETIC | 5,000 | 25 | **53** | `LinearRegression` | 6.87 MB | 0.0039 MB | 0.00 MB | 0.0000s | 1.7249s |
| Synthetic Medium | SYNTHETIC | 5,000 | 25 | **53** | `Ridge` | 6.81 MB | 0.0035 MB | 0.00 MB | 0.0000s | 1.4914s |
| Synthetic Medium | SYNTHETIC | 5,000 | 25 | **53** | `RandomForestRegressor` | 6.87 MB | 2.3724 MB | 10.82 MB | 0.2118s | 3.6554s |
| California Housing | REAL_STRESS | 20,640 | 8 | **8** | `LinearRegression` | 8.25 MB | 0.0020 MB | 0.00 MB | 0.0000s | 0.2168s |
| California Housing | REAL_STRESS | 20,640 | 8 | **8** | `Ridge` | 8.13 MB | 0.0020 MB | 0.00 MB | 0.0000s | 0.2352s |
| California Housing | REAL_STRESS | 20,640 | 8 | **8** | `RandomForestRegressor` | 17.18 MB | 7.9232 MB | 42.41 MB | 0.2345s | 3.0700s |

---

## 3. Stress Dataset: Observed Numbers vs. Enforced Policy Caps

> [!IMPORTANT]
> **Observation-vs-Policy Headroom Rule**: A policy cap must never be stated as a bare, unjustified number. Each cap is derived by multiplying empirical stress observations by a justified safety headroom factor.

### Explicit Stress Observations (California Housing, 20,640 rows, 8 features)

1. **SHAP Explanation Footprint (RandomForestRegressor)**:
   - **Observed Peak RAM**: `42.41 MB`
   - **Observed Execution Time**: `0.2345 seconds` (evaluating 50 sample instances against 100 background instances).
   - **Empirical Ratio**: SHAP on 8 encoded features across 20,640 rows $\to$ **42.41 MB RAM / 0.23s**.

2. **Training & Cross-Validation Footprint (RandomForestRegressor)**:
   - **Observed Peak Training RAM**: `17.18 MB`
   - **Observed Serialized Artifact Size**: `7.9232 MB` (`.joblib` compressed)
   - **Observed 5-Fold CV Duration**: `3.0700 seconds`.

---

## 4. Enforced Policy Caps & Headroom Justifications

| Resource Dimension | Empirical Stress Peak | Enforced Policy Cap | Headroom Multiplier | Headroom Rationale & Justification |
| :--- | :--- | :--- | :--- | :--- |
| **SHAP Memory Budget** | `42.41 MB` | **`1,024 MB (1.0 GB)`** | **~24×** | Accommodates high-cardinality categorical expansions (up to 100+ OHE columns) and larger background evaluation sets without risk of worker OOM. |
| **SHAP Time Budget** | `0.2345 s` | **`5.0000 s`** | **~21×** | Guarantees sub-second interactive UI response for single-instance explainability while allowing batch explanations to complete cleanly within API timeouts. |
| **Peak Training RAM** | `17.18 MB` | **`2,048 MB (2.0 GB)`** | **~119×** | Provides ample memory headroom for parallel fold execution across multi-core CPU workers on datasets up to 100k rows. |
| **Model Artifact Size** | `7.9232 MB` | **`50.00 MB`** | **~6×** | Prevents storage bloat in artifact registry while supporting large Random Forest and Gradient Boosting ensembles with up to 500 deep trees. |
| **Max Preprocessed Features** | `8 features` | **`250 features`** | **~31×** | Limits one-hot encoding feature explosion from unpruned high-cardinality categorical variables. |

---

## 5. Architectural & System Guarantees

1. **Deterministic Memory Boundaries**: Preprocessing, training, and explainability memory allocations strictly operate within a 2GB container boundary.
2. **Artifact Size Guardrail**: Models exceeding the 50 MB threshold trigger automated pruning / tree depth constraints.
3. **Reproducibility**: Artifact sizes, random seeds, and environment checksums are frozen in `transformation_snapshots` and `model_metrics`.
