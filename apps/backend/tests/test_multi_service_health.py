import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch
from app.services.health_service import HealthService, SubsystemHealth

def test_liveness_endpoints(client: TestClient):
    for endpoint in ["/health/live", "/api/v1/health/live"]:
        response = client.get(endpoint)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "alive"
        assert "uptime_seconds" in data
        assert "timestamp" in data
        assert "service" in data

def test_readiness_endpoints_healthy(client: TestClient):
    for endpoint in ["/health/ready", "/api/v1/health/ready"]:
        response = client.get(endpoint)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ready"
        assert data["ready"] is True
        assert "database" in data["dependencies"]
        assert "storage" in data["dependencies"]
        assert "task_queue" in data["dependencies"]
        assert data["dependencies"]["database"]["status"] == "UP"
        assert data["dependencies"]["storage"]["status"] == "UP"

def test_readiness_endpoint_db_failure_returns_503(client: TestClient):
    with patch.object(HealthService, "check_database", return_value=SubsystemHealth(status="DOWN", latency_ms=10.0, details={"error": "Connection refused"})):
        response = client.get("/health/ready")
        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "unready"
        assert data["ready"] is False
        assert data["dependencies"]["database"]["status"] == "DOWN"

def test_readiness_endpoint_storage_failure_returns_503(client: TestClient):
    with patch.object(HealthService, "check_storage", return_value=SubsystemHealth(status="DOWN", latency_ms=5.0, details={"error": "Read-only filesystem"})):
        response = client.get("/health/ready")
        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "unready"
        assert data["ready"] is False
        assert data["dependencies"]["storage"]["status"] == "DOWN"

def test_detailed_health_status_endpoints(client: TestClient):
    for endpoint in ["/health/status", "/api/v1/health/status"]:
        response = client.get(endpoint)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] in ("HEALTHY", "DEGRADED")
        assert data["api_version"] == "v1"
        assert "code_version" in data
        assert "uptime_seconds" in data
        
        deps = data["dependencies"]
        assert "database" in deps
        assert "storage" in deps
        assert "task_queue" in deps
        assert "ml_runtime" in deps
        
        assert deps["database"]["status"] == "UP"
        assert deps["storage"]["status"] == "UP"
        assert deps["ml_runtime"]["status"] == "UP"
        assert "sklearn_version" in deps["ml_runtime"]["details"]

def test_detailed_health_status_unhealthy_returns_503(client: TestClient):
    with patch.object(HealthService, "check_database", return_value=SubsystemHealth(status="DOWN", latency_ms=25.0, details={"error": "DB disconnected"})):
        response = client.get("/health/status")
        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "UNHEALTHY"

def test_backward_compatible_baseline_health(client: TestClient):
    for endpoint in ["/health", "/api/v1/health"]:
        response = client.get(endpoint)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["api_version"] == "v1"
        assert "code_version" in data
        assert "timestamp" in data
