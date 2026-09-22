# ML Studio: Production Deployment Guide

This guide provides authoritative, end-to-end instructions for deploying **Intelligent ML Studio** to production:
- **Frontend (SPA):** [Vercel](https://vercel.com)
- **Backend API (FastAPI):** [Render Web Service](https://render.com)
- **ML Task Worker (Durable Daemon):** [Render Background Worker](https://render.com)
- **Database (PostgreSQL):** [Render Managed PostgreSQL](https://render.com/docs/databases)
- **Shared Object Storage:** S3-Compatible Storage ([AWS S3](https://aws.amazon.com/s3/), [Cloudflare R2](https://www.cloudflare.com/developer-platform/r2/), or [MinIO](https://min.io))

---

## 🏗️ Architecture & Topology

```
+--------------------------------------------------------------------+
|                           USER BROWSER                             |
+---------------------------------+----------------------------------+
                                  |
            HTTPS (HTML/JS/Assets)| HTTPS API Requests (with JWT/CORS)
                                  v
+---------------------------------+   +------------------------------+
|        VERCEL (Frontend)        |   |    RENDER (FastAPI Web API)  |
| - React 18 + Vite (SPA)         |   | - apps/backend/start.sh      |
| - apps/frontend/vercel.json     |   | - Uvicorn Server on $PORT    |
| - VITE_API_URL env config       |   | - Alembic Auto-Migrations    |
| - Edge CDN & Compression        |   | - Enforces Auth/Rate Limits  |
+---------------------------------+   +--------------+---------------+
                                                     |
                         +---------------------------+---------------------------+
                         |                                                       |
                         | PostgreSQL SSL                                        | S3 Object Storage API
                         v                                                       v
          +------------------------------+                        +------------------------------+
          |    RENDER POSTGRESQL / DB    |                        |   S3-COMPATIBLE OBJECT STORE |
          | - Canonical RBAC Schema      |                        | - Datasets (Parquet/CSV)     |
          | - Durable Tasks & Leases     |                        | - Signed Model Artifacts     |
          | - Lineage & Audit Trails     |                        | - HMAC Manifests & Snapshots |
          +--------------+---------------+                        +--------------+---------------+
                         |                                                       ^
                         | Polls Tasks (FOR UPDATE SKIP LOCKED)                  | Reads/Writes Artifacts
                         v                                                       |
          +----------------------------------------------------------------------+
          |                   RENDER (Durable ML Worker Service)                 |
          | - apps/backend: python -m app.tasks.worker                          |
          | - Process Isolation, Heartbeats & Auto-Recovery                      |
          +----------------------------------------------------------------------+
```

---

## 🔑 Secret Key & Storage Configuration

Before deploying, generate two unique, cryptographically strong random secrets (minimum 32 characters) for production:

```bash
# In Python:
python -c "import secrets; print('JWT_SECRET=' + secrets.token_urlsafe(32)); print('ARTIFACT_SIGNING_KEY=' + secrets.token_urlsafe(32))"

# Or in Bash / OpenSSL:
openssl rand -hex 32
```

> [!CAUTION]
> In production (`ENV=production`), ML Studio enforces strict security invariants:
> - `JWT_SECRET` and `ARTIFACT_SIGNING_KEY` must be at least 32 characters long.
> - Default or sample keys are rejected at startup.
> - `JWT_SECRET` and `ARTIFACT_SIGNING_KEY` must be distinct keys (key separation invariant).
> - Wildcard CORS (`*`) and `SEED_DEMO_DATA=true` are strictly forbidden.
> - Render API and Worker instances MUST share the same S3-compatible bucket and database.

---

## 🚀 Part 1: Deploy Backend, Worker & Database on Render

### Option A: 1-Click Blueprint (Recommended)

1. Push your repository to **GitHub**.
2. Log in to [Render Dashboard](https://dashboard.render.com).
3. Click **New +** → **Blueprint**.
4. Connect your GitHub repository.
5. Render will detect [`infra/render/render.yaml`](./infra/render/render.yaml) and configure:
   - A managed PostgreSQL instance (`ml-studio-db`)
   - A Python Web Service (`ml-studio-api`) with automatic migrations via [`apps/backend/start.sh`](./apps/backend/start.sh)
   - A dedicated Python Background Worker (`ml-studio-worker`) running `python -m app.tasks.worker`
6. In the Blueprint variables review:
   - Set `BACKEND_CORS_ORIGINS` to include your Vercel URL (e.g. `https://ml-studio.vercel.app,http://localhost:3000`).
   - Configure S3 credentials (`S3_BUCKET_NAME`, `S3_ACCESS_KEY_ID`, `S3_SECRET_ACCESS_KEY`, and `S3_ENDPOINT_URL` if using R2/MinIO).
7. Click **Apply**.

---

### Option B: Manual Setup on Render

#### Step 1: Create PostgreSQL Database
1. In Render Dashboard, click **New +** → **PostgreSQL**.
2. **Name:** `ml-studio-db`
3. **Database:** `mlstudio`
4. **User:** `mlstudio_user`
5. **Plan:** Free or Starter
6. Click **Create Database**.
7. Once created, copy the **Internal Database URL** (e.g., `postgres://mlstudio_user:...@dpg-...-a/mlstudio`).

#### Step 2: Create FastAPI Web API Service
1. In Render Dashboard, click **New +** → **Web Service**.
2. Connect your GitHub repository.
3. Configure the service settings:
   - **Name:** `ml-studio-api`
   - **Root Directory:** `apps/backend`
   - **Runtime:** `Python 3`
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `./start.sh`
   - **Health Check Path:** `/health`
4. Add the following **Environment Variables**:

| Variable | Value | Description |
| :--- | :--- | :--- |
| `ENV` | `production` | Enables production validation & security gates |
| `DATABASE_URL` | *(Paste Internal Database URL from Step 1)* | PostgreSQL database connection string |
| `AUTO_CREATE_TABLES` | `false` | Schema handled by Alembic migrations |
| `SEED_DEMO_DATA` | `false` | Prohibited in production |
| `STORAGE_BACKEND` | `s3` | Shared cloud object storage |
| `S3_BUCKET_NAME` | `my-ml-studio-bucket` | S3 bucket name |
| `S3_ACCESS_KEY_ID` | `...` | S3 / Cloudflare R2 Access Key |
| `S3_SECRET_ACCESS_KEY` | `...` | S3 / Cloudflare R2 Secret Key |
| `S3_REGION_NAME` | `us-east-1` | S3 Region |
| `JWT_SECRET` | *(Generated secret ≥32 chars)* | Signs user session JWTs |
| `ARTIFACT_SIGNING_KEY` | *(Generated secret ≥32 chars)* | HMAC signing key for model files |
| `BACKEND_CORS_ORIGINS` | `https://your-app.vercel.app` | Comma-separated allowed frontend origins |

5. Click **Create Web Service**.

#### Step 3: Create Dedicated Background Worker Service
1. In Render Dashboard, click **New +** → **Background Worker**.
2. Connect your GitHub repository.
3. Configure settings:
   - **Name:** `ml-studio-worker`
   - **Root Directory:** `apps/backend`
   - **Runtime:** `Python 3`
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `python -m app.tasks.worker`
4. Add the same Environment Variables (`ENV=production`, `DATABASE_URL`, `STORAGE_BACKEND`, `S3_*`, `JWT_SECRET`, `ARTIFACT_SIGNING_KEY`).
5. Click **Create Background Worker**.

---

## 👤 Part 2: Bootstrap Initial Admin Account

Once the backend is deployed and migrated, bootstrap the administrator account:

1. Open your `ml-studio-api` service in the [Render Dashboard](https://dashboard.render.com).
2. Navigate to the **Shell** tab in the left sidebar.
3. Execute the admin bootstrap CLI command:

```bash
python -m scripts.bootstrap_admin --email admin@yourdomain.com --password YourStrongPassword123! --full-name "Lead Administrator"
```

---

## ⚡ Part 3: Deploy Frontend on Vercel

1. Log in to [Vercel Dashboard](https://vercel.com/dashboard).
2. Click **Add New...** → **Project**.
3. Import your GitHub repository.
4. Configure Project Settings:
   - **Framework Preset:** `Vite`
   - **Root Directory:** `apps/frontend`
   - **Build Command:** `npm run build`
   - **Output Directory:** `dist`
5. Expand **Environment Variables** and add:

| Key | Value | Description |
| :--- | :--- | :--- |
| `VITE_API_URL` | `https://ml-studio-api-xxxx.onrender.com/api/v1` | URL of your deployed Render backend |

6. Click **Deploy**. Vercel will build the frontend and apply SPA rewrites defined in [`apps/frontend/vercel.json`](./apps/frontend/vercel.json).

---

## ✅ Part 4: Production Verification Checklist

- [ ] **Health Probe:** Open `https://<render-url>/health` in browser. Returns `healthy`.
- [ ] **Readiness Probe:** Open `https://<render-url>/health/ready`. Confirms database connectivity.
- [ ] **Frontend Loading:** Open `https://<vercel-url>`. Landing page renders cleanly.
- [ ] **SPA Direct Linking:** Refresh on `https://<vercel-url>/login`. Renders without 404.
- [ ] **Admin Login:** Log in using bootstrapped admin credentials.
- [ ] **2FA Setup:** Enable 2FA from account settings to verify TOTP generation.
- [ ] **Data Ingestion:** Upload a sample CSV/Parquet dataset to verify multipart uploads to object store.
- [ ] **Experiment Run:** Execute training to verify durable worker task claiming, fold execution, and HMAC artifact manifest creation.
