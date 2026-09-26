# ADR-005: Sliding-Window Rate Limiter using Collections Deque

## Status
Accepted

## Context
Auth and inference endpoints require protection against volumetric floods and brute-force attacks. The prior implementation used a naive list comprehension filtering `[t for t in timestamps if t > window_start]` on every request, creating $\mathcal{O}(N)$ memory allocations and linear scan overhead per request.

## Decision
We adopted `collections.deque[float]` per client IP key within `app.core.rate_limiter.SlidingWindowRateLimiter`.
Because timestamps arrive strictly in monotonically increasing order:
- Expired timestamps are popped from the left ($\mathcal{O}(1)$ per item).
- New request timestamps are appended to the right ($\mathcal{O}(1)$).
- Each timestamp is pushed once and popped once, yielding amortized $\mathcal{O}(1)$ time complexity per request and $\mathcal{O}(R_{\text{window}})$ bounded memory.

## Alternatives Considered
1. **Redis sliding window / token bucket**: Adds an external network dependency and operational complexity; rejected for single-node deployments under the YAGNI principle.
2. **Fixed window counter**: Subject to burst boundary conditions (2x request rate at window edges); rejected.

## Consequences
- Single-node in-memory rate limiting operates at near-zero CPU and memory overhead.
- In-memory limits are process-local; horizontal scaling across multiple nodes will route via an API gateway / edge limiter or shared Redis backing store if distributed enforcement is mandated.
