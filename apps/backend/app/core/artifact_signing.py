"""
Cryptographic Artifact Manifest & Signature Verification Facade.
Canonical implementation located in app.infrastructure.security.artifact_signing.
"""

from app.infrastructure.security.artifact_signing import (
    SecurityError,
    compute_file_sha256,
    compute_hmac_signature,
    sign_artifact_manifest,
    verify_artifact_manifest,
    save_signed_model_artifact,
    verify_and_load_model_artifact,
    load_dev_fixture_artifact,
)

__all__ = [
    "SecurityError",
    "compute_file_sha256",
    "compute_hmac_signature",
    "sign_artifact_manifest",
    "verify_artifact_manifest",
    "save_signed_model_artifact",
    "verify_and_load_model_artifact",
    "load_dev_fixture_artifact",
]
