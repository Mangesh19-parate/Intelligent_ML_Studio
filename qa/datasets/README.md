# Acceptance Test Datasets (`qa/datasets/`)

This directory contains 5 dedicated synthetic datasets engineered specifically for black-box pre-submission acceptance testing of the ML Studio platform.

---

## Datasets Overview

### 1. `clean_housing_regression.csv`
- **Purpose**: Tier 0 happy-path regression testing (T0.2).
- **Rows**: 2,000 | **Columns**: 7 (6 features, 1 target).
- **Target**: `price` (Continuous numeric, strictly positive).
- **Features**: `sqft`, `bedrooms`, `bathrooms`, `location_score`, `year_built`, `garage_capacity`.
- **Characteristics**: Realistic linear/non-linear combinations with independent Gaussian noise. No artificial leakage. True $R^2 \approx 0.85 - 0.92$.

### 2. `clean_churn_classification.csv`
- **Purpose**: Tier 0 happy-path binary classification testing (T0.3).
- **Rows**: 2,000 | **Columns**: 7 (6 features, 1 target).
- **Target**: `churn` (Binary integer: `0` or `1`).
- **Features**: `tenure_months`, `monthly_spend`, `support_tickets`, `contract_type`, `paperless_billing`, `usage_gb`.
- **Characteristics**: Balanced customer churn scenario governed by realistic log-odds weights. Tests metric evaluation (Macro-F1, ROC-AUC), decision threshold freezing, and confusion matrix rendering.

### 3. `leaky_housing.csv`
- **Purpose**: Tier 1 data leakage detection testing (T1.1).
- **Rows**: 2,000 | **Columns**: 8 (7 features, 1 target).
- **Target**: `price`.
- **Injected Leak**: `price_bucket_proxy` $= \text{price} \times 0.98 + \mathcal{N}(0, 500)$.
- **Characteristics**: Pearson correlation $> 0.99$ with target. Verifies that the Diagnostics engine flags high correlation / suspicious target proxy with concrete evidence metrics.

### 4. `all_categorical_dqi.csv`
- **Purpose**: Tier 1 edge-case DQI normalization testing (T1.2).
- **Rows**: 250 | **Columns**: 4 (all categorical string variables).
- **Features**: `region`, `device`, `plan`, `satisfaction`.
- **Characteristics**: Contains zero numeric columns. Verifies that Data Quality Index (DQI) properly skips outlier prevalence calculation and dynamically renormalizes the remaining 3 sub-score weights to sum to 1.0 without crashing.

### 5. `ambiguous_task_type.csv`
- **Purpose**: Tier 1 edge-case task type resolution (T1.2).
- **Rows**: 300 | **Columns**: 3 (2 continuous features, 1 ambiguous target).
- **Target**: `rating_score` (Discrete integers 1–15, unique ratio 5%).
- **Characteristics**: Falls inside the ambiguous heuristic zone between discrete classification and continuous regression, testing user prompt confirmation without silent defaulting.
