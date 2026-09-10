# ML Studio — Deployment

Two distinct meanings of "deployment" in this project — infrastructure deployment (how the app gets hosted) and ML model deployment governance (the gate). Both covered here.

## Infrastructure Deployment

```
Frontend:  Vercel  - React + Vite build, static/SSR hosting
Backend:   Render  - Dockerized FastAPI web service
Database:  Render managed PostgreSQL (or an equivalent managed Postgres)
```

### Required Configuration - Not Optional

**Persistent storage on Render.** Render's default web service has ephemeral local disk - a redeploy or restart wipes anything written via the local-filesystem `StorageService` implementation. This silently breaks artifact checksums, lineage, and the deployment gate's `artifact_verified` condition, none of which fail loudly until someone tries to load a "verified" artifact that no longer exists. Provision Render's persistent disk add-on and mount it at the `StorageService` local-FS root before storing a single artifact. The `StorageService` interface exists specifically so this doesn't require touching calling code - use it.

**CORS.** The Render-hosted API must explicitly allowlist the Vercel frontend's origin(s), including preview-deployment URLs if Vercel preview builds are used during development.

**Environment variables**, set per platform, never committed:
```
DATABASE_URL, JWT_SECRET, STORAGE_ROOT (pointing at the persistent disk mount),
CORS_ALLOWED_ORIGINS, API_BASE_URL (frontend's reference to the Render backend)
```

**Migrations.** `alembic upgrade head` runs as a Render deploy hook (pre-deploy or release phase), never manually against production after the fact. The same fresh-database migration check used in weekly regression is what should catch a migration that only worked because a dev database already had manually-patched state.

**Cold starts.** If using Render's free or low tier, the service spins down after inactivity and the first request after idle is slow. This is a real risk on demo/viva day, not just a performance footnote - either use an always-on tier for the demo window, or explicitly warm the backend up a few minutes before presenting. Don't discover this live.

### Local Development

Unchanged from the build process: `docker-compose up` brings up Postgres + API + frontend dev server in one command. The Vercel/Render split is a deployment-time concern, not a development-time one.

---

## ML Model Deployment Governance

### The Gate - Two Parts

```
8a Model Eligibility Check (5 conditions, owns ModelState.DEPLOYABLE, re-checkable):
   locked_test_evaluated, schema_locked, artifact_verified, lineage_complete,
   performance_threshold_passed

8b Deployment Approval Check (1 condition, evaluated fresh per deployment attempt):
   user_approved, approved_by != trained_models.created_by
```

### DeploymentState Lifecycle

```
CREATED -> GATE_PENDING -> (GATE_PASSED | GATE_BLOCKED, reason recorded)
        -> APPROVED -> DEPLOYED -> PAUSED -> RETIRED
```

### Demo Accounts (required for the separation-of-duties demo)

```
trainer@demo.com  - USER, default bundle (READ/EDIT_DATA/TRAIN/EXPORT), no DEPLOY
approver@demo.com - USER, default bundle + explicit DEPLOY override
```

Neither is ADMIN - this pair demonstrates the permission-override mechanism itself.

### Prediction & Logging

Decoupled `/predict` (fast path, cached pipeline in memory) and `/predict/{id}/explain` (SHAP). `prediction_logs.payload_mode` defaults to `HASHED`, documented in the UI as correlation/integrity, not anonymization. `FULL` mode requires explicit ADMIN or `DEPLOY`-permission opt-in with a visible warning.

### Monitoring

Operational monitoring only in the MVP: prediction volume, latency split into prediction vs. explanation. Drift/performance monitoring (PSI, etc.) is named future work, not silently absent - see `PRD.md`.
