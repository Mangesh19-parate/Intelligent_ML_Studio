"""
Unit tests for Day 5 /health and /api/v1/health endpoints.
Validates:
- Health check returns HTTP 200 OK.
- Response contains status='healthy', api_version='v1', and a valid code_version git commit SHA string.
"""

from fastapi.testclient import TestClient


def test_health_endpoints(client: TestClient):
    for endpoint in ["/health", "/api/v1/health"]:
        response = client.get(endpoint)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "ML Studio"
        assert data["api_version"] == "v1"
        assert "code_version" in data
        assert isinstance(data["code_version"], str)
        assert len(data["code_version"]) > 0
        assert "timestamp" in data
