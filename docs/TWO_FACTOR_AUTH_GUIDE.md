# Two-Factor Authentication (2FA) with OTP — Developer's Guide

## 1. Introduction & Security Rationale
Authentication confirms a user's digital identity. Traditional username/password schemes have single-point-of-failure vulnerabilities (credential stuffing, database breaches, weak password reuse, and phishing).

**Two-Factor Authentication (2FA)** mitigates these risks by enforcing two distinct, orthogonal categories:
- **Something you know**: Password, PIN.
- **Something you have**: Authenticator app (TOTP), SMS/Email OTP, hardware key (YubiKey).

```
User enters username + password
                ↓
    Server verifies credentials
                ↓
           Generate OTP
                ↓
 Send OTP to user's second factor
                ↓
         User enters OTP
                ↓
       Server verifies OTP
                ↓
   Issue Authenticated Session (JWT)
```

---

## 2. Comparison: SMS OTP vs. Authenticator Apps (TOTP)

| Feature | SMS OTP | Authenticator App (TOTP - RFC 6238) |
|---|---|---|
| **Delivery Network** | Cellular carrier network | Offline mathematical algorithm (HMAC-SHA1) |
| **Internet Requirement** | Required for SMS delivery | None (works completely offline) |
| **SIM-Swap Risk** | High (telecom interception) | Low (tied directly to hardware secret) |
| **Setup Friction** | Low (phone number only) | Moderate (QR code scan / secret key) |
| **Enterprise Standard** | Consumer banking/retail | Developer platforms, cloud infrastructure, ML studio |

---

## 3. Production Security Checklist

- [x] **Server-Side Generation**: OTP calculation, cryptographic secret storage, and comparison must strictly occur on the backend. Never expose OTPs in frontend logs or client-side variables.
- [x] **Single-Use & Fast Expiration**: OTP tokens must be single-use and expire within a short window (30 seconds for TOTP; 5–10 minutes for SMS/Email).
- [x] **Rate Limiting & Anti-Brute-Force**: Enforce maximum failed verification attempts (e.g., max 3–5 attempts) before locking the challenge token.
- [x] **Single-Use Backup Recovery Codes**: Provide single-use hashed recovery keys in case the physical authenticator device is lost.
- [x] **PII Masking**: Mask phone numbers (`•••••••••• 4821`) and email addresses on challenge screens.
- [x] **Transport Layer Security**: HTTPS enforcement across all auth endpoints to prevent token sniffing.

---

## 4. Architecture Pattern in ML Studio

1. **First-Factor Verification (`POST /api/v1/auth/login`)**:
   - Compares password hash via `argon2` or `bcrypt`.
   - If 2FA is active, returns a short-lived, low-privilege `two_factor_token` rather than a full platform access token.
2. **Second-Factor Verification (`POST /api/v1/auth/2fa/verify-login`)**:
   - Validates the 6-digit rolling code against the user's stored `two_factor_secret` via RFC 6238 TOTP window ($\pm 1$ period).
   - Only on success issues the long-lived `access_token` and `refresh_token`.
3. **Deactivation Safety (`POST /api/v1/auth/2fa/disable`)**:
   - Requires both the user's account password and a valid current OTP code to prevent unauthorized security removal.
