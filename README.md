# Intelligent ML Studio 🔬⚡

> **A Leakage-Aware Tabular ML Experimentation & Governance Platform**
> 
> *Manages the complete lifecycle from dataset profiling and leakage-safe feature selection to reproducible model training, model passports, four-eyes governance, and controlled production deployment.*

[![Python](https://img.shields.io/badge/Python-3.11%20%7C%203.12%20%7C%203.13-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-green.svg)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-18.2-61dafb.svg)](https://react.dev/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.0+-3178c6.svg)](https://www.typescriptlang.org/)
[![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2.0+-red.svg)](https://www.sqlalchemy.org/)
[![Tests](https://img.shields.io/badge/Automated%20Tests-467%20Passed-brightgreen.svg)]()
[![Typecheck](https://img.shields.io/badge/TypeScript%20Typecheck-0%20Errors-success.svg)]()

---

## 🎯 What is Intelligent ML Studio?

In tabular machine learning, subtle data leakage, undocumented transformation drift, and untested holdout reuse consistently inflate offline metrics while causing silent failures upon deployment.

**Intelligent ML Studio** eliminates these failure modes by architectural enforcement:
1. **Dataset Profiling & Quality Inspection**: Ingest tabular data (CSV) and automatically compute statistical summaries, missingness distributions, cardinality, and data quality indices.
2. **Immutable Partition Isolation**: Deterministic 80/20 train/holdout splitting with row hash verification. Model training and preprocessing estimators never fit on locked holdout data.
3. **Fold-Isolated Feature Engineering**: Imputation, scaling, encoding, and ranking-based feature selection run strictly within cross-validation training folds.
4. **Canonical Multi-Algorithm Tournament**: Train and benchmark a curated 6-algorithm catalog (Linear Regression, Random Forest Regressor, Gradient Boosting Regressor, Logistic Regression, Random Forest Classifier, Gradient Boosting Classifier) across cross-validation folds with standardized metric tracking.
5. **Cryptographic Model Passports**: Generate tamper-evident technical passports recording exact dataset hashes, hyperparameter manifests, fold metrics, and SHA-256 artifact checksums.
6. **Four-Eyes Governance & Deployment**: Enforce server-side separation-of-duties (`approved_by != created_by`) before models can be promoted to production endpoints.
7. **Production Serving & Instant Rollback**: Serve live inference endpoints with structured input validation and one-click deployment rollbacks.

---

## 🏗️ Architecture & Component Topology

```text
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                        INTELLIGENT ML STUDIO ARCHITECTURE                              │
└────────────────────────────────────────────────────────────────────────────────────────┘

                           React 18 + Vite Web UI
                                     │ (REST / JSON / JWT)
                                     ▼
                        FastAPI Modular API Monolith
                                     │
           ┌─────────────────────────┼─────────────────────────┐
           │ (SQLAlchemy ORM)        │ (Task Queue Table)      │ (HMAC Signing)
           ▼                         ▼                         ▼
    PostgreSQL / SQLite       durable_tasks Table       Artifact Storage
    (ACID State Machines,    (FOR UPDATE SKIP LOCKED   (SHA-256 Checksums,
     Snapshots, Lineage)       on PostgreSQL)            HMAC Signatures)
                                     │
                                     ▼
                          Dedicated ML Task Worker
                         (OS Process-Isolated Execution,
                          Hard Timeout Termination,
                          Lease Requeue & Recovery)
```

---

## 📊 Technical Capabilities & Implementation Status

To ensure complete transparency, every architectural capability is documented according to its shipped implementation status:

| Capability Area | Shipped Implementation | Architectural Scope | Status |
|:---|:---|:---|:---:|
| **Holdout Leakage Prevention** | Zero-fitting on holdout test partition; Row-hash verified splits | Core Engine | `[IMPLEMENTED]` |
| **Fold-Safe Feature Selection** | Multi-method rank aggregation fitted strictly inside training folds | Core Engine | `[IMPLEMENTED]` |
| **Durable Task Queue** | `durable_tasks` table, OS child process isolation, hard timeouts | Core Engine | `[IMPLEMENTED]` |
| **Multi-Worker Concurrency** | PostgreSQL `FOR UPDATE SKIP LOCKED` (SQLite transaction fallback) | Core Engine | `[IMPLEMENTED]` |
| **Model Artifact Integrity** | SHA-256 manifest + HMAC signature verification before deserialization | Security | `[IMPLEMENTED]` |
| **Four-Eyes Deployment Gate** | Server-side separation-of-duties (`approved_by != created_by`) | Governance | `[IMPLEMENTED]` |
| **One-Click Rollback** | Immediate retirement of active deployment and restored target routing | Governance | `[IMPLEMENTED]` |
| **Explainability (SHAP)** | Global feature importance summary & instance-level local SHAP explanations | Analytics | `[IMPLEMENTED]` |
| **Storage Architecture** | `LocalStorageService` implemented; pluggable `StorageService` interface | Storage | `[LOCAL ENGINE]` |
| **Distributed Object Store** | S3 / MinIO / Cloudflare R2 adapter interface | Storage | `[PLANNED EXTENSION]` |
| **Rate Limiting** | Sliding window in-memory limiter for single-node / edge protection | Security | `[SINGLE-NODE]` |
| **Distributed Rate Limiting**| Redis / API Gateway distributed rate limiting tier | Security | `[PLANNED EXTENSION]` |
| **Observability** | Structured JSON logging, health endpoints, authenticated Prometheus metrics | Telemetry | `[IMPLEMENTED]` |
| **APM / Error Tracking** | Sentry / OpenTelemetry integration hooks | Telemetry | `[PLANNED EXTENSION]` |

---

## 🚀 Quick Start

### Option A: Run with Docker Compose
```bash
# Standard Developer Stack (Hot-reloading, dev defaults)
docker compose -f docker-compose.dev.yml up --build -d

# Production-Hardened Stack (Internal database, secret enforcement, least-privilege)
POSTGRES_PASSWORD=your_secure_password JWT_SECRET=your_32char_secret docker compose -f docker-compose.prod.yml up --build -d
```
Access the application:
- **Frontend Application**: `http://localhost:3000`
- **Backend Swagger API**: `http://localhost:8000/docs`

### Option B: Local Developer Setup
```bash
# 1. Backend Setup
cd backend
python -m venv venv
# On Windows: .\venv\Scripts\activate | On Linux/macOS: source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
alembic upgrade head

# Start API server and background worker
python -m uvicorn app.main:app --port 8000 --reload
python -m app.tasks.worker

# 2. Frontend Setup (in a separate terminal)
cd ../frontend
npm install
cp .env.example .env
npm run dev
```

---

## 🧪 Deterministic Verification Suite

Run the single-command verification suite to validate the entire platform from dependencies to builds:

```bash
# Cross-Platform Python Runner
python scripts/verify.py

# Or native platform wrappers:
./scripts/verify.sh      # Linux / macOS
.\scripts\verify.ps1     # Windows PowerShell
```

The verification suite validates:
1. **Python Environment**: Dependencies & module imports verified.
2. **Database Schema**: Migration integrity and table synchronization.
3. **Backend Test Suite**: 467 pytest test cases passing green.
4. **Frontend Typecheck**: `tsc --noEmit` passing with 0 TypeScript errors.
5. **Frontend Unit Tests**: Vitest component and stage test suite passing.
6. **Frontend Build**: Vite production bundle compiled cleanly.

---

## 📦 Clean Client Release Packaging

To build a pristine, zero-pollution distribution archive for client delivery:

```bash
python scripts/package_release.py --output releases/ml_studio_client_release.zip
```

This utility automatically purges `node_modules`, `dist`, build caches, databases, temporary scripts, and private development `.env` credentials, generating an ultra-clean archive (< 5 MB) containing only validated source code and configuration templates.

---

## 📜 License

Proprietary & Confidential. Built for client deployment.
