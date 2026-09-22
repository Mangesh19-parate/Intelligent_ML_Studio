"""
Storage Service Facade (delegating to app.infrastructure.storage.object_store).
"""

from app.infrastructure.storage.object_store import (
    StorageService,
    LocalStorageService,
    S3StorageService,
    get_storage_service,
)

__all__ = [
    "StorageService",
    "LocalStorageService",
    "S3StorageService",
    "get_storage_service",
]
