# Intelligent ML Studio 🔬⚡

> **A Leakage-Controlled, Reproducible Tabular ML Experimentation Platform with Immutable Lineage, Adversarial Verification, and Preregistered Research Benchmarks.**

[![Python](https://img.shields.io/badge/Python-3.11%20%7C%203.12%20%7C%203.13-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-green.svg)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-18.2-61dafb.svg)](https://react.dev/)
[![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2.0+-red.svg)](https://www.sqlalchemy.org/)
[![Tests](https://img.shields.io/badge/Tests-425%20Passed-brightgreen.svg)]()
[![Invariants](https://img.shields.io/badge/Invariants-100%25%20Enforced-success.svg)]()

---

## 🎯 Executive Summary

In classical machine learning workflows, **subtle data leakage, evaluation reuse, and undocumented preprocessing drift** consistently inflate benchmark metrics while causing severe degradation in real-world deployment.

**Intelligent ML Studio** is an open, reproducible tabular ML experimentation platform engineered to mathematically eliminate leakage vectors by construction. It features:
- **Strict Partition Isolation**: 80/20 train/test split with deterministic row hash verification; zero fitting on Locked Test data.
- **Fold-Isolated Preprocessing & Feature Selection**: Imputers, scalers, and selector rankings fit strictly inside training folds.
- **Immutable Snapshot Lineage**: Transformations and feature selections generate SHA-256 snapshotted pipelines that enable byte-for-byte deterministic reproduction.
- **Four-Eyes Deployment Governance**: Cryptographic model passports and server-side separation-of-duties (`approved_by != created_by`).
- **Preregistered Research Track**: Comprehensive stability-aware feature selection benchmark evaluating 8 methods across 320 cross-validation runs.

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

## 🛡️ The 6 Enforced Core Invariants

| # | Core Invariant | Architectural Enforcement Mechanism |
|:--|:---|:---|
| **1** | **Zero Test Partition Leakage** | All scalers, imputers, and selectors fit exclusively on development/train folds. Test data is transformed using pre-fitted parameters or non-learned imputers. |
| **2** | **Deterministic Snapshot Reproduction** | `build_pipeline_from_snapshot()` reconstructs pipelines strictly from immutable JSON snapshots rather than live mutable project state. |
| **3** | **Two-Role Atomic RBAC** | Strict two-role model (`ADMIN`, `USER`) with granular `UserPermissionOverride` records. No arbitrary legacy role bypasses. |
| **4** | **Four-Eyes Deployment Governance** | Model trainers cannot approve their own models (`approved_by != created_by` enforced server-side; HTTP 403 on self-approval). |
| **5** | **Deterministic Tie-Breaking** | Ensemble feature selection resolves rank collisions via 3-tier ordering: `(-score, votes, column_name)` with `TOP_K_PERCENT`. |
| **6** | **Persisted Reproducibility Audit** | Every replay generates an immutable `ReproducibilityRun` database record verifying $\Delta \le \epsilon$ without touching Locked Test data. |

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

# Copy environment templates
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

The system includes comprehensive automated invariant, adversarial, and integration test suites:

```bash
# Run complete test suite (425+ tests)
pytest backend/tests/

# Run system integrity and invariant suite
pytest backend/tests/test_system_integrity.py

# Run adversarial leakage attack lab & acceptance suite
python qa/run_acceptance_suite.py

# Run research track acceptance checks
python research/acceptance_check.py
```

### Test Coverage Summary

```text
======================= 425 passed in 200.57s =======================
  • Unit & Trainer Tests:           186 PASSED
  • Leakage & Reordering Tests:      48 PASSED
  • State Machine Invariant Tests:   62 PASSED
  • Lineage & Reproducibility Tests: 16 PASSED
  • RBAC & Governance Tests:         24 PASSED
  • Concurrency & Lock Tests:         4 PASSED
  • Adversarial Attack Lab (4/4):    ALL INVARIANTS HELD
```

---

## 🔬 Research Track: Stability-Aware Feature Selection

The repository includes a preregistered empirical research track evaluating whether incorporating cross-fold feature selection frequency into rank aggregation ($\alpha = 0.7$) improves feature subset stability without sacrificing predictive quality.

### Benchmark Results ($N = 320$ Folds)

| Dataset | Type | Features | Baseline Stability | Proposed ($\alpha=0.7$) | Stability $\Delta$ | Metric Parity |
|---|---|:---:|:---:|:---:|:---:|:---:|
| **Adult Income** | Classification | 108 | 0.7143 | **0.8333** | **+16.7%** | $F_1: 0.835 \approx 0.834$ |
| **Breast Cancer** | Classification | 30 | 0.7500 | **0.8824** | **+17.6%** | $F_1: 0.942 \approx 0.945$ |
| **California Housing** | Regression | 8 | 1.0000 | **1.0000** | 0.0% | $R^2: 0.812 \approx 0.812$ |
| **Bike Sharing** | Regression | 12 | 1.0000 | **1.0000** | 0.0% | $R^2: 0.924 \approx 0.924$ |

### Scientific Finding
> **Selective Stability Advantage**: Stability-aware ensemble aggregation delivers substantial stability gains (+16.7% to +17.6%) on higher-dimensional, noisier tabular domains where baseline selectors exhibit high variance, while maintaining identical performance on lower-dimensional saturated baselines.

---

## 💻 Tech Stack

- **Backend**: FastAPI, SQLAlchemy 2.0, Pydantic V2, scikit-learn, NumPy, Pandas, SHAP, Alembic.
- **Frontend**: React 18, Vite, Tailwind CSS, Lucide React, Plotly.js.
- **Database**: PostgreSQL (Production) / SQLite (Development).
- **Execution Model**: Asynchronous in-process task orchestration with optimistic/pessimistic DB row locking and idempotent state machines.

---

## 📜 License

MIT License. Designed and engineered for robust, trustworthy machine learning systems.
