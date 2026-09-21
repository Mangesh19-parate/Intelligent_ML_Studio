# ADR-002: Database-Backed Durable Task Queue

## Status
**ACCEPTED**

## Context
Long-running machine learning workflows (cross-validation tournaments, feature selection permutation passes, SHAP explainability matrices) require asynchronous execution without blocking HTTP request threads. External broker systems (Celery + Redis/RabbitMQ, Kafka) add deployment dependencies, separate failure domains, and state desynchronization risks between the task queue and database entities.

## Decision
We implement a lightweight, robust database-backed task engine on top of the `durable_tasks` table:
1. **Task Dispatch**: Tasks are inserted atomically into `durable_tasks` within the same transaction as experiment creation.
2. **Concurrent Worker Leasing**: Workers claim pending tasks using `SELECT ... FOR UPDATE SKIP LOCKED` on PostgreSQL (with transaction fallback on SQLite).
3. **Lease Renewal & Heartbeats**: Workers periodically update `lease_expires_at`. Dead workers' tasks are automatically recovered after lease expiration.
4. **OS Process Isolation**: Heavy ML workloads run in subprocesses to ensure memory reclamation upon completion and hard timeout termination.

## Consequences
- **Positive**: Zero external broker infrastructure, transactional consistency between business state and task queue, automatic recovery, zero message loss during crashes.
- **Negative**: Database polling overhead (mitigated by exponential backoff and index on `(status, scheduled_at)`).
