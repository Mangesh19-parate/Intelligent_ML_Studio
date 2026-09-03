import os
import shutil
from abc import ABC, abstractmethod
from pathlib import Path
from typing import BinaryIO
from uuid import UUID
from app.core.config import settings

class StorageService(ABC):
    """
    Abstract interface for object storage.
    Enables drop-in replacement with S3/GCS/Azure Blob storage later.
    """

    @abstractmethod
    def save_file(self, project_id: str | UUID, version: int, filename: str, content: bytes) -> str:
        """
        Saves file bytes to object storage.
        Returns the canonical storage path identifier.
        """
        pass

    @abstractmethod
    def get_file_bytes(self, storage_path: str) -> bytes:
        """
        Reads and returns raw file bytes.
        """
        pass

    @abstractmethod
    def get_file_path(self, storage_path: str) -> str:
        """
        Returns local filesystem path or local temporary cache path accessible to pandas/readers.
        """
        pass

    @abstractmethod
    def delete_file(self, storage_path: str) -> bool:
        """
        Deletes the file from storage.
        """
        pass

    @abstractmethod
    def exists(self, storage_path: str) -> bool:
        """
        Checks if file exists in storage.
        """
        pass


class LocalStorageService(StorageService):
    """
    Local filesystem implementation of StorageService.
    Stores files at: {STORAGE_LOCAL_DIR}/datasets/{project_id}/{version}/{filename}
    """

    def __init__(self, base_dir: str | None = None) -> None:
        self.base_dir = Path(base_dir or settings.STORAGE_LOCAL_DIR).resolve()

    def _resolve_dataset_dir(self, project_id: str | UUID, version: int) -> Path:
        target_dir = self.base_dir / "datasets" / str(project_id) / str(version)
        target_dir.mkdir(parents=True, exist_ok=True)
        return target_dir

    def save_file(self, project_id: str | UUID, version: int, filename: str, content: bytes) -> str:
        target_dir = self._resolve_dataset_dir(project_id, version)
        # Sanitize filename to prevent directory traversal
        safe_filename = Path(filename).name
        target_file = target_dir / safe_filename
        
        with open(target_file, "wb") as f:
            f.write(content)
            
        # Return path relative to base_dir or standard storage URI
        return str(target_file)

    def get_file_bytes(self, storage_path: str) -> bytes:
        path = Path(storage_path)
        if not path.is_absolute():
            path = (self.base_dir / storage_path).resolve()
            
        if not path.exists():
            raise FileNotFoundError(f"Storage object not found at: {storage_path}")
            
        with open(path, "rb") as f:
            return f.read()

    def get_file_path(self, storage_path: str) -> str:
        path = Path(storage_path)
        if not path.is_absolute():
            path = (self.base_dir / storage_path).resolve()
            
        if not path.exists():
            raise FileNotFoundError(f"Storage object not found at: {storage_path}")
            
        return str(path)

    def delete_file(self, storage_path: str) -> bool:
        path = Path(storage_path)
        if not path.is_absolute():
            path = (self.base_dir / storage_path).resolve()
            
        if path.exists():
            path.unlink()
            return True
        return False

    def exists(self, storage_path: str) -> bool:
        path = Path(storage_path)
        if not path.is_absolute():
            path = (self.base_dir / storage_path).resolve()
        return path.exists()


_storage_instance: StorageService | None = None

def get_storage_service() -> StorageService:
    global _storage_instance
    if _storage_instance is None:
        _storage_instance = LocalStorageService()
    return _storage_instance
