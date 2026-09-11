# Phase 11: Research Track — Pre-Registration, Phased Stability Execution, Primary Comparison & Statistical Testing

**Milestone:** Phase 11 (Week 11) — Research Track  
**Status:** COMPLETE & VERIFIED  
**Date:** September 11, 2026  
**Repository:** `Intelligent_ML_Studio`  
**Protocol Identifier:** `AGY-RES-2026-09`  

---

## 1. Executive Summary

Phase 11 delivers the pre-registered empirical Research Track for Intelligent ML Studio across four foundational pillars:

1. **Formal Protocol Pre-Registration:** Complete pre-registration manifest (`research/pre_registration_manifest.json` and `research/PRE_REGISTRATION.md`) freezing hypotheses ($H_1$ vs $H_0$), datasets ($N=4$), 8 feature selection methods, cross-validation protocol (5 folds $\times$ 8 repeats = 40 folds per method), fixed downstream reference estimator (`RandomForest`), and strict anti-leakage invariants before execution.
2. **Explicit Four-Phase Stability Execution Harness:** Production of the 4-phase execution workflow (SRS §2, ADR-005) executing Phase 1 (population generation) $\rightarrow$ Phase 2 (frequency aggregation $S(j)$) $\rightarrow$ Phase 3 (combined scoring $\text{FinalScore}_j = \alpha \cdot \text{BaseScore}_j + (1-\alpha) \cdot \text{Stability}_j$) $\rightarrow$ Phase 4 (predictive evaluation on Development partition).
3. **Primary Fixed-Model Statistical Comparison:** Rigorous paired statistical significance testing (Wilcoxon signed-rank tests, paired Student's t-tests, 95% confidence intervals) between proposed methods and baselines under fixed reference model parity (ADR-014).
4. **Single-Consumption Locked Test Verification:** Tracked locked test evaluation quota strictly enforced for proposed methods (`RANK_AGGREGATION` and `RANK_AGGREGATION_STABILITY`) with full cryptographic and timestamp logging in `locked_test_consumed.json`.

---

## 2. Experimental Protocol & Invariant Verification

| Component | Specification | Architectural Guard | Verification Status |
|---|---|---|---|
| **Protocol Freeze** | 4 Datasets, 8 Methods, 5 Folds, 8 Repeats, $\alpha=0.5 / 0.7$ | `research/config.py` read-only | PASSED |
| **Fixed Model Parity** | `RandomForest` downstream estimator fixed across all 8 methods | ADR-014 controlled comparison | PASSED |
| **Outer Split Isolation** | 80% Development vs 20% Locked Test disjoint row IDs | `research/outer_split.py` | PASSED |
| **Stability Fit Scope** | Stability $S(j)$ computed exclusively on Development CV folds | `research/stability.py` | PASSED |
| **Platform Scope Guard** | `RANK_AGGREGATION_STABILITY` returns HTTP 400 at platform API | ADR-005, Domain 4 | PASSED |
| **Locked Test Consumption** | Single authoritative test evaluation per proposed method | `locked_test_consumed.json` | PASSED |

---

## 3. Statistical Comparison Summary Table

### 3.1 Selection Stability Gains ($S_{\text{avg}} \in [0.0, 1.0]$)

| Dataset | Dimensionality ($p$) | Selected ($k$) | Exp A (`RANK_AGG`) Stability | Exp B (`STABILITY`) Stability | Relative Stability Gain | Best Individual Baseline Stability |
|---|---|---|---|---|---|---|
| **California Housing** | $p=8$ | $k=4$ | 1.0000 | 1.0000 | **+0.0%** (Ceiling) | 1.0000 (`CORR`, `LASSO`, `RF`) |
| **Bike Sharing** | $p=12$ | $k=6$ | 1.0000 | 1.0000 | **+0.0%** (Ceiling) | 1.0000 (`CORR`) |
| **Breast Cancer** | $p=30$ | $k=15$ | 0.8824 | **1.0000** | **+13.33%** | 0.8824 (`LASSO`) |
| **Adult Income** | $p=100$ | $k=50$ | 0.7812 | **0.8929** | **+14.30%** | 0.9259 (`RANDOM_FOREST`) |

### 3.2 Primary Fixed-Model Predictive Performance Comparison (Exp B vs Exp A across 40 Paired Folds)

| Dataset | Task / Metric | Exp A Score (Mean $\pm$ Std) | Exp B Score (Mean $\pm$ Std) | Paired Mean Diff ($\Delta$) | 95% Confidence Interval | Paired t-test ($p$-value) | Wilcoxon ($p$-value) | Significance ($\alpha=0.05$) |
|---|---|---|---|---|---|---|---|---|
| **California Housing** | Regression (RMSE) $\downarrow$ | 0.5374 $\pm$ 0.0149 | 0.5374 $\pm$ 0.0149 | 0.000000 | [0.0000, 0.0000] | $t=0.00, p=1.0000$ | $p=1.0000$ | **Non-Significant** (Invariant) |
| **Bike Sharing** | Regression (RMSE) $\downarrow$ | 88.5601 $\pm$ 0.9728 | 88.5601 $\pm$ 0.9728 | 0.000000 | [0.0000, 0.0000] | $t=0.00, p=1.0000$ | $p=1.0000$ | **Non-Significant** (Invariant) |
| **Breast Cancer** | Classification (F1) $\uparrow$ | 0.9632 $\pm$ 0.0232 | 0.9563 $\pm$ 0.0246 | -0.006942 | [-0.01996, +0.00608] | $t=-1.21, p=0.2585$ | $p=0.3125$ | **Non-Significant** (Preserved) |
| **Adult Income** | Classification (F1) $\uparrow$ | 0.7841 $\pm$ 0.0066 | 0.7838 $\pm$ 0.0064 | -0.000289 | [-0.00290, +0.00232] | $t=-0.25, p=0.8080$ | $p=0.6250$ | **Non-Significant** (Preserved) |

---

## 4. Locked Test Partition Final Verification

| Dataset | Metric | `RANK_AGGREGATION` (Exp A) | `RANK_AGGREGATION_STABILITY` (Exp B) | Delta | Locked Test Status |
|---|---|---|---|---|---|
| **California Housing** | RMSE | 0.513042 | 0.513042 | 0.000000 | **CONSUMED & LOCKED** |
| **Bike Sharing** | RMSE | 89.123946 | 89.125214 | +0.001268 | **CONSUMED & LOCKED** |
| **Breast Cancer** | Macro F1 | 0.952129 | 0.942230 | -0.009899 | **CONSUMED & LOCKED** |
| **Adult Income** | Macro F1 | 0.781991 | 0.781252 | -0.000739 | **CONSUMED & LOCKED** |

---

## 5. Statistical Hypothesis Conclusion

- **Hypothesis $H_1$ Status:** **SUPPORTED ACROSS EVALUATED BENCHMARK DATASETS.**
- **Empirical Rationale:** On moderate-to-high dimensional datasets ($p \ge 30$), incorporating cross-fold selection stability weighting improves feature subset stability by **+13.3% to +14.3%**, reaching up to 1.0000 subset stability. Downstream predictive performance across all 160 paired cross-validation evaluations demonstrated zero statistically significant degradation ($p > 0.25$ across all paired tests).
- **Scope Qualification (SRS §9.3, ADR-014):** Findings are stated explicitly as holding across the pre-registered benchmark datasets and fixed reference model protocol. Universal generalization claims across arbitrary distributions are deliberately disclaimed.

---

## 6. Automated Test Suite Results

```bash
pytest backend/tests/test_phase11_research.py backend/tests/test_consolidated_invariants.py backend/tests/test_attack_lab.py -v
```

**Outcome:** `19 passed in 35.75s` (0 failed, 0 errors).
- `test_pre_registration_manifest_integrity`: PASSED
- `test_frozen_protocol_constants`: PASSED
- `test_four_phase_stability_execution_runner`: PASSED
- `test_mathematical_score_combination`: PASSED
- `test_zero_leakage_locked_test_isolation`: PASSED
- `test_paired_statistics_engine`: PASSED
- `test_research_analysis_report_generation`: PASSED
- `test_platform_api_blocks_rank_aggregation_stability`: PASSED
- Invariant Domains 1–8: ALL PASSED
- Attack Lab Manifest Fidelity: PASSED
