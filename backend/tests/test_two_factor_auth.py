import json
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.core.totp import TOTPService
from app.models.user import User

def test_totp_rfc6238_generation_and_verification():
    secret = TOTPService.generate_secret()
    assert len(secret) >= 16

    code = TOTPService.generate_totp(secret)
    assert len(code) == 6
    assert code.isdigit()

    assert TOTPService.verify_totp(secret, code, drift_windows=1) is True
    assert TOTPService.verify_totp(secret, "999999" if code != "999999" else "000000", drift_windows=0) is False
    assert TOTPService.verify_totp(secret, "invalid", drift_windows=1) is False

def test_backup_codes_generation_and_consumption():
    plain, hashed = TOTPService.generate_backup_codes(count=8)
    assert len(plain) == 8
    assert len(hashed) == 8

    test_code = plain[0]
    valid, updated_hashes = TOTPService.verify_and_consume_backup_code(test_code, hashed)
    assert valid is True
    assert len(updated_hashes) == 7

    # Trying to reuse same code fails
    valid_again, _ = TOTPService.verify_and_consume_backup_code(test_code, updated_hashes)
    assert valid_again is False

def test_2fa_full_lifecycle(client: TestClient, db_session: Session):
    # 1. Create and login user
    signup_resp = client.post("/api/v1/auth/signup", json={
        "full_name": "Two Factor Tester",
        "email": "totp_tester@mlstudio.io",
        "password": "TestPassword123!"
    })
    assert signup_resp.status_code == 201

    login_resp = client.post("/api/v1/auth/login", json={
        "email": "totp_tester@mlstudio.io",
        "password": "TestPassword123!"
    })
    assert login_resp.status_code == 200
    token_data = login_resp.json()
    assert token_data["requires_2fa"] is False
    access_token = token_data["access_token"]
    auth_headers = {"Authorization": f"Bearer {access_token}"}

    # 2. Check 2FA Status (Initially Disabled)
    status_resp = client.get("/api/v1/auth/2fa/status", headers=auth_headers)
    assert status_resp.status_code == 200
    assert status_resp.json()["is_two_factor_enabled"] is False

    # 3. Initialize 2FA Setup
    setup_resp = client.post("/api/v1/auth/2fa/setup", headers=auth_headers)
    assert setup_resp.status_code == 200
    setup_data = setup_resp.json()
    secret = setup_data["secret"]
    backup_codes = setup_data["backup_codes"]
    assert "otpauth://" in setup_data["otpauth_url"]
    assert len(backup_codes) == 8

    # 4. Attempt confirmation with invalid code -> 400
    bad_confirm = client.post("/api/v1/auth/2fa/confirm", headers=auth_headers, json={
        "secret": secret,
        "code": "000000",
        "backup_codes": backup_codes,
    })
    assert bad_confirm.status_code == 400

    # 5. Confirm with valid code -> 200
    valid_code = TOTPService.generate_totp(secret)
    good_confirm = client.post("/api/v1/auth/2fa/confirm", headers=auth_headers, json={
        "secret": secret,
        "code": valid_code,
        "backup_codes": backup_codes,
    })
    assert good_confirm.status_code == 200

    # 6. Verify 2FA is now enabled
    status_resp = client.get("/api/v1/auth/2fa/status", headers=auth_headers)
    assert status_resp.status_code == 200
    assert status_resp.json()["is_two_factor_enabled"] is True
    assert status_resp.json()["remaining_backup_codes"] == 8

    # 7. Attempt Login -> Should trigger 2FA challenge gate
    challenge_login = client.post("/api/v1/auth/login", json={
        "email": "totp_tester@mlstudio.io",
        "password": "TestPassword123!"
    })
    assert challenge_login.status_code == 200
    challenge_data = challenge_login.json()
    assert challenge_data["requires_2fa"] is True
    two_factor_token = challenge_data["two_factor_token"]
    assert "access_token" not in challenge_data or challenge_data["access_token"] is None

    # 8. Verify with invalid code -> 401
    bad_verify = client.post("/api/v1/auth/2fa/verify-login", json={
        "two_factor_token": two_factor_token,
        "code": "111111",
    })
    assert bad_verify.status_code == 401

    # 9. Verify with valid TOTP code -> 200 and issues real access token
    current_totp = TOTPService.generate_totp(secret)
    good_verify = client.post("/api/v1/auth/2fa/verify-login", json={
        "two_factor_token": two_factor_token,
        "code": current_totp,
    })
    assert good_verify.status_code == 200
    assert "access_token" in good_verify.json()
    assert good_verify.json()["user"]["is_two_factor_enabled"] is True

    # 10. Test Login using Single-Use Emergency Recovery Backup Code
    challenge_login2 = client.post("/api/v1/auth/login", json={
        "email": "totp_tester@mlstudio.io",
        "password": "TestPassword123!"
    })
    t2_token = challenge_login2.json()["two_factor_token"]
    
    first_backup_code = backup_codes[0]
    backup_verify = client.post("/api/v1/auth/2fa/verify-login", json={
        "two_factor_token": t2_token,
        "code": first_backup_code,
    })
    assert backup_verify.status_code == 200
    new_auth_headers = {"Authorization": f"Bearer {backup_verify.json()['access_token']}"}

    # Verify backup code count decreased from 8 to 7
    status_resp2 = client.get("/api/v1/auth/2fa/status", headers=new_auth_headers)
    assert status_resp2.json()["remaining_backup_codes"] == 7

    # 11. Test Disabling 2FA
    disable_resp = client.post("/api/v1/auth/2fa/disable", headers=new_auth_headers, json={
        "password": "TestPassword123!",
        "code": TOTPService.generate_totp(secret),
    })
    assert disable_resp.status_code == 200

    # Verify 2FA is disabled and standard login works directly
    direct_login = client.post("/api/v1/auth/login", json={
        "email": "totp_tester@mlstudio.io",
        "password": "TestPassword123!"
    })
    assert direct_login.status_code == 200
    assert direct_login.json()["requires_2fa"] is False
    assert "access_token" in direct_login.json()
