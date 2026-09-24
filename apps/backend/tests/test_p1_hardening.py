"""
Phase 1 (P1) Hardening Tests:
- Production Secret Hygiene
- Production CORS Restrictions
- Refresh Token Rotation & Reuse Detection
- Cryptographic Signed Artifact Manifests
- Structured Logging & Metrics Monitoring
"""

import uuid
import pytest
from pydantic import ValidationError
from fastapi.testclient import TestClient
from app.core.config import Settings
from app.infrastructure.security.artifact_signing import (
    save_signed_model_artifact,
    verify_and_load_model_artifact,
    SecurityError
)
from app.services.auth_service import AuthService
from app.schemas.auth import LoginRequest
from app.main import app


def test_production_secret_hygiene_refuses_default_keys():
    """
    P1.1 INVARIANT: Startup validation MUST raise a ValueError if ENV=production
    and JWT_SECRET or ARTIFACT_SIGNING_KEY is a known default, less than 32 characters,
    or if ARTIFACT_SIGNING_KEY is identical to JWT_SECRET, or if SEED_DEMO_DATA is True.
    """
    with pytest.raises(ValidationError, match="Production security hygiene violation"):
        Settings(
            ENV="production",
            JWT_SECRET="dev-jwt-secret-key-change-in-production-1234567890",
            ARTIFACT_SIGNING_KEY="secure-artifact-key-11223344556677889900",
            BACKEND_CORS_ORIGINS=["https://app.mlstudio.io"],
        )

    with pytest.raises(ValidationError, match="Production security hygiene violation"):
        Settings(
            ENV="production",
            JWT_SECRET="a-very-long-and-secure-random-production-key-99887766554433221100",
            ARTIFACT_SIGNING_KEY="dev-artifact-key-change-in-production-0987654321",
            BACKEND_CORS_ORIGINS=["https://app.mlstudio.io"],
        )

    with pytest.raises(ValidationError, match="key separation required"):
        Settings(
            ENV="production",
            JWT_SECRET="a-very-long-and-secure-random-production-key-99887766554433221100",
            ARTIFACT_SIGNING_KEY="a-very-long-and-secure-random-production-key-99887766554433221100",
            BACKEND_CORS_ORIGINS=["https://app.mlstudio.io"],
        )

    with pytest.raises(ValidationError, match="SEED_DEMO_DATA is strictly prohibited"):
        Settings(
            ENV="production",
            SEED_DEMO_DATA=True,
            JWT_SECRET="a-very-long-and-secure-random-production-key-99887766554433221100",
            ARTIFACT_SIGNING_KEY="another-very-long-and-secure-random-key-1122334455",
            BACKEND_CORS_ORIGINS=["https://app.mlstudio.io"],
        )

    # Valid production settings pass
    valid_settings = Settings(
        ENV="production",
        JWT_SECRET="a-very-long-and-secure-random-production-key-99887766554433221100",
        ARTIFACT_SIGNING_KEY="another-very-long-and-secure-random-key-1122334455",
        BACKEND_CORS_ORIGINS=["https://app.mlstudio.io"],
    )
    assert valid_settings.ENV == "production"


def test_production_cors_disallows_wildcard():
    """
    P1.2 INVARIANT: Startup validation MUST raise a ValueError if ENV=production
    and BACKEND_CORS_ORIGINS contains wildcard '*'.
    """
    with pytest.raises(ValidationError, match="Wildcard CORS origin"):
        Settings(
            ENV="production",
            JWT_SECRET="a-very-long-and-secure-random-production-key-99887766554433221100",
            ARTIFACT_SIGNING_KEY="another-very-long-and-secure-random-key-1122334455",
            BACKEND_CORS_ORIGINS=["*"],
        )


def test_refresh_token_rotation_and_reuse_detection(db_session, create_test_user):
    """
    P1.3 INVARIANT: Using a refresh token rotates it and issues a new pair.
    Attempting to reuse the consumed refresh token MUST trigger an HTTP 401 reuse rejection.
    """
    test_user = create_test_user("user_rotation@mlstudio.io")
    service = AuthService(db_session)

    # Authenticate user to obtain initial token pair
    login_resp, initial_refresh = service.authenticate_user(LoginRequest(email="user_rotation@mlstudio.io", password="password123"))
    assert initial_refresh is not None

    # 1. First refresh exchange -> SUCCEEDS and rotates
    rotated_resp, new_refresh = service.refresh_access_token(initial_refresh)
    assert rotated_resp.access_token is not None
    assert new_refresh != initial_refresh

    # 2. Second exchange with the SAME initial refresh token -> REJECTED with 401 reuse detection
    with pytest.raises(Exception) as exc_info:
        service.refresh_access_token(initial_refresh)
    
    assert "Refresh token reuse detected" in str(exc_info.value)


def test_signed_artifact_manifest_and_tamper_detection(tmp_path):
    """
    P1.4 INVARIANT: Signed model artifacts produce a valid HMAC manifest.
    Altering the artifact content without a valid HMAC signature strictly blocks loading.
    """
    artifact_path = tmp_path / "model.joblib"
    fake_model = {"model_name": "RandomForestClassifier", "weights": [0.1, 0.4, 0.5]}
    secret = "test-secret-hmac-key-12345678901234567890"

    # Save signed artifact
    save_signed_model_artifact(fake_model, artifact_path, secret=secret)
    assert artifact_path.exists()
    assert (tmp_path / "model.manifest.json").exists()

    # Load signed artifact -> SUCCEEDS
    loaded = verify_and_load_model_artifact(artifact_path, secret=secret)
    assert loaded["model_name"] == "RandomForestClassifier"

    # Tamper with the artifact content
    with open(artifact_path, "wb") as f:
        f.write(b"TAMPERED_MALICIOUS_BYTECODE")

    # Attempt to load tampered artifact -> BLOCKED
    with pytest.raises(SecurityError, match="Artifact integrity violation|Artifact signature violation"):
        verify_and_load_model_artifact(artifact_path, secret=secret)


def test_structured_logging_and_authenticated_metrics(client, create_test_user, auth_headers):
    """
    P1.5 INVARIANT: Requests include X-Request-ID in response headers.
    Metrics endpoint requires authentication (HTTP 401 unauthenticated, HTTP 200 authenticated).
    """
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert "X-Request-ID" in response.headers

    # Custom correlation ID is preserved
    custom_id = f"req-{uuid.uuid4()}"
    res_custom = client.get("/api/v1/health", headers={"X-Request-ID": custom_id})
    assert res_custom.headers.get("X-Request-ID") == custom_id

    # Unauthenticated /metrics must be rejected
    res_unauth = client.get("/api/v1/metrics")
    assert res_unauth.status_code == 401

    # Authenticated /metrics succeeds
    user = create_test_user("metrics_user@mlstudio.io")
    res_metrics = client.get("/api/v1/metrics", headers=auth_headers(user))
    assert res_metrics.status_code == 200
    metrics_data = res_metrics.json()
    assert "task_queue_depth" in metrics_data
    assert "tasks_succeeded" in metrics_data
    assert "request_latency_p50_ms" in metrics_data


def test_demo_accounts_skipped_when_disabled(db_session):
    """
    P0.1 INVARIANT: Demo accounts (trainer@demo.com, approver@demo.com) must NOT be seeded
    unless settings.SEED_DEMO_DATA is explicitly True.
    """
    from app.core.config import settings
    from app.core.seeder import seed_rbac_data
    from app.models.user import User

    # Clean existing demo users if any in test DB
    db_session.query(User).filter(User.email.in_(["trainer@demo.com", "approver@demo.com"])).delete(synchronize_session=False)
    db_session.commit()

    original_val = settings.SEED_DEMO_DATA
    try:
        settings.SEED_DEMO_DATA = False
        seed_rbac_data(db_session)

        # Confirm demo accounts were NOT created
        trainer = db_session.query(User).filter(User.email == "trainer@demo.com").first()
        approver = db_session.query(User).filter(User.email == "approver@demo.com").first()
        assert trainer is None
        assert approver is None
    finally:
        settings.SEED_DEMO_DATA = original_val


def test_state_machine_transition_enforcement(client, create_test_user, auth_headers):
    """
    P1 INVARIANT: Project pipeline_stage cannot be bypassed via PUT /projects/{id}.
    Stage transitions must use POST /projects/{id}/transition and follow legal graph.
    """
    user = create_test_user("sm_user@mlstudio.io")
    headers = auth_headers(user)

    # 1. Create project (initial stage = DATA)
    create_res = client.post("/api/v1/projects", json={"project_name": "SM Test Project"}, headers=headers)
    assert create_res.status_code == 201
    proj_id = create_res.json()["id"]

    # 2. Attempt to bypass state machine via regular PUT -> ignored / blocked
    put_res = client.put(f"/api/v1/projects/{proj_id}", json={"project_name": "Renamed SM Project", "pipeline_stage": "DEPLOYED"}, headers=headers)
    assert put_res.status_code == 200
    assert put_res.json()["pipeline_stage"] == "DATA"  # pipeline_stage was NOT updated

    # 3. Attempt illegal transition via POST /projects/{id}/transition (DATA -> DEPLOYED is illegal)
    bad_trans = client.post(f"/api/v1/projects/{proj_id}/transition", json={"target_stage": "DEPLOYED"}, headers=headers)
    assert bad_trans.status_code == 422

    # 4. Perform legal transition (DATA -> SPLIT is legal)
    good_trans = client.post(f"/api/v1/projects/{proj_id}/transition", json={"target_stage": "SPLIT"}, headers=headers)
    assert good_trans.status_code == 200
    assert good_trans.json()["pipeline_stage"] == "SPLIT"


def test_object_level_model_and_deployment_authorization(client, db_session, create_test_user):
    """
    P0.2 INVARIANT (IDOR Protection): A user with global READ/DEPLOY cannot access or mutate
    models or deployments belonging to another user's project.
    """
    from app.services.auth_service import AuthService
    from app.schemas.auth import LoginRequest
    from app.models.project import Project
    from app.models.experiment import Experiment
    from app.models.trained_model import TrainedModel
    from app.models.deployment import Deployment

    # Create Owner User A and Attacker User B
    user_a = create_test_user("victim_a@mlstudio.io")
    user_b = create_test_user("attacker_b@mlstudio.io")

    # Create Project, Experiment, Model, Deployment for User A
    proj_a = Project(owner_id=user_a.id, project_name="Victim Project", task_type="CLASSIFICATION", pipeline_stage="DEPLOYED")
    db_session.add(proj_a)
    db_session.flush()

    exp_a = Experiment(project_id=proj_a.id, status="REGISTERED", task_type="CLASSIFICATION")
    db_session.add(exp_a)
    db_session.flush()

    model_a = TrainedModel(experiment_id=exp_a.id, algorithm_name="RandomForestClassifier", hyperparameters={})
    db_session.add(model_a)
    db_session.flush()

    dep_a = Deployment(model_id=model_a.id, endpoint_path=f"/api/v1/predict/{model_a.id}", status="DEPLOYED", deployed_by=user_a.id)
    db_session.add(dep_a)
    db_session.commit()

    # Authenticate User B
    auth_service = AuthService(db_session)
    tokens_b, _ = auth_service.authenticate_user(LoginRequest(email="attacker_b@mlstudio.io", password="password123"))
    headers_b = {"Authorization": f"Bearer {tokens_b.access_token}"}

    # User B attempts to access Model A metrics -> HTTP 403 Forbidden
    res_model = client.get(f"/api/v1/models/{model_a.id}/metrics", headers=headers_b)
    assert res_model.status_code == 403

    # User B attempts to access Model A passport -> HTTP 403 Forbidden
    res_passport = client.get(f"/api/v1/models/{model_a.id}/passport", headers=headers_b)
    assert res_passport.status_code == 403

    # User B attempts to access Deployment A details -> HTTP 403 Forbidden
    res_dep = client.get(f"/api/v1/deployments/{dep_a.id}", headers=headers_b)
    assert res_dep.status_code == 403

    # User B attempts to pause Deployment A -> HTTP 403 Forbidden (or permission denied)
    res_pause = client.put(f"/api/v1/deployments/{dep_a.id}/status", json={"status": "PAUSED"}, headers=headers_b)
    assert res_pause.status_code in [403, 401]
