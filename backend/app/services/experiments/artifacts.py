"""
Artifact Management & Cryptographic Signing Module for Experiments.

Provides serialization, SHA-256 verification, and HMAC-signed manifests.
"""

from pathlib import Path
from typing import Any
from uuid import UUID
from app.core.artifact_signing import (
    save_signed_model_artifact,
    verify_and_load_model_artifact,
    calculate_file_sha256,
)


def persist_experiment_model_artifact(
    model_object: Any,
    storage_dir: Path,
    model_id: UUID | str,
    metadata: dict[str, Any] | None = None,
) -> tuple[Path, str, str]:
    """
    Saves and HMAC-signs a trained model artifact to storage.
    Returns (artifact_path, sha256_checksum, hmac_signature).
    """
    storage_dir.mkdir(parents=True, exist_ok=True)
    target_path = storage_dir / f"model_{model_id}.joblib"

    manifest = save_signed_model_artifact(
        artifact_path=target_path,
        model_object=model_object,
        model_id=str(model_id),
        metadata=metadata or {},
    )

    return target_path, manifest["artifact_sha256"], manifest["signature"]


def load_verified_model_artifact(artifact_path: Path | str) -> Any:
    """
    Verifies digital signature & SHA-256 checksum, then safely unpickles artifact.
    """
    return verify_and_load_model_artifact(artifact_path)
