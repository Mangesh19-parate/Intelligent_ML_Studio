# Research Track: Formal Pre-Registration Document (SRS §9)

**Protocol Registration Date:** September 11, 2026  
**Status:** FROZEN & PRE-REGISTERED (Read-Only)  
**Study Identifier:** `AGY-RES-2026-09`  
**Platform Separation:** Per ADR-005, ADR-014, and NFR-10, this research track is formally isolated from the platform application layer.

---

## 1. Research Questions & Hypotheses

### Primary Research Question
Does combining ensemble rank aggregation with cross-fold selection stability improve feature subset robustness without compromising downstream predictive accuracy under a fixed reference model?

### Hypotheses
- **Alternative Hypothesis ($H_1$):** Rank aggregation combined with selection stability produces more stable feature subsets than individual feature-selection methods and plain rank aggregation, while maintaining comparable downstream predictive performance under a fixed reference model.
- **Null Hypothesis ($H_0$):** Rank aggregation combined with selection stability does not produce a meaningful improvement in feature selection stability without unacceptable predictive-performance degradation.

---

## 2. Experimental Datasets ($N=4$)

Four diverse tabular benchmark datasets spanning continuous regression and classification with variable dimensionality:

1. **California Housing (Regression):** 8 features ($p=8, k=4$), target = median house value, metric = RMSE.
2. **Bike Sharing (Regression):** 12 features ($p=12, k=6$), target = hourly rental count, metric = RMSE.
3. **Breast Cancer Wisconsin (Classification):** 30 features ($p=30, k=15$), target = diagnosis, metric = Macro F1.
4. **Adult Census Income (Classification):** 100 one-hot encoded features ($p=100, k=50$), target = income bracket, metric = Macro F1.

---

## 3. Evaluated Methods

Eight feature selection methods evaluated under identical cross-validation splits:
- **Reference Baseline:** `NO_SELECTION` (100% of features).
- **Univariate Filter Baseline:** `CORRELATION` (Pearson correlation / ANOVA F-value).
- **Embedded Baseline:** `LASSO` (L1-regularized linear/logistic regression).
- **Embedded Impurity Baseline:** `RANDOM_FOREST` (Mean Decrease in Impurity).
- **Model-Agnostic Baseline:** `PERMUTATION` (Validation fold feature permutation).
- **Wrapper Baseline:** `RFE` (Recursive Feature Elimination).
- **Proposed Experiment A:** `RANK_AGGREGATION` (Ensemble combining 4 core selectors).
- **Proposed Experiment B:** `RANK_AGGREGATION_STABILITY` (Ensemble + cross-fold selection stability weighting, $\alpha=0.7 / 0.5$).

---

## 4. Controlled Parity Protocol (ADR-014)

1. **Downstream Reference Estimator:** Fixed to `RandomForest` ($n=50$, max_depth=10) across all 8 methods to isolate the feature selection effect from model-selection variance.
2. **Repeated Cross-Validation:** 5-Fold Cross-Validation $\times$ 8 Repeats ($seeds = 1000 \dots 1007$) = 40 folds per method (320 runs per dataset, 1,280 total CV evaluations).
3. **Anti-Leakage Controls:**
   - Strict 80/20 outer split into Development and Locked Test partitions with disjoint `row_uid`s before any fitting.
   - Transformers and feature selectors fit strictly inside training folds.
   - Stability scores $S(j)$ computed exclusively on the Development partition across repeated folds.
   - Locked Test evaluated at most once per proposed method (`RANK_AGGREGATION` and `RANK_AGGREGATION_STABILITY`) and never by baselines.

---

## 5. Statistical Testing Protocol

- **Paired Differences:** Evaluated per dataset across the 40 paired folds ($\Delta = \text{Score}_B - \text{Score}_A$).
- **Significance Tests:** Two-tailed Wilcoxon signed-rank test and paired Student's t-test with $\alpha=0.05$.
- **Effect Bounds:** 95% Confidence Intervals for mean and median differences.
- **Reporting Standard:** Results reported honestly as *"across the evaluated benchmark datasets"*.
