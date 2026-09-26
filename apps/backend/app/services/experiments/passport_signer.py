"""
Model Passport & Cryptographic Signing Subsystem.
Computes artifact checksums and validates cryptographic integrity signatures.
"""

from typing import Any
import hashlib
import hmac
from app.core.config import settings


class ModelPassportSigner:
    """Manages cryptographic signatures and reproducibility manifests for trained models."""

    @staticmethod
    def generate_artifact_manifest(
        model_id: str,
        algorithm_name: str,
        hyperparameters: dict[str, Any],
        metrics: dict[str, float],
        dataset_hash: str,
        raw_artifact_bytes: bytes,
    ) -> dict[str, Any]:
        artifact_hash = hashlib.sha256(raw_artifact_bytes).hexdigest()
        signature_key = settings.SECRET_KEY.encode("utf-8")
        manifest_payload = f"{model_id}:{algorithm_name}:{dataset_hash}:{artifact_hash}"
        signature = hmac.new(signature_key, manifest_payload.encode("utf-8"), hashlib.sha256).hexdigest()

        return {
            "model_id": model_id,
            "algorithm_name": algorithm_name,
            "hyperparameters": hyperparameters,
            "metrics": metrics,
            "dataset_hash": dataset_hash,
            "artifact_hash": artifact_hash,
            "hmac_signature": signature,
        }

    @staticmethod
    def verify_manifest_signature(manifest: dict[str, Any]) -> bool:
        model_id = manifest.get("model_id", "")
        algorithm_name = manifest.get("algorithm_name", "")
        dataset_hash = manifest.get("dataset_hash", "")
        artifact_hash = manifest.get("artifact_hash", "")
        provided_signature = manifest.get("hmac_signature", "")

        signature_key = settings.SECRET_KEY.encode("utf-8")
        manifest_payload = f"{model_id}:{algorithm_name}:{dataset_hash}:{artifact_hash}"
        expected_signature = hmac.new(signature_key, manifest_payload.encode("utf-8"), hashlib.sha256).hexdigest()

        return hmac.compare_digest(expected_signature, provided_signature)
