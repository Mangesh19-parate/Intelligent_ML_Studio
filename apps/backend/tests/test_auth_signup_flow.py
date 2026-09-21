"""
Unit & Integration tests for Day 3 Auth + Signup + Login endpoints.
Validates:
- POST /api/v1/auth/signup hardcoding role='USER'
- Rejection (HTTP 400) of any signup request containing 'role' or 'role_name'
- Successful login with JWT generation
"""

import pytest
from fastapi.testclient import TestClient


def test_signup_successful(client: TestClient, db_session):
    """POST /api/v1/auth/signup successfully registers a user with role='USER'."""
    signup_payload = {
        "full_name": "Test User",
        "email": "signup_standard@example.com",
        "password": "strongpassword123",
    }
    response = client.post("/api/v1/auth/signup", json=signup_payload)
    assert response.status_code == 201, response.text
    data = response.json()
    assert data["email"] == "signup_standard@example.com"
    assert data["full_name"] == "Test User"
    assert data["role"]["role_name"] == "USER"
    assert "READ" in data["permissions"]


def test_signup_rejects_role_field_with_400(client: TestClient, db_session):
    """POST /api/v1/auth/signup rejects requests containing a 'role' key with HTTP 400."""
    payload_with_role = {
        "full_name": "Privilege Escalation Attempt",
        "email": "escalate@example.com",
        "password": "password123",
        "role": "ADMIN",
    }
    response = client.post("/api/v1/auth/signup", json=payload_with_role)
    assert response.status_code == 400
    assert "role" in response.json()["detail"].lower()


def test_signup_rejects_role_name_field_with_400(client: TestClient, db_session):
    """POST /api/v1/auth/signup rejects requests containing a 'role_name' key with HTTP 400."""
    payload_with_role_name = {
        "full_name": "Another Escalation Attempt",
        "email": "escalate2@example.com",
        "password": "password123",
        "role_name": "ADMIN",
    }
    response = client.post("/api/v1/auth/signup", json=payload_with_role_name)
    assert response.status_code == 400
    assert "role" in response.json()["detail"].lower()


def test_signup_duplicate_email_rejected(client: TestClient, db_session):
    """POST /api/v1/auth/signup rejects duplicate email with HTTP 400."""
    payload = {
        "full_name": "Duplicate User",
        "email": "duplicate@example.com",
        "password": "password123",
    }
    res1 = client.post("/api/v1/auth/signup", json=payload)
    assert res1.status_code == 201
    
    res2 = client.post("/api/v1/auth/signup", json=payload)
    assert res2.status_code == 400
    assert "already exists" in res2.json()["detail"].lower()


def test_login_successful_and_jwt_verification(client: TestClient, db_session):
    """POST /api/v1/auth/login authenticates registered users and returns valid JWT tokens."""
    signup_payload = {
        "full_name": "Login Tester",
        "email": "login_tester@example.com",
        "password": "mypassword123",
    }
    client.post("/api/v1/auth/signup", json=signup_payload)

    login_payload = {
        "email": "login_tester@example.com",
        "password": "mypassword123",
    }
    response = client.post("/api/v1/auth/login", json=login_payload)
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == "login_tester@example.com"
    assert data["user"]["role"]["role_name"] == "USER"


def test_login_invalid_credentials(client: TestClient, db_session):
    """POST /api/v1/auth/login returns HTTP 401 on incorrect password."""
    login_payload = {
        "email": "login_tester@example.com",
        "password": "wrongpassword",
    }
    response = client.post("/api/v1/auth/login", json=login_payload)
    assert response.status_code == 401
