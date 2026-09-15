# ML Studio — Production Operations, Security & Resilience Guide

This document defines the operational architecture, security controls, resilience mechanisms, and compliance standards for ML Studio across all operational tiers (Tier 0 through Tier 3).

---

## Tier 0 — Security Baseline (Critical & Immediate)

### 1. Granular Resource Ownership & Multi-Tenant Access Control
Every resource endpoint (`/projects`, `/datasets`, `/experiments`, `/transformations`, `/feature-selection`, `/models`, `/deployments`) enforces explicit ownership checks via `ProjectService.get_project_by_id(project_id, current_user)`:
- If a user has the global `MANAGE_USERS` administrative permission, cross-project visibility is permitted.
- For standard users, access is strictly scoped to `project.owner_id == current_user.id`. Any attempt to access, preview, train, or deploy against unowned projects immediately yields `HTTP 403 Forbidden` or `HTTP 404 Not Found`.

### 2. Rate Limiting on Authentication Endpoints
- **Endpoints Protected**: `/api/v1/auth/login`, `/api/v1/auth/signup`, `/api/v1/auth/register`.
- **Mechanism**: In-memory thread-safe sliding window rate limiter (`app.core.rate_limiter.SlidingWindowRateLimiter`) for single-node and local deployments.
- **Distributed Note**: For multi-instance horizontal deployments across multiple containers, distributed rate limiting at the API Gateway / reverse proxy (e.g. Nginx, Cloudflare) or Redis tier is recommended.
- **Policy**:
  - `/auth/login`: Maximum 15 requests per 60-second window per IP.
  - `/auth/signup`: Maximum 10 requests per 60-second window per IP.
- **Response**: `HTTP 429 Too Many Requests` with dynamic `Retry-After` header.

### 3. Production Secret Management & JWT Rotation
- In production (`ENV=production`), `app.core.config.Settings` enforces:
  - `JWT_SECRET` must NOT match known development defaults (`dev-jwt-secret...`, `changeme`, etc.) and must be >= 32 characters.
  - Wildcard CORS origins (`"*"`) are rejected during startup.
- **Recommended Secret Managers**:
  - **AWS Secrets Manager / SSM Parameter Store**: Retrieve `JWT_SECRET` and `DATABASE_URL` via IAM instance profiles at container launch.
  - **HashiCorp Vault**: Read dynamic credentials from `/v1/secret/data/ml-studio`.
  - **Render / Vercel Secret Files**: Mount secrets as environment variables injected at deployment time.

### 4. Dependency Vulnerability Audits (`pip-audit`)
- Automated scanning via `pip-audit` runs in the CI/CD pipeline before every deploy.
- Dependency baseline: `fastapi>=0.110.0,<1.0.0`, `python-multipart>=0.0.9`, `cryptography>=42.0.0`.

### 5. HTTPS & Security Headers Middleware
- `app.core.security_headers.SecurityHeadersMiddleware` is registered in `main.py`:
  - Enforces automatic 301 redirection from HTTP to HTTPS when `X-Forwarded-Proto: http` in production.
  - Sets `Strict-Transport-Security: max-age=31536000; includeSubDomains; preload` (HSTS).
  - Injects `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `X-XSS-Protection: 1; mode=block`, and `Referrer-Policy: strict-origin-when-cross-origin`.

### 6. Two-Factor Authentication (2FA) & Multi-Factor Authentication (MFA)
- **Standard Protocol**: RFC 6238 Time-Based One-Time Password (TOTP) algorithm operating on 30-second time steps with $\pm 1$ step drift tolerance.
- **Pure Standard-Library Cryptography**: Built with Python `hmac`, `hashlib`, `struct`, and `secrets` to eliminate third-party supply-chain dependency risks.
- **Zero-Trust Login Flow**:
  - Primary credential verification (`POST /auth/login`) checks email and bcrypt password.
  - If 2FA is enabled, login halts and issues a signed, time-limited (5-minute) challenge token with `purpose: "2fa_challenge"`. No access or refresh tokens are issued at this stage.
  - Client submits the 6-digit TOTP code or emergency backup key to `POST /auth/2fa/verify-login`.
  - Upon successful verification, the backend issues standard in-memory JWT access tokens and sets the `HttpOnly`, `SameSite=Lax`, `Secure` refresh cookie.
- **Emergency Recovery Keys**:
  - Generates 8 single-use cryptographically secure alphanumeric backup keys during 2FA enrollment.
  - Stored exclusively as one-way SHA-256 hashes in the database (`two_factor_backup_codes`).
  - Key is permanently invalidated and removed from database once successfully consumed.
- **Enrollment & Lifecycle**:
  - `POST /auth/2fa/setup`: Generates Base32 secret and standard `otpauth://totp/...` URI compatible with Google Authenticator, Microsoft Authenticator, 1Password, and Apple Keychain.
  - `POST /auth/2fa/confirm`: Requires immediate live code verification before activating 2FA on the user record.
  - `POST /auth/2fa/disable`: Requires live password verification to prevent unauthorized downgrade attacks.


---

## Tier 1 — Scalability Architecture

### 1. Asynchronous Model Training Off the Request Path
- All model training (`POST /projects/{id}/experiments`) submits tasks to the persistent task engine (`app.tasks.experiment_tasks.submit_experiment_task`):
  - Backed by database records (`DurableTask` model) with lease management, process-level isolation, and worker timeouts.
  - PostgreSQL `FOR UPDATE SKIP LOCKED` guarantees multi-worker atomic task claiming with zero collisions (SQLite transaction locking for local dev).
  - HTTP requests return immediately with `HTTP 200 OK` (`status: "TRAINING"`), preventing proxy gateway timeouts.
  - Frontend polls `/experiments/{id}` or listens to lifecycle updates until completion.

### 2. Pluggable Storage Architecture
- The `StorageService` abstract base class (`app.services.storage_service.StorageService`) decouples artifact persistence from local disk.
- **Local Engine (Shipped)**: `LocalStorageService` manages structured local filesystem storage with path isolation.
- **Object Store Extension**: Pluggable interface defined for adding multi-node S3 / MinIO / Cloudflare R2 storage backends.

### 3. Database Connection Pooling
- SQLAlchemy engine configured in `app.core.database`:
  - `pool_size=10`, `max_overflow=20`, `pool_pre_ping=True`, `pool_recycle=1800`.
  - Read replicas can be attached via secondary sessionmakers for analytical reporting routes.

---

## Tier 2 — Operational Maturity & Incident Prevention

### 1. Test-Gated CI/CD Pipeline
- GitHub Actions workflow (`.github/workflows/ci.yml`) executes on every push and pull request to `main`:
  - **Backend Gate**: Runs `pip-audit` CVE checks and full 424-test `pytest` suite testing leakage invariants.
  - **Frontend Gate**: Runs TypeScript check (`tsc --noEmit`) and Vite production bundle build.
  - **Deploy Gate**: Deploys only trigger after all quality gates pass.

### 2. Structured Logging & Multi-Service Health Observability
- `StructuredLoggingMiddleware` emits structured JSON request logs including `request_id`, duration in ms, and status codes.
- **Container Orchestration & Health Endpoints**:
  - `GET /health/live` (`/api/v1/health/live`): Process liveness probe for Kubernetes / ECS container restart decisions (returns `200 OK` if process loop is responsive).
  - `GET /health/ready` (`/api/v1/health/ready`): Deep readiness probe validating database connectivity (`SELECT 1`), artifact volume writeability, and `DurableTask` engine. Returns `200 OK` when ready for user traffic or `503 Service Unavailable` if critical dependencies fail.
  - `GET /health/status` (`/api/v1/health/status`): Multi-service subsystem telemetry report detailing database latency, pool stats, disk free/used capacity, active workers, and scikit-learn/SHAP runtime readiness.
  - `GET /health` (`/api/v1/health`): Backward-compatible baseline health probe.
  - Authenticated Prometheus metrics hook: `/metrics`.

### 3. Backups, Restore & Migration Rollbacks
- **Automated Database Backups**:
  ```bash
  # Daily snapshot command (PostgreSQL)
  pg_dump -Fc --no-acl --no-owner -h $DB_HOST -U $DB_USER $DB_NAME > /backups/ml_studio_$(date +%F_%H%M%S).dump
  ```
- **Restore Verification Runbook**:
  ```bash
  # Restore to a staging database to verify backup integrity
  pg_restore -h $STAGING_DB_HOST -U $DB_USER -d $STAGING_DB_NAME --clean /backups/ml_studio_snapshot.dump
  ```
- **Alembic Schema Rollback**:
  ```bash
  # Roll back exactly one migration
  alembic downgrade -1
  ```

---

## Tier 3 — Compliance, Privacy & Governance

### 1. Data Retention Policy & Automated Pruning
- Scheduled cleanup script: `python backend/scripts/cleanup_data_retention.py 90`
  - Purges prediction audit logs and durable task execution records older than retention period (default 90 days).
  - Can be scheduled via cron or Kubernetes CronJob.

### 2. Encryption at Rest & in Transit
- **In Transit**: TLS 1.3 enforced by reverse proxy (Render / Cloudflare / Vercel) + HSTS headers.
- **At Rest**: PostgreSQL database volume encrypted via AES-256 (Render managed PostgreSQL / AWS RDS KMS).

### 3. Incident Response Runbook
1. **Severity 1 (Data Leakage / Auth Breach)**:
   - Rotate `JWT_SECRET` immediately in Secret Manager and restart backend instances to revoke all active tokens.
   - Review `/deployments/{id}/logs` and structured logs for unauthorized IP access patterns.
2. **Severity 2 (Worker Stalling / Training Deadlock)**:
   - Check `durable_tasks` table for tasks stuck in `RUNNING` beyond `timeout_seconds`.
   - The lease watchdog will automatically mark timed-out tasks as `FAILED` and release worker leases.
