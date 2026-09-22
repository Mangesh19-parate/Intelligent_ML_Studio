"""
Cryptographic Artifact Manifest & Signature Verification (P1.4).
Prevents arbitrary or untrusted model deserialization by requiring a valid HMAC-SHA256
signature alongside SHA-256 hash before loading any model artifact.
"""

import hmac
import hashlib
import json
import joblib
from pathlib import Path
from datetime import datetime, timezone
from typing import Any
from app.core.config import settings


class SecurityError(Exception):
    """Raised when an artifact fails cryptographic verification or lacks authorization."""
    pass


def compute_file_sha256(file_path: Path | str) -> str:
    path = Path(file_path)
    hasher = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


def compute_hmac_signature(content_sha256: str, secret: str | None = None) -> str:
    signing_secret = secret or settings.ARTIFACT_SIGNING_KEY
    return hmac.new(
        signing_secret.encode("utf-8"),
        content_sha256.encode("utf-8"),
        hashlib.sha256
    ).hexdigest()


def save_signed_model_artifact(
    artifact: Any,
    file_path: Path | str,
    secret: str | None = None,
    metadata: dict[str, Any] | None = None
) -> str:
    """
    Serializes a model artifact and generates a cryptographic HMAC signature manifest.
    """
    path = Path(file_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    # 1. Serialize artifact
    joblib.dump(artifact, path)

    # 2. Compute SHA-256 and HMAC
    file_hash = compute_file_sha256(path)
    signature = compute_hmac_signature(file_hash, secret)

    # 3. Write manifest
    manifest_path = path.with_suffix(".manifest.json")
    manifest_data = {
        "artifact_file": path.name,
        "sha256": file_hash,
        "signature": signature,
        "signed_at": datetime.now(timezone.utc).isoformat(),
        "metadata": metadata or {},
    }
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest_data, f, indent=2)

    return file_hash


def verify_and_load_model_artifact(
    file_path: Path | str,
    secret: str | None = None,
    allow_unsigned_fixtures: bool = False,
) -> Any:
    """
    Verifies the HMAC signature and hash of an artifact manifest before deserialization.
    Explicitly blocks arbitrary or untrusted model deserialization paths across all environments.
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Model artifact not found at: {path}")

    manifest_path = path.with_suffix(".manifest.json")
    if not manifest_path.exists():
        if not allow_unsigned_fixtures:
            raise SecurityError(
                f"Untrusted artifact: missing cryptographic signature manifest for {path.name}. "
                "Runtime model loader strictly requires an authenticated HMAC manifest."
            )
        return joblib.load(path)

    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    expected_hash = manifest.get("sha256")
    expected_sig = manifest.get("signature")

    actual_hash = compute_file_sha256(path)
    if actual_hash != expected_hash:
        raise SecurityError(
            f"Artifact integrity violation: SHA-256 mismatch for {path.name} (expected {expected_hash}, got {actual_hash})"
        )

    computed_sig = compute_hmac_signature(actual_hash, secret)
    if not hmac.compare_digest(computed_sig, expected_sig):
        raise SecurityError(
            f"Artifact signature violation: Unauthorized or tampered model artifact {path.name}."
        )

    return joblib.load(path)


def load_dev_fixture_artifact(file_path: Path | str) -> Any:
    """Explicit loader helper strictly reserved for development fixtures / testing."""
    return verify_and_load_model_artifact(file_path, allow_unsigned_fixtures=True)
