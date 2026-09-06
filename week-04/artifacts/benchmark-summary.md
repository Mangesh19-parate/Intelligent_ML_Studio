# Day 4 — Actual (Not Estimated) 5-Fold CV Benchmark Report
**Generated:** 2026-09-06 14:11:29 UTC  
**Standard:** SRS v9 §10 — Actual Timing vs $t_{\text{fold}_1} \times 5$ Estimation

## Executive Summary
Direct wall-clock measurement of full 5-fold cross validation reveals the impact of per-fold data slicing, feature transformation pipelines, and model training overhead.

## Benchmark Results Table

| Dataset | Type | Rows | Features | Algorithm | Transform (1-Fold) | 1-Fold 1-Model | Actual 5-Fold CV | Estimated 5-Fold | Estimation Formula | Discrepancy % |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| Synthetic Small | SYNTHETIC | 500 | 10 | `LinearRegression` | 0.0433s | 0.0013s | **0.0799s** | 0.2230s | `fold_1_time_sec * 5` | 179.1% |
| Synthetic Small | SYNTHETIC | 500 | 10 | `Ridge` | 0.0146s | 0.0089s | **0.0817s** | 0.1175s | `fold_1_time_sec * 5` | 43.8% |
| Synthetic Small | SYNTHETIC | 500 | 10 | `RandomForestRegressor` | 0.0152s | 0.0899s | **0.5472s** | 0.5251s | `fold_1_time_sec * 5` | 4.0% |
| Synthetic Medium | SYNTHETIC | 5,000 | 25 | `LinearRegression` | 0.0409s | 0.0388s | **0.3905s** | 0.3988s | `fold_1_time_sec * 5` | 2.1% |
| Synthetic Medium | SYNTHETIC | 5,000 | 25 | `Ridge` | 0.0456s | 0.0101s | **0.2259s** | 0.2783s | `fold_1_time_sec * 5` | 23.2% |
| Synthetic Medium | SYNTHETIC | 5,000 | 25 | `RandomForestRegressor` | 0.0408s | 0.3696s | **1.6782s** | 2.0520s | `fold_1_time_sec * 5` | 22.3% |
| California Housing | REAL_STRESS | 20,640 | 8 | `LinearRegression` | 0.0212s | 0.0032s | **0.1211s** | 0.1217s | `fold_1_time_sec * 5` | 0.5% |
| California Housing | REAL_STRESS | 20,640 | 8 | `Ridge` | 0.0210s | 0.0020s | **0.1109s** | 0.1147s | `fold_1_time_sec * 5` | 3.5% |
| California Housing | REAL_STRESS | 20,640 | 8 | `RandomForestRegressor` | 0.0215s | 0.4633s | **2.1316s** | 2.4244s | `fold_1_time_sec * 5` | 13.7% |

## Observations & Architectural Takeaways
1. **Actual vs Estimated Discrepancy**: Naive estimation ($t_{\text{fold}_1} \times 5$) neglects fold-variance in tree building and GC/memory overhead.
2. **Preprocessing Overhead**: Transformation pipelines fit per-fold in milliseconds, ensuring strict zero-leakage isolation without bottlenecking CV throughput.
3. **Artifact Location**: Recorded in [`week-04/artifacts/benchmark-timing.csv`](./benchmark-timing.csv).
