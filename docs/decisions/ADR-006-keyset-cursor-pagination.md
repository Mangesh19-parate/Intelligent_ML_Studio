# ADR-006: Keyset Cursor-Based Pagination for High-Volume Entities

## Status
Accepted

## Context
High-volume database queries (projects, audit logs, prediction logs) suffered performance degradation under offset pagination (`OFFSET S LIMIT L`), which forces the database engine to scan and discard $S$ rows ($\mathcal{O}(S + L)$). Additionally, offset pagination exhibits page drift and duplicate row reads under concurrent insertions.

## Decision
We implemented keyset pagination in `app.core.pagination` using opaque URL-safe base64 cursor tokens containing `{"t": created_at_iso, "id": uuid}`.
- SQL Query Filter: `WHERE (created_at < :t) OR (created_at == :t AND id < :id)`
- SQL Sort: `ORDER BY created_at DESC, id DESC`
- Time Complexity: $\mathcal{O}(\log N + L)$ direct B-Tree index seek regardless of pagination depth.

## Alternatives Considered
1. **Offset-limit pagination**: Simple but degrades linearly on deep pages and drifts on active workloads.
2. **Page number token hashing**: Retains offset-scan performance penalty.

## Consequences
- Deep pagination scales predictably without database load spikes.
- Pagination requires ordering on an indexed monotonic column (`created_at`, `id`).
