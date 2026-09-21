# System Architecture & Component Topology

## Overview
Intelligent ML Studio is designed as a **Modular Monolith + Dedicated Worker** execution platform for tabular machine learning experimentation, governance, and model serving.

```text
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                        INTELLIGENT ML STUDIO ARCHITECTURE                              │
└────────────────────────────────────────────────────────────────────────────────────────┘

                           React 18 + Vite Web UI (apps/frontend)
                                      │ (REST / JSON / JWT)
                                      ▼
                        FastAPI Modular API Monolith (apps/backend)
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

## Bounded Contexts

1. **`domain/`**: Pure domain entities, state transition machines (`VALID_EXPERIMENT_TRANSITIONS`), and invariant policies (Four-Eyes governance, Split isolation rules).
2. **`ml/`**: Algorithms, estimators, preprocessors, feature selection selectors, statistical profilers, metrics evaluation, and SHAP explainability.
3. **`application/`**: Use-case orchestration coordinating data persistence, ML engine execution, and response schemas.
4. **`infrastructure/`**: Storage services, database engine configuration, security token verification, and durable task queue dispatching.
5. **`workers/`**: Process-isolated worker daemons executing asynchronous tasks with heartbeat leases and automatic recovery.
