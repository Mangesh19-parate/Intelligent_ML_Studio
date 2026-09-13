# Intelligent ML Studio: System Architecture Specification

## 1. Architectural Philosophy

Intelligent ML Studio is designed as a **modular monolith with dedicated asynchronous worker execution**, eliminating data leakage by architectural construction and providing immutable cryptographic lineage from ingestion to deployment.

```text
                           React + TypeScript UI
                                  │
                                  ▼
                         FastAPI API Gateway
                                  │
          ┌───────────────────────┼───────────────────────┐
          ▼                       ▼                       ▼
   Data Intelligence       Experiment Engine          Governance
   • Structural Validation • 5-Fold CV Runner         • Model Passport
   • DQI Profiling Engine  • Rank Aggregator          • 4-Eyes Deployment Gate
   • Recommendations       • Out-of-Fold Tuning       • Prediction Logging
          │                       │                       │
          └───────────────────────┼───────────────────────┘
                                  ▼
                         PostgreSQL Database
                                  │
                  ┌───────────────┴───────────────┐
                  ▼                               ▼
          Artifact Storage                 Lineage & Audit
        • SHA-256 Pipeline Snapshots     • ReproducibilityRun Table
        • Model Checksums & Signatures   • State Transition Ledger
```

## 2. Partition & Preprocessing Isolation

1. **80/20 Outer Split**: Raw data is partitioned once at dataset upload into Development (80%) and Locked Test (20%) using deterministic SHA-256 row indexing.
2. **Fold-Safe Cross Validation**: Within the Development partition, $K$-Fold cross-validation isolates each train fold.
3. **Snapshot Immutability**: Fitted transformation pipelines and selected feature sets produce immutable JSON snapshots (`TransformationSnapshot`, `FeatureSelectionSnapshot`) referenced during model training and deterministic replay.
4. **Locked Test Evaluation**: Evaluated strictly once after model selection is frozen.

## 3. Asynchronous Job State Machine

Experiments transition through an idempotent state machine:
`QUEUED` $\to$ `RUNNING` $\to$ `SUCCEEDED` / `FAILED` / `TIMED_OUT` / `CANCELLED`.
