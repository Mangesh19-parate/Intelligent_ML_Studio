# ADR-001: Modular Monolith + Dedicated Worker Architecture

## Status
**ACCEPTED**

## Context
Intelligent ML Studio is a tabular ML experimentation, governance, and model serving platform. As the system scales in capability (dataset profiling, cross-validation feature selection, multi-algorithm training tournament, SHAP explainability, four-eyes governance, and live inference), architectural boundaries must be enforced to prevent coupling while minimizing operational complexity.

Splitting the platform into distinct microservices (auth-service, ml-service, registry-service, governance-service, monitoring-service) introduces distributed transaction overhead, network latency, multi-repo synchronization challenges, and infrastructure management burden disproportionate to the system scale.

## Decision
We adopt a **Modular Monolith + Dedicated Worker** topology with shared persistence:
1. **API Monolith (`apps/backend/app/api/`)**: Stateless FastAPI application handling HTTP requests, client authentication, and metadata queries.
2. **Dedicated Worker (`apps/backend/app/workers/`)**: Background daemon executing long-running ML training and feature selection jobs in child OS processes with hard execution timeouts.
3. **Bounded Context Layers**:
   - `domain/`: Business invariants, state machines, and approval policies.
   - `ml/`: Pure ML algorithms, estimators, preprocessing, and SHAP explainability.
   - `application/`: Use-case orchestration coordinating domain and ML engines.
   - `infrastructure/`: External integrations (PostgreSQL, storage, security, task queues).
4. **Durable Task Queue (`durable_tasks`)**: ACID task orchestration using PostgreSQL `FOR UPDATE SKIP LOCKED`.

## Consequences
- **Positive**: Single deployable backend artifact, zero distributed networking latency for internal calls, ACID transactions across state transitions, shared domain models, and simplified local development.
- **Negative**: Worker and API share the same codebase dependencies (handled via unified requirements/lockfile).
