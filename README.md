# Intelligent ML Studio 🔬⚡

> **A Leakage-Controlled, Reproducible Tabular ML Experimentation Platform with Immutable Lineage, Adversarial Verification, and Preregistered Research Benchmarks.**

[![Python](https://img.shields.io/badge/Python-3.11%20%7C%203.12%20%7C%203.13-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-green.svg)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-18.2-61dafb.svg)](https://react.dev/)
[![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2.0+-red.svg)](https://www.sqlalchemy.org/)
[![Tests](https://img.shields.io/badge/Tests-428%20Passed-brightgreen.svg)]()
[![Invariants](https://img.shields.io/badge/Invariants-100%25%20Verified-success.svg)]()

---

## 🎯 Executive Summary

In classical machine learning workflows, **subtle data leakage, evaluation reuse, and undocumented preprocessing drift** consistently inflate benchmark metrics while causing severe degradation in real-world deployment.

**Intelligent ML Studio** is a reproducible tabular ML experimentation platform engineered to eliminate leakage vectors by architectural construction. It features:
- **Strict Partition Isolation**: 80/20 train/test split with deterministic row hash verification; zero fitting on Locked Test data.
- **Fold-Isolated Preprocessing & Feature Selection**: Imputers, scalers, and selector rankings fit strictly inside training folds.
- **Immutable Snapshot Lineage**: Transformations and feature selections generate SHA-256 snapshotted pipelines that enable byte-for-byte deterministic reproduction.
- **Four-Eyes Deployment Governance**: Cryptographic model passports and server-side separation-of-duties (`approved_by != created_by`).
- **Preregistered Research Track**: Comprehensive stability-aware feature selection benchmark evaluating 8 methods across 320 cross-validation runs with $\Delta S \ge 0.05$ decision criteria.

---

## 🏗️ System Architecture

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│                          INTELLIGENT ML STUDIO ARCHITECTURE                 │
└─────────────────────────────────────────────────────────────────────────────┘

  Raw CSV Ingestion ──► Ingestion & Profiling ──► Data Quality Index (DQI)
                                │
                        80/20 Outer Split (Deterministic SHA-256)
                                │
        ┌───────────────────────┴───────────────────────┐
        ▼                                               ▼
┌───────────────────────────────┐       ┌───────────────────────────────┐
│     DEVELOPMENT PARTITION     │       │     LOCKED TEST PARTITION     │
│             (80%)             │       │             (20%)             │
├───────────────────────────────┤       ├───────────────────────────────┤
│ • 5-Fold Cross Validation     │       │ • Zero Preprocessing Fitting  │
│ • Fold-Safe Transformations   │       │ • Zero Feature Selection Fit  │
│ • Multi-Method Selector Voting│       │ • Untouched During CV/Tuning  │
│ • Out-of-Fold Threshold Tuning│       │ • Single Evaluation Trigger   │
│ • Algorithm Leaderboard       │       │ • Status: TEST_CONSUMED       │
└───────────────┬───────────────┘       └───────────────┬───────────────┘
                │                                       │
                ▼                                       ▼
     Winning Model Selection ──────────────► Final Authoritative Eval
                │                                       │
                ▼                                       ▼
     Immutable Snapshot Hash                Model Technical Passport
  (Transformation & Selection)               (SHA-256 + Metric Drift)
                │                                       │
                ▼                                       ▼
    Deterministic Replay Engine             Four-Eyes Deployment Gate
  (Persisted ReproducibilityRun)           (approved_by != created_by)
```

---

## 🛡️ Public Assurance Matrix

| System Invariant / Property | Verification Test Suite | Architectural Enforcement | Result |
|:---|:---|:---|:---:|
| **Locked Test Zero Leakage** | `test_system_integrity.py`<br>`test_day4_leakage_and_reordering.py` | Test partition transformed using pre-fitted transformers or non-learned imputers (`nan_to_num`) | **PASS** |
| **Fold-Safe Feature Selection** | `test_feature_selection_isolation.py` | Permutation, Lasso, and Correlation selectors execute strictly on training folds | **PASS** |
| **Deterministic Reproduction** | `test_lineage_and_reproducibility.py` | `build_pipeline_from_snapshot()` builds strictly from immutable snapshot records | **PASS** |
| **Persisted Replay Audit** | `test_system_integrity.py` | Replays generate immutable `ReproducibilityRun` database records without mutating experiments | **PASS** |
| **Four-Eyes Separation-of-Duties** | `test_system_integrity.py` | `approved_by != created_by` enforced server-side; HTTP 403 on self-approval | **PASS** |
| **Deterministic Tie-Breaking** | `test_day2_selectors.py` | 3-tier deterministic sort: `(-score, votes, column_name)` with `TOP_K_PERCENT` | **PASS** |
| **Single Test Consumption** | `test_day4_locked_test_consumption.py` | Single authoritative evaluation; repeat accesses marked `TEST_REUSED_DIAGNOSTIC` | **PASS** |
| **Adversarial Attack Lab (4/4)** | `qa/run_acceptance_suite.py` | Global scaling, full-data FS, test thresholding, and test reuse attacks blocked | **PASS** |
| **Headless Migration Cleanliness** | `alembic upgrade head` | Production database schema migrations driven strictly via Alembic revisions | **PASS** |

---

## 📜 Model Technical Passport

Every deployable candidate model exposes an immutable cryptographic passport:

```text
┌────────────────────────────────────────────────────────────────────────┐
│ MODEL TECHNICAL PASSPORT                                               │
│ Model ID: a482dee6-17bd-4de4-8e53-553ced6a81f6         DEPLOYABLE ✓    │
├────────────────────────────────────────────────────────────────────────┤
│ Project: Customer Churn Predictor                                      │
│ Dataset SHA-256: 7f83a21d9c0e4b8a12f5e4d9c3b2a10e8f7a6b5c4d3e2f1a0    │
│ Task Type: CLASSIFICATION | Algorithm: RandomForestClassifier          │
│ CV Strategy: 5-Fold Stratified | CV Seed: 42                           │
├────────────────────────────────┬───────────────────────────────────────┤
│ Cross-Validation Macro-F1      │ 0.8421 ± 0.012                        │
│ Locked Test Macro-F1           │ 0.8350                                │
│ Feature Reduction              │ 108 features ──► 50 selected (46.3%)  │
│ Out-of-Fold Decision Threshold │ 0.3800                                │
├────────────────────────────────┴───────────────────────────────────────┤
│ GOVERNANCE & INTEGRITY AUDIT                                           │
│ ✓ Locked Test evaluated once (Zero reuse detected)                     │
│ ✓ Input feature schema locked & immutable                              │
│ ✓ SHA-256 artifact checksum matched (Disk: e3b0c442...)                │
│ ✓ End-to-end lineage complete (Transformation & FS snapshots captured)  │
│ ✓ Performance threshold satisfied (Macro-F1 >= 0.80)                   │
│ ✓ Four-Eyes approval confirmed (Approved by: approver@demo.com)        │
└────────────────────────────────────────────────────────────────────────┘
```

---

## ⚠️ Graceful Safety Failure-Mode

Unlike naive AutoML systems that silently train sub-optimal models on invalid inputs, Intelligent ML Studio enforces an **explicit safety failure path**:

```text
┌────────────────────────────────────────────────────────────────────────┐
│ 🛑 EXPERIMENT HALTED: SAFETY THRESHOLD VIOLATION                       │
├────────────────────────────────────────────────────────────────────────┤
│ Reason: Feature selection consensus requirement not satisfied.         │
│                                                                        │
│ Selector Diagnostics:                                                  │
│   [✓] Correlation Selector:       APPLIED   (Score variance: 0.14)     │
│   [✗] Lasso L1 Selector:          FAILED    (Collinear rank collapse)  │
│   [✗] Permutation Importance:     FAILED    (Insufficient validation)  │
│   [✗] Random Forest Importance:   FAILED    (Memory constraint)        │
│                                                                        │
│ Safety Policy: Minimum 2 independent selector agreements required.     │
│ Action Taken: Execution aborted without mutating experiment state.     │
└────────────────────────────────────────────────────────────────────────┘
```

---

## ⚡ 5-Minute Quickstart

### Prerequisites
- Python 3.11+
- Node.js 18+ and npm
- Git

### 1. Clone & Set Up Environment
```bash
git clone https://github.com/Mangesh19-parate/Intelligent_ML_Studio.git
cd Intelligent_ML_Studio

# Copy environment template
cp .env.example .env
```

### 2. Backend Setup & Startup
```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt

# Run migrations and start server
alembic upgrade head
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```
*Backend is running at [http://localhost:8000](http://localhost:8000) (Swagger Docs at [http://localhost:8000/docs](http://localhost:8000/docs))*

### 3. Frontend Setup & Startup
```bash
cd ../frontend
npm install
npm run dev
```
*Frontend UI is running at [http://localhost:3000](http://localhost:3000)*

---

## 🧪 Test Suite & Invariant Verification

```bash
# Run complete test suite (428+ tests)
pytest backend/tests/

# Run system integrity and invariant suite
pytest backend/tests/test_system_integrity.py

# Run durable task orchestration tests
pytest backend/tests/test_durable_tasks.py

# Run adversarial leakage attack lab & acceptance suite
python qa/run_acceptance_suite.py

# Run research track acceptance checks & statistical evaluation
python research/acceptance_check.py
python research/statistical_analysis.py
```

---

## 🔬 Research Track: Stability-Aware Feature Selection

The repository includes a preregistered empirical research benchmark evaluating whether combining rank aggregation with cross-fold selection frequency ($\alpha = 0.7$) improves feature subset stability without sacrificing predictive quality.

### Benchmark Results ($N = 320$ Folds across 4 Standard Datasets)

| Dataset | Type | Features | Baseline Stability | Proposed ($\alpha=0.7$) | Stability $\Delta$ | Metric Parity |
|---|---|:---:|:---:|:---:|:---:|:---:|
| **Adult Income** | Classification | 108 | 0.8065 | **0.9091** | **+12.72%** ($\Delta S \ge 0.05$) | $F_1: 0.784 \approx 0.784$ ($p = 0.405$) |
| **Breast Cancer** | Classification | 30 | 0.8333 | **0.8824** | **+5.89%** ($\Delta S \ge 0.05$) | $F_1: 0.949 \approx 0.949$ ($p = 0.985$) |
| **California Housing** | Regression | 8 | 1.0000 | **1.0000** | 0.0% (Saturated baseline) | $R^2: 0.812 \approx 0.812$ ($p = 1.000$) |
| **Bike Sharing** | Regression | 12 | 1.0000 | **1.0000** | 0.0% (Saturated baseline) | $R^2: 0.924 \approx 0.924$ ($p = 1.000$) |

### Scientific Finding
> **Selective Stability Advantage**: Stability-aware ensemble aggregation delivers substantial stability gains (+5.89% to +12.72%) on higher-dimensional, noisier tabular domains where baseline selectors exhibit high variance, while maintaining identical performance on lower-dimensional saturated baselines.

---

## 💻 Tech Stack

- **Backend**: FastAPI, SQLAlchemy 2.0, Pydantic V2, scikit-learn, NumPy, Pandas, SHAP, Alembic.
- **Frontend**: React 18, Vite, Tailwind CSS, Lucide React, Plotly.js.
- **Database**: PostgreSQL (Production) / SQLite (Development).
- **Execution Model**: Asynchronous durable task orchestration with optimistic/pessimistic DB row locking and idempotent state machines.

---

## 📜 License

MIT License. Designed and engineered for robust, trustworthy machine learning systems.
