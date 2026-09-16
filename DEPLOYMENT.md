# ML Studio: Production Deployment Guide

This guide provides end-to-end instructions for deploying **ML Studio** to production:
- **Frontend (SPA):** [Vercel](https://vercel.com)
- **Backend (FastAPI):** [Render](https://render.com)
- **Database (PostgreSQL):** [Render PostgreSQL](https://render.com/docs/databases)

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
|        VERCEL (Frontend)        |   |       RENDER (Backend)       |
| - React 18 + Vite (SPA)         |   | - FastAPI Web Service        |
| - Edge CDN & Compression        |   | - Uvicorn Server on $PORT    |
| - SPA Rewrite (/ -> /index.html)|   | - Alembic Auto-Migrations    |
| - VITE_API_URL env config       |   | - Strict Production Hygiene  |
+---------------------------------+   +--------------+---------------+
                                                     |
                                                     | PostgreSQL SSL
                                                     v
                                      +------------------------------+
                                      |   RENDER POSTGRESQL / DB     |
                                      | - Managed Persistent Storage |
                                      | - Canonical RBAC Schema      |
                                      +------------------------------+
```

---

## 🔑 Secret Key Generation

Before deploying, generate two unique, cryptographically strong random secrets (minimum 32 characters) for production:

```bash
# In Python:
python -c "import secrets; print('JWT_SECRET=' + secrets.token_urlsafe(32)); print('ARTIFACT_SIGNING_KEY=' + secrets.token_urlsafe(32))"

# Or in Bash / OpenSSL:
openssl rand -hex 32
```

> [!CAUTION]
> In production (`ENV=production`), ML Studio enforces strict security validation:
> - `JWT_SECRET` and `ARTIFACT_SIGNING_KEY` must be at least 32 characters long.
> - Default or sample keys are rejected at startup.
> - `JWT_SECRET` and `ARTIFACT_SIGNING_KEY` must be distinct keys.
> - Wildcard CORS (`*`) and `SEED_DEMO_DATA=true` are strictly forbidden.

---

## 🚀 Part 1: Deploy Backend & Database on Render

### Option A: 1-Click Blueprint (Recommended)

1. Push your repository to **GitHub**.
2. Log in to [Render Dashboard](https://dashboard.render.com).
3. Click **New +** → **Blueprint**.
4. Connect your GitHub repository.
5. Render will automatically detect [`render.yaml`](./render.yaml) and configure:
   - A managed PostgreSQL instance (`ml-studio-db`)
   - A Python Web Service (`ml-studio-api`) with automatic migrations via [`backend/start.sh`](./backend/start.sh)
6. In the Blueprint variables review, set `BACKEND_CORS_ORIGINS` to include your Vercel URL (e.g. `https://ml-studio.vercel.app,http://localhost:3000`).
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

#### Step 2: Create FastAPI Web Service
1. In Render Dashboard, click **New +** → **Web Service**.
2. Connect your GitHub repository.
3. Configure the service settings:
   - **Name:** `ml-studio-api`
   - **Root Directory:** `backend`
   - **Runtime:** `Python 3`
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `./start.sh` (or `alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port $PORT --proxy-headers --forwarded-allow-ips='*'`)
   - **Health Check Path:** `/health`
4. Add the following **Environment Variables**:

| Variable | Value | Description |
| :--- | :--- | :--- |
| `ENV` | `production` | Enables production validation & security gates |
| `DATABASE_URL` | *(Paste Internal Database URL from Step 1)* | PostgreSQL database connection string |
| `AUTO_CREATE_TABLES` | `false` | Schema handled by Alembic migrations |
| `SEED_DEMO_DATA` | `false` | Prohibited in production |
| `STORAGE_LOCAL_DIR` | `/data` | Object storage directory |
| `JWT_SECRET` | *(Generated secret ≥32 chars)* | Signs user session JWTs |
| `ARTIFACT_SIGNING_KEY` | *(Generated secret ≥32 chars)* | HMAC signing key for model files |
| `BACKEND_CORS_ORIGINS` | `https://your-app.vercel.app` | Comma-separated allowed frontend origins |

5. Click **Create Web Service**. Render will deploy your backend and run all database migrations automatically.
6. Note down your backend URL: `https://ml-studio-api-xxxx.onrender.com`.

---

## 👤 Part 2: Bootstrap Initial Admin Account

Once the backend is deployed and the database is migrated, create the initial Administrator account:

1. Open your `ml-studio-api` service in the [Render Dashboard](https://dashboard.render.com).
2. Navigate to the **Shell** tab in the left sidebar.
3. Execute the idempotent admin bootstrap CLI command:

```bash
python -m scripts.bootstrap_admin --email admin@yourdomain.com --password YourStrongPassword123! --full-name "Lead Administrator"
```

4. You should see:
```
SUCCESS: Administrator account 'admin@yourdomain.com' (ID: ...) created successfully.
```

---

## ⚡ Part 3: Deploy Frontend on Vercel

1. Log in to [Vercel Dashboard](https://vercel.com/dashboard).
2. Click **Add New...** → **Project**.
3. Import your GitHub repository.
4. Configure the Project Settings:
   - **Framework Preset:** `Vite`
   - **Root Directory:** Click **Edit** and choose `frontend`
   - **Build Command:** `npm run build` (or leave default `vite build`)
   - **Output Directory:** `dist`
5. Expand **Environment Variables** and add:

| Key | Value | Description |
| :--- | :--- | :--- |
| `VITE_API_URL` | `https://ml-studio-api-xxxx.onrender.com/api/v1` | URL of your deployed Render backend |

6. Click **Deploy**.
7. Vercel will build the frontend with optimized chunk splitting and apply the SPA rewrites defined in [`frontend/vercel.json`](./frontend/vercel.json).
8. Once deployed, copy your production Vercel URL (e.g. `https://ml-studio-frontend.vercel.app`).

---

## 🔄 Part 4: Link Vercel Domain to Backend CORS

1. Go back to [Render Dashboard](https://dashboard.render.com) → `ml-studio-api` Web Service.
2. Go to the **Environment** tab.
3. Update `BACKEND_CORS_ORIGINS` to include your Vercel domains:
   ```
   https://ml-studio-frontend.vercel.app,https://your-custom-domain.com
   ```
4. Render will automatically redeploy the service with the updated CORS policy.

---

## ✅ Part 5: Production Verification Checklist

Perform these smoke tests to verify the deployment:

- [ ] **Health Endpoint:** Open `https://<render-url>/health` in your browser. It should return status `healthy`.
- [ ] **Readiness Probe:** Open `https://<render-url>/health/ready`. It should confirm database connectivity.
- [ ] **Frontend Loading:** Open `https://<vercel-url>` in your browser. The landing page should render smoothly.
- [ ] **SPA Direct Deep Linking:** Refresh on `https://<vercel-url>/login` or navigate directly. It should render without a 404.
- [ ] **Admin Login:** Log in using your bootstrapped credentials (`admin@yourdomain.com`).
- [ ] **2FA Setup:** Enable 2FA from account settings to verify TOTP generation and verification.
- [ ] **Data Ingestion:** Upload a sample CSV dataset to verify multipart uploads and object storage.
- [ ] **Experiment Run:** Execute a training run to verify model training, scoring, and artifact creation.

---

## 🛠️ Maintenance & Operations

### Database Migrations
When deploying updates with schema changes, the startup script ([`backend/start.sh`](./backend/start.sh)) executes `alembic upgrade head` before starting the server.

### Adding New Allowed Domains
To allow new frontend domains (e.g., custom domains, staging previews), simply update the `BACKEND_CORS_ORIGINS` environment variable in Render as a comma-separated list:
```
BACKEND_CORS_ORIGINS=https://app.example.com,https://preview.vercel.app
```

### Rotating Secrets
To rotate `JWT_SECRET` or `ARTIFACT_SIGNING_KEY`:
1. Generate new keys using `python -c "import secrets; print(secrets.token_urlsafe(32))"`.
2. Update the environment variables in Render.
3. Service will restart automatically with the new secrets.
