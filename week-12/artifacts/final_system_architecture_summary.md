# Intelligent ML Studio — Final System Architecture Summary

**Milestone:** Phase 12 (Week 12) — Final Architecture & System Specifications  
**System:** Intelligent ML Studio (Tabular Machine Learning Workbench)  
**Status:** COMPLETE, AUDITED & VERIFIED  
**Date:** September 11, 2026

---

## 1. High-Level Architecture Overview

Intelligent ML Studio is an enterprise-grade tabular machine learning workbench built to structurally eliminate methodological data leakage, enforce strict governance with separation of duties, and deliver end-to-end cryptographic model lineage.

```mermaid
graph TD
    subgraph Client Layer
        UI[React 18 + TypeScript + Tailwind Frontend]
        REST_CLIENT[External Inference API Client]
    end

    subgraph Platform Backend Layer (FastAPI)
        AUTH[Auth & Granular RBAC / Overrides]
        DATA_SVC[Data Upload & Structural Validation]
        SPLIT_SVC[Deterministic Outer Splitter]
        DQI_SVC[DQI Profiling & Task Type Detection]
        TRANS_SVC[Transformation Engine & Benchmark]
        FS_SVC[Feature Selection & Rank Aggregation]
        CANONICAL[Canonical Experiment Engine]
        EVAL_SVC[Evaluation & Locked Test Gate]
        DIAG_SVC[SHAP & Permutation Explainers]
        PASSPORT_SVC[Model Passport & Lineage]
        GATE_SVC[Two-Phase Deployment Gate]
        PRED_SVC[Prediction & Drift Monitoring]
        DIFF_SVC[Counterfactual Experiment Diff]
    end

    subgraph Research Track (Standalone)
        PHASED_RUNNER[4-Phase Phased Stability Runner]
        STAT_ENGINE[Statistical Hypothesis Testing]
        RESEARCH_STORE[ResultsStore - SQLite & Parquet]
    end

    subgraph Storage & Infrastructure Layer
        DB[(PostgreSQL Database)]
        DISK_STORAGE[Artifact Storage - SHA-256 Verified]
    end

    UI --> AUTH
    AUTH --> DATA_SVC --> SPLIT_SVC --> DQI_SVC --> TRANS_SVC --> FS_SVC --> CANONICAL --> EVAL_SVC --> DIAG_SVC --> PASSPORT_SVC --> GATE_SVC --> PRED_SVC
    REST_CLIENT --> PRED_SVC
    CANONICAL --> DB
    CANONICAL --> DISK_STORAGE
    PASSPORT_SVC --> DB
    GATE_SVC --> DB
    PHASED_RUNNER --> CANONICAL
    PHASED_RUNNER --> RESEARCH_STORE
```

---

## 2. The 8 Platform Invariant Domains

1. **Domain 1: Locked-Test Disjointness & Reordering Invariance** — Ingestion assigns unique UUID `row_uid`s; physical row shuffling does not alter split assignment or data hashes.
2. **Domain 2: Fit Scope Isolation** — All scalers, imputers, and feature selectors fit strictly inside cross-validation training fold slices; validation and locked test sets only invoke `.transform()`.
3. **Domain 3: Deterministic Tie-Breaks** — 3-tier deterministic sorting (`-score` $\rightarrow$ `+rank_sum` $\rightarrow$ `+name`) and threshold tie-breaking to distance from 0.5.
4. **Domain 4: Platform Scope Boundary** — `RANK_AGGREGATION_STABILITY` is strictly blocked at the platform API with HTTP 400 (ADR-005).
5. **Domain 5: Out-of-Fold Decision Threshold Invariance** — Binary classification decision thresholds are tuned strictly on out-of-fold validation predictions and frozen before test evaluation.
6. **Domain 6: Locked Test Consumption** — Single authoritative evaluation on the Locked Test partition; re-evaluations tagged `TEST_REUSED_DIAGNOSTIC`.
7. **Domain 7: Concurrency Lock Mutex** — Atomic state checks prevent concurrent training attempts on the same project (HTTP 409 Conflict).
8. **Domain 8: State Machine Legality vs. Gate Eligibility Separation** — Pure separation between state transition legality (`ModelState.DEPLOYABLE`) and substantive deployment approval (`approved_by != created_by`).

---

## 3. Technology Stack & Directory Structure

```
Intelligent_ML_Studio/
├── backend/
│   ├── app/
│   │   ├── api/v1/          # FastAPI REST endpoints
│   │   ├── config/          # State machines, settings, invariants
│   │   ├── core/            # Database session, auth, dependencies
│   │   ├── models/          # SQLAlchemy ORM models (25 tables)
│   │   ├── repositories/    # Clean architecture data access layer
│   │   ├── schemas/         # Pydantic v2 validation schemas
│   │   └── services/        # Business logic & domain services (27 services)
│   └── tests/               # Consolidated invariant, unit & integration tests (58 files)
├── frontend/                # React 18, TypeScript, Tailwind CSS, Lucide icons
├── research/                # Pre-registered Research Track & stability evaluation
├── docs/                    # Architecture contracts & system specifications
└── week-01/ ... week-12/    # Milestone evidence packages & deliverables
```
