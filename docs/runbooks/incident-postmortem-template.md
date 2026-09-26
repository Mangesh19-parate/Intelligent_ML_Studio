# Incident Postmortem & Root Cause Analysis (RCA)

## Incident Overview
| Field | Details |
| :--- | :--- |
| **Incident ID** | INC-YYYYMMDD-01 |
| **Severity** | SEV-1 / SEV-2 / SEV-3 |
| **Date & Time (UTC)** | YYYY-MM-DD HH:MM:SS |
| **Duration / TTX** | Time to Detect: Xm \| Time to Mitigate: Ym \| Time to Resolve: Zm |
| **Impacted Services** | Inference API / Training Worker / Dashboard / Storage |
| **Incident Lead** | Lead Engineer |

---

## Executive Summary
A concise 2-3 paragraph non-technical summary of what happened, who was affected, how it was mitigated, and permanent preventive actions.

---

## Timeline of Events (UTC)
- **HH:MM** - Anomaly detected via automated alerting / metric threshold breach.
- **HH:MM** - Incident triage initiated; on-call engineer paged.
- **HH:MM** - Root cause identified as ...
- **HH:MM** - Mitigation deployed (rollback / configuration update / worker restart).
- **HH:MM** - System verified healthy; metrics restored to baseline.

---

## Root Cause Analysis (5 Whys)
1. **Why did the service fail?** ...
2. **Why did that occur?** ...
3. **Why was that condition present?** ...
4. **Why didn't automated tests catch it?** ...
5. **Why was our invariant guard bypassed?** ...

---

## Corrective & Preventive Action Items (CAPA)
| Action Item | Owner | Priority | Target Date | Ticket / PR |
| :--- | :--- | :--- | :--- | :--- |
| Add regression test for invariant breach | Engineer A | P0 | YYYY-MM-DD | PR #123 |
| Tighten rate limiter burst tolerance | Engineer B | P1 | YYYY-MM-DD | PR #124 |
| Update Prometheus alert latency threshold | DevOps | P2 | YYYY-MM-DD | Issue #125 |
