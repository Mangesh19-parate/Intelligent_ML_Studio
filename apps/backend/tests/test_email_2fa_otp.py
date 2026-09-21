import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.services.email_service import EmailService
from app.models.user import User

def test_email_service_validation():
    """Test EmailService email format validation."""
    assert EmailService.is_valid_email("user@example.com") is True
    assert EmailService.is_valid_email("dev.engineer+tag@mlstudio.io") is True
    assert EmailService.is_valid_email("invalid-email") is False
    assert EmailService.is_valid_email("missing_at.domain.com") is False
    assert EmailService.is_valid_email("user@.com") is False
    assert EmailService.is_valid_email("user@domain") is False
    assert EmailService.is_valid_email("") is False
    assert EmailService.is_valid_email(None) is False

def test_email_service_masking():
    """Test EmailService email address masking for UI privacy."""
    assert EmailService.mask_email("dev@mlstudio.io") == "d***v@mlstudio.io"
    assert EmailService.mask_email("john.doe@company.org") == "j***e@company.org"

def test_email_service_otp_generation():
    """Test 6-digit numeric OTP generation."""
    for _ in range(20):
        otp = EmailService.generate_otp(digits=6)
        assert len(otp) == 6
        assert otp.isdigit()
        assert 100000 <= int(otp) <= 999999

def test_email_2fa_signup_validation_rejection(client: TestClient):
    """Test that signup rejects invalid email formats with 422."""
    resp = client.post("/api/v1/auth/signup", json={
        "full_name": "Invalid Email User",
        "email": "not-an-email",
        "password": "Password123!"
    })
    assert resp.status_code == 422

def test_email_2fa_full_login_resend_and_logout_flow(client: TestClient, db_session: Session):
    """
    Test Email 2FA Flow:
    1. Register user with valid email
    2. Activate 2FA on user
    3. Login triggers 2FA challenge and dispatches 6-digit email OTP
    4. Resend OTP issues fresh 6-digit code to registered email
    5. Verify with email OTP completes sign in without QR code
    6. User logs out and signs in again -> 2FA email OTP is prompted again
    """
    # 1. Register user
    signup_resp = client.post("/api/v1/auth/signup", json={
        "full_name": "Security Pro",
        "email": "security_pro@mlstudio.io",
        "password": "StrongPassword123!"
    })
    assert signup_resp.status_code == 201
    user_id = signup_resp.json()["id"]
    import uuid
    user_uuid = uuid.UUID(str(user_id))

    # Directly enable 2FA on the user record in DB
    user = db_session.query(User).filter(User.id == user_uuid).first()
    user.is_two_factor_enabled = True
    db_session.commit()

    # 2. Login -> Triggers Email 2FA challenge
    login_resp = client.post("/api/v1/auth/login", json={
        "email": "security_pro@mlstudio.io",
        "password": "StrongPassword123!"
    })
    assert login_resp.status_code == 200
    login_data = login_resp.json()
    assert login_data["requires_2fa"] is True
    assert login_data["two_factor_token"] is not None
    assert "email_masked" in login_data
    two_factor_token = login_data["two_factor_token"]

    # Extract the generated OTP from user state to simulate user receiving email
    db_session.refresh(user)
    import json
    secret_data = json.loads(user.two_factor_secret)
    assert secret_data["type"] == "email_otp"

    # 3. Test Resend OTP endpoint
    resend_resp = client.post("/api/v1/auth/2fa/resend", json={
        "two_factor_token": two_factor_token
    })
    assert resend_resp.status_code == 200
    assert "new" in resend_resp.json()["message"].lower() or "sent" in resend_resp.json()["message"].lower()

    # Check updated OTP from resend
    db_session.refresh(user)
    new_secret_data = json.loads(user.two_factor_secret)
    otp_hash = new_secret_data["otp_hash"]

    # 4. Verify login using wrong code -> 401
    bad_verify = client.post("/api/v1/auth/2fa/verify-login", json={
        "two_factor_token": two_factor_token,
        "code": "000000"
    })
    assert bad_verify.status_code == 401

    # To verify valid login, let's find the matching OTP or test verification
    # We can test by calling resend or testing with known OTP
    import hashlib
    test_otp = "456789"
    user.two_factor_secret = json.dumps({
        "type": "email_otp",
        "otp_hash": hashlib.sha256(test_otp.encode("utf-8")).hexdigest(),
        "expires_at": 9999999999,
        "totp_secret": None
    })
    db_session.commit()

    good_verify = client.post("/api/v1/auth/2fa/verify-login", json={
        "two_factor_token": two_factor_token,
        "code": test_otp
    })
    assert good_verify.status_code == 200
    token_resp = good_verify.json()
    assert "access_token" in token_resp
    assert token_resp["user"]["email"] == "security_pro@mlstudio.io"

    # 5. User logs out
    auth_header = {"Authorization": f"Bearer {token_resp['access_token']}"}
    logout_resp = client.post("/api/v1/auth/logout", headers=auth_header)
    assert logout_resp.status_code == 200

    # 6. User signs in again -> 2FA challenge is prompted again
    relogin_resp = client.post("/api/v1/auth/login", json={
        "email": "security_pro@mlstudio.io",
        "password": "StrongPassword123!"
    })
    assert relogin_resp.status_code == 200
    assert relogin_resp.json()["requires_2fa"] is True
