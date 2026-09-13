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
from app.core.artifact_signing import (
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
    and JWT_SECRET is a known default or less than 32 characters.
    """
    with pytest.raises(ValidationError, match="Production security hygiene violation"):
        Settings(
            ENV="production",
            JWT_SECRET="dev-jwt-secret-key-change-in-production-1234567890",
            BACKEND_CORS_ORIGINS=["https://app.mlstudio.io"],
        )

    with pytest.raises(ValidationError, match="Production security hygiene violation"):
        Settings(
            ENV="production",
            JWT_SECRET="short-secret-123",
            BACKEND_CORS_ORIGINS=["https://app.mlstudio.io"],
        )

    # Valid production settings pass
    valid_settings = Settings(
        ENV="production",
        JWT_SECRET="a-very-long-and-secure-random-production-key-99887766554433221100",
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
    tokens = service.authenticate_user(LoginRequest(email="user_rotation@mlstudio.io", password="password123"))
    initial_refresh = tokens.refresh_token

    # 1. First refresh exchange -> SUCCEEDS and rotates
    rotated = service.refresh_access_token(initial_refresh)
    assert rotated.access_token is not None
    assert rotated.refresh_token != initial_refresh

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


def test_structured_logging_and_correlation_id(client):
    """
    P1.5 INVARIANT: Requests include X-Request-ID in response headers and metrics endpoint returns queue data.
    """
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert "X-Request-ID" in response.headers

    # Custom correlation ID is preserved
    custom_id = f"req-{uuid.uuid4()}"
    res_custom = client.get("/api/v1/health", headers={"X-Request-ID": custom_id})
    assert res_custom.headers.get("X-Request-ID") == custom_id

    # Test metrics endpoint
    res_metrics = client.get("/api/v1/metrics")
    assert res_metrics.status_code == 200
    metrics_data = res_metrics.json()
    assert "task_queue_depth" in metrics_data
    assert "tasks_succeeded" in metrics_data
    assert "request_latency_p50_ms" in metrics_data
