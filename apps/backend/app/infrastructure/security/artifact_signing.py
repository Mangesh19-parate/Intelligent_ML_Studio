"""
HMAC-SHA256 Model Artifact Signing & Manifest Verification.
"""

import hmac
import hashlib
from typing import Any
from app.core.config import settings


def sign_artifact_manifest(manifest_payload: str, secret_key: str | None = None) -> str:
    """Computes HMAC-SHA256 signature for a manifest payload string."""
    key = (secret_key or settings.ARTIFACT_SIGNING_KEY or settings.JWT_SECRET).encode("utf-8")
    return hmac.new(key, manifest_payload.encode("utf-8"), hashlib.sha256).hexdigest()


def verify_artifact_manifest(manifest_payload: str, expected_signature: str, secret_key: str | None = None) -> bool:
    """Constant-time verification of artifact manifest signature."""
    actual_signature = sign_artifact_manifest(manifest_payload, secret_key)
    return hmac.compare_digest(actual_signature, expected_signature)
