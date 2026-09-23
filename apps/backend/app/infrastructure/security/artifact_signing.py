"""
Cryptographic Artifact Manifest & Signature Verification.
Prevents arbitrary or untrusted model deserialization by requiring a valid HMAC-SHA256
signature alongside SHA-256 hash before loading any model artifact.
Strict key isolation: requires ARTIFACT_SIGNING_KEY (no JWT_SECRET fallback).
"""

import os
import tempfile
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
    if not signing_secret:
        raise SecurityError("ARTIFACT_SIGNING_KEY is not configured on this host.")
    return hmac.new(
        signing_secret.encode("utf-8"),
        content_sha256.encode("utf-8"),
        hashlib.sha256
    ).hexdigest()


def sign_artifact_manifest(manifest_payload: str, secret_key: str | None = None) -> str:
    """Computes HMAC-SHA256 signature for a manifest payload string."""
    key = secret_key or settings.ARTIFACT_SIGNING_KEY
    if not key:
        raise SecurityError("ARTIFACT_SIGNING_KEY is not configured on this host.")
    return hmac.new(key.encode("utf-8"), manifest_payload.encode("utf-8"), hashlib.sha256).hexdigest()


def verify_artifact_manifest(manifest_payload: str, expected_signature: str, secret_key: str | None = None) -> bool:
    """Constant-time verification of artifact manifest signature."""
    actual_signature = sign_artifact_manifest(manifest_payload, secret_key)
    return hmac.compare_digest(actual_signature, expected_signature)


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
            f"Artifact integrity check failed: SHA-256 checksum mismatch. Artifact integrity violation for {path.name} (expected {expected_hash}, got {actual_hash})"
        )

    computed_sig = compute_hmac_signature(actual_hash, secret)
    if not hmac.compare_digest(computed_sig, expected_sig):
        raise SecurityError(
            f"Artifact signature violation: Unauthorized or tampered model artifact {path.name}."
        )

    return joblib.load(path)


import io
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from app.infrastructure.storage.object_store import StorageService

def save_signed_model_to_storage(
    artifact: Any,
    storage_key: str,
    storage: Any | None = None,
    secret: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> tuple[str, str, str]:
    """
    Serializes a model artifact and stores both the model binary and HMAC manifest
    into the configured StorageService (Local or S3/R2).
    Returns (storage_key_or_path, sha256_hash, hmac_signature).
    """
    from app.infrastructure.storage.object_store import get_storage_service
    storage_svc = storage or get_storage_service()

    # 1. Serialize using temporary file to maintain joblib compatibility with path-based hooks and mocks
    clean_key = storage_key.replace("\\", "/").lstrip("/")
    with tempfile.NamedTemporaryFile(suffix=".joblib", delete=False) as tmp_f:
        tmp_name = tmp_f.name
    try:
        joblib.dump(artifact, tmp_name)
        with open(tmp_name, "rb") as f:
            model_bytes = f.read()
    finally:
        if os.path.exists(tmp_name):
            try:
                os.remove(tmp_name)
            except Exception:
                pass

    # 2. Compute SHA-256 and HMAC
    file_hash = hashlib.sha256(model_bytes).hexdigest()
    signature = compute_hmac_signature(file_hash, secret)

    # 3. Save model binary to storage
    _ = storage_svc.save_bytes(clean_key, model_bytes)

    # 4. Save manifest to storage
    manifest_key = str(Path(clean_key).with_suffix(".manifest.json")).replace("\\", "/")
    manifest_data = {
        "artifact_file": Path(clean_key).name,
        "sha256": file_hash,
        "signature": signature,
        "signed_at": datetime.now(timezone.utc).isoformat(),
        "metadata": metadata or {},
    }
    manifest_bytes = json.dumps(manifest_data, indent=2).encode("utf-8")
    storage_svc.save_bytes(manifest_key, manifest_bytes)

    try:
        actual_path = storage_svc.get_file_path(clean_key)
    except Exception:
        actual_path = clean_key

    return actual_path, file_hash, signature


def load_signed_model_from_storage(
    storage_key: str,
    storage: Any | None = None,
    secret: str | None = None,
    allow_unsigned_fixtures: bool = False,
) -> Any:
    """
    Loads and cryptographically verifies a model artifact from StorageService (Local or S3).
    Ensures both the model binary and manifest are retrieved and authenticated before deserialization.
    """
    from app.infrastructure.storage.object_store import get_storage_service
    storage_svc = storage or get_storage_service()

    # If storage_key exists directly on local disk, verify and load it directly
    if Path(storage_key).exists():
        return verify_and_load_model_artifact(
            storage_key,
            secret=secret,
            allow_unsigned_fixtures=allow_unsigned_fixtures
        )

    clean_key = storage_key.replace("\\", "/").lstrip("/")
    manifest_key = str(Path(clean_key).with_suffix(".manifest.json")).replace("\\", "/")

    # Ensure local path is cached and accessible for both manifest and model
    try:
        _ = storage_svc.get_file_path(manifest_key)
    except Exception:
        pass

    model_local_path = storage_svc.get_file_path(clean_key)
    return verify_and_load_model_artifact(
        model_local_path,
        secret=secret,
        allow_unsigned_fixtures=allow_unsigned_fixtures
    )


def load_dev_fixture_artifact(file_path: Path | str) -> Any:
    """Explicit loader helper strictly reserved for development fixtures / testing."""
    return verify_and_load_model_artifact(file_path, allow_unsigned_fixtures=True)

