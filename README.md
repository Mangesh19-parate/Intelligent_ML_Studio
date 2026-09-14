# Intelligent ML Studio 🔬⚡

> **A Leakage-Controlled, Reproducible Tabular ML Experimentation Platform with Immutable Lineage, Adversarial Verification, and Preregistered Research Benchmarks.**

[![Python](https://img.shields.io/badge/Python-3.11%20%7C%203.12%20%7C%203.13-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-green.svg)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-18.2-61dafb.svg)](https://react.dev/)
[![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2.0+-red.svg)](https://www.sqlalchemy.org/)
[![Tests](https://img.shields.io/badge/Tests-435%20Passed-brightgreen.svg)]()
[![Invariants](https://img.shields.io/badge/Invariants-100%25%20Verified-success.svg)]()

---

## 🎯 Executive Summary

In classical machine learning workflows, **subtle data leakage, evaluation reuse, and undocumented preprocessing drift** consistently inflate benchmark metrics while causing severe degradation in real-world deployment.

**Intelligent ML Studio** is a reproducible tabular ML experimentation platform engineered to eliminate leakage vectors by architectural construction. It features:
- **Strict Partition Isolation**: 80/20 train/test split with deterministic row hash verification; zero fitting on Locked Test data.
- **Fold-Isolated Preprocessing & Feature Selection**: Imputers, scalers, and selector rankings fit strictly inside training folds.
- **Durable Task Persistence & Crash Recovery**: DB-backed durable tasks with worker crash recovery, active timeout enforcement terminating execution, and zero zombie writes.
- **Immutable Snapshot Lineage & HMAC Artifact Signing**: Transformations and feature selections generate SHA-256 snapshotted pipelines; serialized model artifacts are cryptographically HMAC signed.
- **Four-Eyes Deployment Governance & Rollback**: Cryptographic model passports, server-side separation-of-duties (`approved_by != created_by`), and first-class one-click deployment rollback.
- **Preregistered Research Track**: Hierarchical statistical analysis ($Dataset \to Repeat \to Fold$) across 1,280 runs with complete $\alpha$ ablation and honest null result reporting.

---

## 🏗️ System Architecture & Deployment Topology

```text
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                        INTELLIGENT ML STUDIO RUNTIME TOPOLOGY                          │
└────────────────────────────────────────────────────────────────────────────────────────┘

                           React + Vite Web UI
                                    │ (REST / JSON / JWT)
                                    ▼
                           FastAPI API Gateway
                                    │
          ┌─────────────────────────┼─────────────────────────┐
          │ (SQLAlchemy ORM)        │ (Redis Queue)           │ (HMAC Signing)
          ▼                         ▼                         ▼
   PostgreSQL / SQLite      Redis Message Broker      Artifact Storage
   (ACID State Machines,    (Task Queuing &           (SHA-256 Checksums,
    Durable Task Records,    Worker Dispatch)          HMAC Signatures)
    Snapshots, Lineage)             │
                                    ▼
                          Celery / Task Worker
                         (CV Training Loops,
                          Active Timeouts,
                          Fold Invariants)
```

---

## 🛡️ Public Assurance Matrix

| System Guarantee / Invariant | Verification Test Suite | Architectural Enforcement | Status |
|:---|:---|:---|:---:|
| **Locked Test Zero Leakage** | `test_system_integrity.py`<br>`test_day4_leakage_and_reordering.py` | Holdout partition transformed via pre-fitted estimators; zero fitting on test folds | **VERIFIED** |
| **Fold-Safe Feature Selection** | `test_feature_selection_isolation.py` | Selector fitting, permutation importance, and row hashes asserted per-fold | **VERIFIED** |
| **Durable Task Crash Recovery** | `test_durable_tasks.py` | Task state persisted to DB; orphaned/running tasks recovered on worker restart | **VERIFIED** |
| **Active Timeout Enforcement** | `test_durable_tasks.py` | Worker processes terminated on timeout with zero zombie/post-timeout DB writes | **VERIFIED** |
| **HMAC Artifact Manifest Signing** | `test_p1_hardening.py` | Serialized models verified against HMAC signatures before unpickling/serving | **VERIFIED** |
| **Refresh Token Rotation & Reuse** | `test_p1_hardening.py` | Rotates refresh tokens on exchange; detects reuse as compromise and revokes family | **VERIFIED** |
| **First-Class Rollback** | `test_deployments_and_gates.py` | Retires current deployment and provisions restored model with full audit trail | **VERIFIED** |
| **Four-Eyes Governance** | `test_golden_path_e2e.py` | `approved_by != created_by` enforced server-side; HTTP 403 on self-approval | **VERIFIED** |
| **Golden-Path E2E Lifecycle** | `test_golden_path_e2e.py` | Full upload $\to$ DQI $\to$ FS $\to$ CV $\to$ Passport $\to$ Gate $\to$ Predict $\to$ Rollback | **VERIFIED** |
| **Strict Migration Upgrade/Downgrade** | `test_alembic_migrations.py` | Headless migration test verifying clean `upgrade head -> downgrade base -> upgrade head` | **VERIFIED** |

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
