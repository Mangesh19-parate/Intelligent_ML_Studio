# Intelligent ML Studio — Release Feature Matrix & Verification Inventory

## Standard Release Policy
Every shipped feature, route, button, worker, script, migration, benchmark, security control, deployment path, and documented claim either works end-to-end or is removed from the release.

Categories:
- `IMPLEMENTED + TESTED`: Fully verified across UI, API, database, storage, worker, unit tests, and integration/E2E pipelines.
- `IMPLEMENTED + NOT YET TESTED`: Shipped code lacking complete end-to-end test evidence. (Release Blocker if included).
- `PLANNED`: Documented future capability, strictly excluded from production runtime bundle.
- `REMOVED`: Pruned or deprecated dead pathways removed to prevent security or stability hazards.

---

## 1. Feature Verification Matrix

| Feature / Capability | UI | API Route | DB Persistence | Background Worker | Object Storage | Unit / Invariant Tests | Integration / E2E Gate | Status |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **User Registration & Signup** | ✓ | `POST /api/v1/auth/register` | ✓ (`users`) | — | — | ✓ (`test_auth.py`) | ✓ | `IMPLEMENTED + TESTED` |
| **Authentication & JWT Login** | ✓ | `POST /api/v1/auth/login` | ✓ (`users`) | — | — | ✓ (`test_auth.py`) | ✓ | `IMPLEMENTED + TESTED` |
| **MFA / 2FA TOTP Enrollment & Verification** | ✓ | `POST /api/v1/auth/2fa/*` | ✓ (`users.totp_secret`) | — | — | ✓ (`test_mfa.py`) | ✓ | `IMPLEMENTED + TESTED` |
| **Token Refresh & Revocation** | ✓ | `POST /api/v1/auth/refresh`, `logout` | ✓ (`refresh_tokens`) | — | — | ✓ (`test_auth_flow.py`) | ✓ | `IMPLEMENTED + TESTED` |
| **Project Workspace Management** | ✓ | `GET/POST /api/v1/projects` | ✓ (`projects`) | — | — | ✓ (`test_projects.py`) | ✓ | `IMPLEMENTED + TESTED` |
| **Dataset Ingestion (CSV, JSON, Parquet, XLSX)** | ✓ | `POST /api/v1/datasets/upload` | ✓ (`datasets`, `dataset_versions`) | — | ✓ | ✓ (`test_datasets.py`) | ✓ | `IMPLEMENTED + TESTED` |
| **Dataset Profiling & Missingness Diagnostics** | ✓ | `GET /api/v1/datasets/{id}/profile` | ✓ (`dataset_profiles`) | ✓ | ✓ | ✓ (`test_profiling.py`) | ✓ | `IMPLEMENTED + TESTED` |
| **Leakage Detection & Invariant Guards** | ✓ | `POST /api/v1/datasets/{id}/leakage-check` | — | ✓ | — | ✓ (`test_day5_leakage_tests.py`) | ✓ | `IMPLEMENTED + TESTED` |
| **Experiment Configuration Freeze** | ✓ | `POST /api/v1/experiments` | ✓ (`experiments`, `configs`) | — | — | ✓ (`test_config_freeze.py`) | ✓ | `IMPLEMENTED + TESTED` |
| **Train/Val/Locked-Test Splitting (Stratified/Group/Time)** | ✓ | `POST /api/v1/experiments/{id}/split` | ✓ (`split_definitions`) | ✓ | ✓ | ✓ (`test_split_engine.py`) | ✓ | `IMPLEMENTED + TESTED` |
| **K-Fold Inner CV Model Training** | ✓ | `POST /api/v1/experiments/{id}/train` | ✓ (`experiments`, `trained_models`) | ✓ | ✓ | ✓ (`test_day6_full_cv_run.py`) | ✓ | `IMPLEMENTED + TESTED` |
| **Locked Test Set Invariant Isolation** | ✓ | `POST /api/v1/experiments/{id}/evaluate-locked` | ✓ (`locked_test_evaluations`) | ✓ | ✓ | ✓ (`test_day4_locked_test_consumption.py`) | ✓ | `IMPLEMENTED + TESTED` |
| **Feature Importance & SHAP Explainability** | ✓ | `GET /api/v1/models/{id}/shap` | — | ✓ | ✓ | ✓ (`test_day4_explain_and_prediction_logs.py`) | ✓ | `IMPLEMENTED + TESTED` |
| **Cryptographic HMAC Artifact Signing** | — | Internal Engine / Storage | ✓ (`trained_models.sha256`) | ✓ | ✓ | ✓ (`test_storage_security.py`) | ✓ | `IMPLEMENTED + TESTED` |
| **6-Condition Deployment Gate** | ✓ | `POST /api/v1/deployments/{id}/evaluate-gate` | ✓ (`deployment_gates`) | — | ✓ | ✓ (`test_deployment_gate_service.py`) | ✓ | `IMPLEMENTED + TESTED` |
| **Deployment Promotion & Activation** | ✓ | `POST /api/v1/deployments/{id}/approve` | ✓ (`deployments`) | — | — | ✓ (`test_day2_predict_endpoint_and_deployment_lifecycle.py`) | ✓ | `IMPLEMENTED + TESTED` |
| **Real-Time Model Inference Serving** | ✓ | `POST /api/v1/deployments/{id}/predict` | ✓ (`prediction_logs`) | — | ✓ | ✓ (`test_day2_predict_endpoint_and_deployment_lifecycle.py`) | ✓ | `IMPLEMENTED + TESTED` |
| **Serving Drift & Latency Telemetry** | ✓ | `GET /api/v1/deployments/{id}/metrics` | ✓ (`prediction_logs`) | — | — | ✓ (`test_day5_monitoring_volume_and_latency_split.py`) | ✓ | `IMPLEMENTED + TESTED` |
| **Automated Deployment Rollback** | ✓ | `POST /api/v1/deployments/{id}/rollback` | ✓ (`deployments`) | — | — | ✓ (`test_deployment_rollback.py`) | ✓ | `IMPLEMENTED + TESTED` |
| **Durable Task Queue & Crash Recovery** | — | `POST /api/v1/tasks/*` | ✓ (`durable_tasks`) | ✓ | ✓ | ✓ (`test_task_queue.py`) | ✓ | `IMPLEMENTED + TESTED` |

---

## 2. API Endpoint Contract Matrix

| Method | Endpoint | Auth Required | Required Role | Request Schema | Success Response | Error Codes |
| :--- | :--- | :---: | :---: | :--- | :--- | :--- |
| `POST` | `/api/v1/auth/register` | No | Public | `UserCreateRequest` | `201 Created` (`UserResponse`) | `400`, `409 Conflict`, `422` |
| `POST` | `/api/v1/auth/login` | No | Public | `LoginRequest` | `200 OK` (`TokenResponse`) | `401 Unauthorized`, `422` |
| `POST` | `/api/v1/auth/refresh` | No | Public | `RefreshTokenRequest` | `200 OK` (`TokenResponse`) | `401 Unauthorized` |
| `POST` | `/api/v1/auth/2fa/setup` | Yes | Authenticated | Empty | `200 OK` (`TOTPSetupResponse`) | `401`, `409` |
| `POST` | `/api/v1/auth/2fa/verify` | Yes | Authenticated | `TOTPVerifyRequest` | `200 OK` (`StatusResponse`) | `400`, `401` |
| `GET` | `/api/v1/projects` | Yes | Viewer+ | Query filters | `200 OK` (`List[ProjectResponse]`) | `401` |
| `POST` | `/api/v1/projects` | Yes | Editor+ | `ProjectCreateRequest` | `201 Created` (`ProjectResponse`) | `400`, `401`, `422` |
| `POST` | `/api/v1/datasets/upload` | Yes | Editor+ | `MultipartFormData` | `201 Created` (`DatasetResponse`) | `400`, `413`, `422` |
| `GET` | `/api/v1/datasets/{id}/profile` | Yes | Viewer+ | Path Param `id` | `200 OK` (`DatasetProfileResponse`) | `401`, `404` |
| `POST` | `/api/v1/experiments` | Yes | Editor+ | `ExperimentCreateRequest` | `201 Created` (`ExperimentResponse`) | `400`, `404`, `422` |
| `POST` | `/api/v1/experiments/{id}/train` | Yes | Editor+ | `TrainRequest` | `202 Accepted` (`TaskResponse`) | `400`, `404`, `409` |
| `POST` | `/api/v1/experiments/{id}/evaluate-locked`| Yes | Editor+ | Empty | `200 OK` (`EvaluationResponse`) | `400`, `403`, `404`, `409` |
| `POST` | `/api/v1/deployments/{id}/evaluate-gate` | Yes | Editor+ | Empty | `200 OK` (`GateEvaluationResponse`) | `400`, `404` |
| `POST` | `/api/v1/deployments/{id}/approve` | Yes | Admin | `DeploymentApproveRequest` | `200 OK` (`DeploymentResponse`) | `400`, `403`, `404`, `409` |
| `POST` | `/api/v1/deployments/{id}/predict` | Yes | Viewer+ | `PredictRequest` | `200 OK` (`PredictResponse`) | `400`, `404`, `422`, `429` |

---

## 3. UI Action & State Coverage Checklist

Every interactive frontend component must handle all respective states gracefully:
- [x] **Idle**: Default baseline UI state with active CTA buttons.
- [x] **Loading / Pending**: Spinners, skeleton loaders, disabled action triggers preventing double-submissions.
- [x] **Success**: Instant visual feedback, data refresh, state mutation confirmation.
- [x] **Empty State**: Explicit zero-data prompts with actionable creation pathways.
- [x] **Client Validation Error**: Inline form warnings before network dispatch.
- [x] **401 Unauthorized**: Automatic token refresh attempt $\rightarrow$ redirect to `/login` with stored return path.
- [x] **403 Forbidden**: Clear permission boundary message (e.g. Viewer trying to trigger training/deployment).
- [x] **404 Not Found**: Entity missing banner with navigation back to project dashboard.
- [x] **409 Conflict**: Explicit state-conflict explanation (e.g. experiment already running or locked test already consumed).
- [x] **429 Rate Limited**: Exponential backoff notification.
- [x] **500 Server Error**: Controlled error alert with request ID trace; never a raw unhandled exception or white screen.
- [x] **Network Offline / Timeout**: Connectivity warning banner with retry trigger.
