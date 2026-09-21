import hmac
import hashlib
import struct
import time
import base64
import secrets
import urllib.parse
from typing import List, Tuple

class TOTPService:
    """
    Standard RFC 6238 Time-Based One-Time Password (TOTP) and HMAC-SHA1 Engine.
    Zero external dependencies — implemented via Python standard library.
    Compatible with Google Authenticator, Microsoft Authenticator, 1Password, Authy, Apple Keychain.
    """

    TIME_STEP: int = 30
    DIGITS: int = 6
    ALGORITHM: str = "SHA1"

    @classmethod
    def generate_secret(cls, length: int = 20) -> str:
        """Generates a secure cryptographically random Base32 secret key."""
        random_bytes = secrets.token_bytes(length)
        return base64.b32encode(random_bytes).decode("utf-8").replace("=", "")

    @classmethod
    def _normalize_secret(cls, secret: str) -> bytes:
        """Decodes a Base32 secret key, padding with '=' if necessary."""
        secret_clean = secret.strip().replace(" ", "").upper()
        missing_padding = len(secret_clean) % 8
        if missing_padding:
            secret_clean += "=" * (8 - missing_padding)
        return base64.b32decode(secret_clean)

    @classmethod
    def generate_totp(cls, secret: str, for_time: float | None = None) -> str:
        """Generates the 6-digit TOTP code for a given timestamp."""
        current_time = for_time if for_time is not None else time.time()
        time_counter = int(current_time // cls.TIME_STEP)
        
        # Pack counter into 8-byte big-endian integer
        counter_bytes = struct.pack(">Q", time_counter)
        key_bytes = cls._normalize_secret(secret)
        
        # HMAC-SHA1 computation
        h = hmac.new(key_bytes, counter_bytes, hashlib.sha1).digest()
        
        # Dynamic truncation (RFC 4226 §5.4)
        offset = h[-1] & 0x0F
        truncated_hash = (
            ((h[offset] & 0x7F) << 24)
            | ((h[offset + 1] & 0xFF) << 16)
            | ((h[offset + 2] & 0xFF) << 8)
            | (h[offset + 3] & 0xFF)
        )
        
        otp = truncated_hash % (10 ** cls.DIGITS)
        return str(otp).zfill(cls.DIGITS)

    @classmethod
    def verify_totp(cls, secret: str, code: str, drift_windows: int = 1) -> bool:
        """
        Verifies a 6-digit TOTP code with time drift tolerance.
        drift_windows=1 checks [t-30s, t, t+30s] to accommodate clock skew.
        """
        code_clean = str(code).strip().replace(" ", "").replace("-", "")
        if not code_clean.isdigit() or len(code_clean) != cls.DIGITS:
            return False

        current_time = time.time()
        for window in range(-drift_windows, drift_windows + 1):
            check_time = current_time + (window * cls.TIME_STEP)
            valid_code = cls.generate_totp(secret, for_time=check_time)
            if hmac.compare_digest(valid_code, code_clean):
                return True
        return False

    @classmethod
    def generate_otpauth_uri(
        cls,
        secret: str,
        account_name: str,
        issuer: str = "IntelligentMLStudio"
    ) -> str:
        """
        Generates standard otpauth:// URI for QR code scanning in authenticator apps.
        Format: otpauth://totp/{Issuer}:{AccountName}?secret={Secret}&issuer={Issuer}&algorithm=SHA1&digits=6&period=30
        """
        label = f"{issuer}:{account_name}"
        params = {
            "secret": secret.strip().replace(" ", "").upper(),
            "issuer": issuer,
            "algorithm": cls.ALGORITHM,
            "digits": str(cls.DIGITS),
            "period": str(cls.TIME_STEP),
        }
        query_string = urllib.parse.urlencode(params)
        return f"otpauth://totp/{urllib.parse.quote(label)}?{query_string}"

    @classmethod
    def generate_backup_codes(cls, count: int = 8) -> Tuple[List[str], List[str]]:
        """
        Generates random single-use recovery backup codes.
        Returns:
            - plain_codes: List of formatted strings (e.g. 'ABCD-1234') to display once to user.
            - hashed_codes: List of SHA-256 hashes to store securely in database.
        """
        alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # High-contrast, no confusing 0/O/1/I
        plain_codes = []
        hashed_codes = []
        
        for _ in range(count):
            part1 = "".join(secrets.choice(alphabet) for _ in range(4))
            part2 = "".join(secrets.choice(alphabet) for _ in range(4))
            raw_code = f"{part1}-{part2}"
            plain_codes.append(raw_code)
            
            # Hash code for storage
            clean_code = raw_code.replace("-", "").upper()
            code_hash = hashlib.sha256(clean_code.encode("utf-8")).hexdigest()
            hashed_codes.append(code_hash)
            
        return plain_codes, hashed_codes

    @classmethod
    def verify_and_consume_backup_code(cls, code: str, hashed_codes: List[str]) -> Tuple[bool, List[str]]:
        """
        Verifies if an entered recovery code matches any unused hashed code.
        If valid, consumes the code and returns (True, updated_hashed_codes).
        """
        clean_code = str(code).strip().replace(" ", "").replace("-", "").upper()
        if not clean_code:
            return False, hashed_codes

        input_hash = hashlib.sha256(clean_code.encode("utf-8")).hexdigest()
        
        for idx, h in enumerate(hashed_codes):
            if hmac.compare_digest(h, input_hash):
                # Consume this code by removing it from the list
                remaining_hashes = hashed_codes[:idx] + hashed_codes[idx+1:]
                return True, remaining_hashes
                
        return False, hashed_codes
