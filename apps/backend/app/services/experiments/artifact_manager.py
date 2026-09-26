import logging
import hashlib
from typing import Any
from app.infrastructure.storage.object_store import StorageService, get_storage_service

logger = logging.getLogger(__name__)

# Scavenger registry tracking orphaned artifacts where immediate deletion failed (Day 3 P0)
ORPHANED_RECOVERABLE_REGISTRY: set[str] = set()


def get_orphaned_recoverable_registry() -> set[str]:
    """Returns the set of artifact file paths marked as ORPHANED_RECOVERABLE."""
    return ORPHANED_RECOVERABLE_REGISTRY


def clear_orphaned_recoverable_registry() -> None:
    """Clears the in-memory scavenger registry (useful in test teardown)."""
    ORPHANED_RECOVERABLE_REGISTRY.clear()


class ExperimentArtifactManager:
    """
    Manages artifact serialization, storage uploads, checksumming, and scavenger cleanup for experiments.
    """

    def __init__(self, storage: StorageService | None = None):
        self.storage = storage or get_storage_service()

    def record_orphan_artifact(self, path: str) -> None:
        """Registers an artifact path into the scavenger registry for deferred cleanup."""
        ORPHANED_RECOVERABLE_REGISTRY.add(path)
        logger.warning(f"Artifact {path} registered in ORPHANED_RECOVERABLE_REGISTRY for scavenger reclamation.")

    def compute_sha256(self, file_bytes: bytes) -> str:
        """Computes deterministic SHA-256 hash of byte payload."""
        return hashlib.sha256(file_bytes).hexdigest()
