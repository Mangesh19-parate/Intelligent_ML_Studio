# Intelligent ML Studio 🔬⚡

> **A Leakage-Controlled, Reproducible Tabular ML Experimentation Platform with Immutable Lineage, Adversarial Verification, and Preregistered Research Benchmarks.**

[![Python](https://img.shields.io/badge/Python-3.11%20%7C%203.12%20%7C%203.13-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-green.svg)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-18.2-61dafb.svg)](https://react.dev/)
[![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2.0+-red.svg)](https://www.sqlalchemy.org/)
[![Tests](https://img.shields.io/badge/Tests-460%2B%20Passed-brightgreen.svg)]()
[![Invariants](https://img.shields.io/badge/Invariants-100%25%20Verified-success.svg)]()

---

## 🎯 Executive Summary

In classical machine learning workflows, **subtle data leakage, evaluation reuse, and undocumented preprocessing drift** consistently inflate benchmark metrics while causing severe degradation in real-world deployment.

**Intelligent ML Studio** is a reproducible tabular ML experimentation platform engineered to eliminate leakage vectors by architectural construction. It features:
- **Strict Partition Isolation**: 80/20 train/test split with deterministic row hash verification; zero fitting on Locked Test data.
- **Fold-Isolated Preprocessing & Feature Selection**: Imputers, scalers, and selector rankings fit strictly inside training folds.
- **DB-Backed Task Queue & Dedicated Worker**: API enqueues tasks exclusively to the `durable_tasks` table; dedicated worker daemon claims tasks via `FOR UPDATE SKIP LOCKED`, executes under OS process isolation, enforces hard timeout termination, and performs lease-based stale-task recovery.
- **Atomic Multi-Worker Claiming**: PostgreSQL `FOR UPDATE SKIP LOCKED` atomic task claiming preventing worker race conditions across concurrent daemons.
- **Immutable Snapshot Lineage & HMAC Artifact Signing**: Transformations and feature selections generate SHA-256 snapshotted pipelines; serialized model artifacts are cryptographically HMAC signed.
- **Four-Eyes Deployment Governance & Rollback**: Cryptographic model passports, server-side separation-of-duties (`approved_by != created_by`), and first-class one-click deployment rollback.
- **Preregistered Research Track**: Hierarchical statistical analysis across benchmark datasets with strict nested cross-validation alpha sensitivity analysis and honest boundary condition characterization.

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
          │ (SQLAlchemy ORM)        │ (PostgreSQL Queue)      │ (HMAC Signing)
          ▼                         ▼                         ▼
   PostgreSQL / SQLite       durable_tasks Table       Artifact Storage
   (ACID State Machines,    (Atomic Claiming with     (SHA-256 Checksums,
    Snapshots, Lineage)       FOR UPDATE SKIP LOCKED)   HMAC Signatures)
                                    │
                                    ▼
                         Dedicated ML Task Worker
                        (OS Process-Isolated Execution,
                         Hard Timeout Termination,
                         Lease Requeue & Crash Recovery)
```

---

## 🛡️ Public Assurance Matrix

| System Guarantee / Invariant | Verification Test Suite | Architectural Enforcement | Status |
|:---|:---|:---|:---:|
| **Locked Test Zero Leakage** | `test_system_integrity.py`<br>`test_day4_leakage_and_reordering.py` | Holdout partition transformed via pre-fitted estimators; zero fitting on test folds | **VERIFIED** |
| **Fold-Safe Feature Selection** | `test_feature_selection_isolation.py` | Selector fitting, permutation importance, and row hashes asserted per-fold | **VERIFIED** |
| **Durable Task Crash Recovery** | `test_durable_tasks.py`<br>`test_chaos_and_resilience.py` | Task state persisted to DB; orphaned/running tasks recovered on worker restart with retry limits | **VERIFIED** |
| **Active Timeout Enforcement** | `test_durable_tasks.py`<br>`test_chaos_and_resilience.py` | Worker processes hard-terminated at OS process boundary on timeout with zero zombie writes | **VERIFIED** |
| **Atomic Multi-Worker Queue** | `test_durable_tasks.py`<br>`test_chaos_and_resilience.py` | `FOR UPDATE SKIP LOCKED` query prevents duplicate claims under high concurrency | **VERIFIED** |
| **HMAC Artifact Manifest Signing** | `test_p1_hardening.py` | Serialized models verified against HMAC signatures before unpickling/serving | **VERIFIED** |
| **Refresh Token Rotation & Reuse** | `test_p1_hardening.py` | Rotates refresh tokens on exchange; detects reuse as compromise and revokes family | **VERIFIED** |
| **First-Class Rollback** | `test_deployments_and_gates.py` | Retires current deployment and provisions restored model with full audit trail | **VERIFIED** |
| **Four-Eyes Governance** | `test_golden_path_e2e.py` | `approved_by != created_by` enforced server-side; HTTP 403 on self-approval | **VERIFIED** |
| **Golden-Path E2E Lifecycle** | `test_golden_path_e2e.py` | Full upload -> DQI -> FS -> CV -> Passport -> Gate -> Predict -> Rollback | **VERIFIED** |
| **Strict Migration Upgrade/Downgrade** | `test_alembic_migrations.py` | Headless migration test verifying clean upgrade head -> downgrade base -> upgrade head | **VERIFIED** |

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

## 🚀 Quick Start

### 1. Run with Docker Compose
```bash
docker compose up --build -d
```
Access the application:
- **Frontend Dashboard**: http://localhost:3000
- **Backend Swagger API**: http://localhost:8000/docs

### 2. Local Development Setup
```bash
# Backend & Worker
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
python -m uvicorn app.main:app --port 8000 --reload
python -m app.tasks.worker

# Frontend
cd frontend
npm install
npm run dev
```

### 3. Running Verification Tests
```bash
pytest backend/tests
```
