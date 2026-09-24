"""
Shared Object Storage Layer for ML Studio (S3-Compatible and Local Filesystem).
Enables seamless multi-service execution (Render Web API + Render ML Worker)
with shared object keys (e.g. datasets/project-id/v1/data.parquet, models/model-id/model.joblib).
"""

import os
import io
import tempfile
import logging
from abc import ABC, abstractmethod
from pathlib import Path
from uuid import UUID
from app.core.config import settings

logger = logging.getLogger("ml_studio.storage")


class StorageError(Exception):
    """Base exception for all storage layer failures."""
    pass


class ObjectNotFoundError(StorageError, FileNotFoundError):
    """Raised when an object key does not exist in storage (maps to HTTP 404)."""
    pass


class StorageUnavailableError(StorageError):
    """Raised on connection timeout, network failure, or S3 outage (maps to HTTP 503)."""
    pass


class StoragePermissionDeniedError(StorageError, PermissionError):
    """Raised when credentials are unauthorized or lack bucket access (maps to HTTP 500/502)."""
    pass


class StorageTimeoutError(StorageError, TimeoutError):
    """Raised when an object storage operation exceeds timeout threshold."""
    pass


class StorageConfigurationError(StorageError):
    """Raised when object store is misconfigured or required client libraries are missing."""
    pass


class StorageService(ABC):
    """
    Abstract interface for shared object storage.
    Enables drop-in switching between Local and S3/MinIO/Cloudflare R2 storage.
    """

    @abstractmethod
    def save_file(self, project_id: str | UUID, version: int, filename: str, content: bytes) -> str:
        """Saves dataset/model file bytes and returns canonical relative storage key."""
        pass

    @abstractmethod
    def save_bytes(self, relative_key: str, content: bytes) -> str:
        """Saves arbitrary bytes to a canonical relative object key."""
        pass

    @abstractmethod
    def get_file_bytes(self, storage_path: str) -> bytes:
        """Reads and returns raw object bytes."""
        pass

    @abstractmethod
    def get_file_path(self, storage_path: str) -> str:
        """
        Returns local filesystem path or local temporary cache path accessible to pandas/joblib.
        """
        pass

    @abstractmethod
    def delete_file(self, storage_path: str) -> bool:
        """Deletes object from storage."""
        pass

    @abstractmethod
    def exists(self, storage_path: str) -> bool:
        """Checks if object exists."""
        pass


class LocalStorageService(StorageService):
    """
    Local filesystem implementation with strict directory traversal guards.
    Enforces identical path containment across development, testing, and production.
    """

    def __init__(self, base_dir: str | Path | None = None) -> None:
        self.base_dir = Path(base_dir or settings.STORAGE_LOCAL_DIR).resolve()
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _resolve_safe_path(self, storage_path: str) -> Path:
        p = Path(storage_path)
        if p.is_absolute():
            resolved = p.resolve()
            if resolved.is_relative_to(self.base_dir):
                return resolved
            raise PermissionError(f"Directory traversal detected for absolute path outside storage root: {storage_path}")
        target_path = (self.base_dir / storage_path).resolve()
        if not target_path.is_relative_to(self.base_dir):
            raise PermissionError(f"Directory traversal detected for path: {storage_path}")
        return target_path

    def save_file(self, project_id: str | UUID, version: int, filename: str, content: bytes) -> str:
        safe_filename = Path(filename).name
        relative_key = f"datasets/{project_id}/{version}/{safe_filename}".replace("\\", "/")
        target_path = self._resolve_safe_path(relative_key)
        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.write_bytes(content)
        return relative_key

    def save_bytes(self, relative_key: str, content: bytes) -> str:
        clean_key = str(relative_key).replace("\\", "/").lstrip("/")
        target_path = self._resolve_safe_path(clean_key)
        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.write_bytes(content)
        return clean_key

    def get_file_bytes(self, storage_path: str) -> bytes:
        path = self._resolve_safe_path(storage_path)
        if not path.exists():
            raise FileNotFoundError(f"Storage object not found at: {storage_path}")
        return path.read_bytes()

    def get_file_path(self, storage_path: str) -> str:
        path = self._resolve_safe_path(storage_path)
        if not path.exists():
            raise FileNotFoundError(f"Storage object not found at: {storage_path}")
        return str(path)

    def delete_file(self, storage_path: str) -> bool:
        path = self._resolve_safe_path(storage_path)
        if path.exists():
            path.unlink()
            return True
        return False

    def exists(self, storage_path: str) -> bool:
        try:
            return self._resolve_safe_path(storage_path).exists()
        except PermissionError:
            return False


class S3StorageService(StorageService):
    """
    S3-compatible Object Storage implementation (AWS S3, MinIO, Cloudflare R2).
    Enables shared persistence across Render API web instances and Render ML Workers.
    """

    def __init__(
        self,
        bucket_name: str | None = None,
        endpoint_url: str | None = None,
        access_key_id: str | None = None,
        secret_access_key: str | None = None,
        region_name: str | None = None,
        max_cache_bytes: int = 500 * 1024 * 1024,
    ) -> None:
        self.bucket_name = bucket_name or settings.S3_BUCKET_NAME
        self.endpoint_url = endpoint_url or settings.S3_ENDPOINT_URL
        self.access_key_id = access_key_id or settings.S3_ACCESS_KEY_ID
        self.secret_access_key = secret_access_key or settings.S3_SECRET_ACCESS_KEY
        self.region_name = region_name or settings.S3_REGION_NAME
        self.max_cache_bytes = max_cache_bytes
        self._client = None
        self._cache_dir = Path(tempfile.gettempdir()) / "ml_studio_s3_cache"
        self._cache_dir.mkdir(parents=True, exist_ok=True)

    def _get_client(self):
        if self._client is None:
            try:
                import boto3
                kwargs = {"region_name": self.region_name}
                if self.endpoint_url:
                    kwargs["endpoint_url"] = self.endpoint_url
                if self.access_key_id and self.secret_access_key:
                    kwargs["aws_access_key_id"] = self.access_key_id
                    kwargs["aws_secret_access_key"] = self.secret_access_key
                self._client = boto3.client("s3", **kwargs)
            except ImportError:
                logger.warning("boto3 not installed. Falling back to local temp storage for S3 emulation.")
                raise RuntimeError("boto3 package required for S3 object storage backend.")
        return self._client

    def _clean_key(self, storage_path: str) -> str:
        clean = os.path.normpath(str(storage_path)).replace("\\", "/").lstrip("/")
        if clean == ".." or clean.startswith("../") or "/../" in clean or clean.endswith("/.."):
            raise PermissionError(f"Directory traversal detected in S3 object key: {storage_path}")
        return clean

    def _evict_cache_if_needed(self) -> None:
        """Evicts oldest files in cache when exceeding capacity."""
        try:
            files = list(self._cache_dir.glob("**/*"))
            file_entries = [(f, f.stat().st_size, f.stat().st_mtime) for f in files if f.is_file()]
            total_size = sum(sz for _, sz, _ in file_entries)
            if total_size > self.max_cache_bytes:
                file_entries.sort(key=lambda x: x[2])
                target_size = int(self.max_cache_bytes * 0.75)
                for f, sz, _ in file_entries:
                    if total_size <= target_size:
                        break
                    try:
                        f.unlink(missing_ok=True)
                        total_size -= sz
                    except OSError:
                        pass
        except Exception as e:
            logger.warning("Cache eviction warning: %s", e)

    def clear_cache(self) -> None:
        """Cleans up temporary files from local S3 cache directory."""
        import shutil
        if self._cache_dir.exists():
            shutil.rmtree(self._cache_dir, ignore_errors=True)
            self._cache_dir.mkdir(parents=True, exist_ok=True)

    def _map_s3_error(self, e: Exception, key: str) -> Exception:
        """Translates low-level boto3 / network errors into strongly typed domain storage exceptions."""
        error_code = ""
        if hasattr(e, "response") and isinstance(e.response, dict):
            error_code = str(e.response.get("Error", {}).get("Code", ""))
        err_str = str(e).lower()
        if error_code in ("NoSuchKey", "404", "NotFound") or "nosuchkey" in err_str or "not found" in err_str:
            return ObjectNotFoundError(f"Object '{key}' not found in S3 bucket '{self.bucket_name}'.")
        if error_code in ("AccessDenied", "InvalidAccessKeyId", "SignatureDoesNotMatch", "403") or "forbidden" in err_str or "accessdenied" in err_str:
            return StoragePermissionDeniedError(f"Access denied for S3 object '{key}' in bucket '{self.bucket_name}': {e}")
        if error_code in ("EndpointConnectionError", "ConnectTimeoutError", "ReadTimeoutError", "500", "502", "503", "ServiceUnavailable", "SlowDown") or "timeout" in err_str or "endpoint" in err_str:
            return StorageUnavailableError(f"Object storage unavailable / connection error for key '{key}': {e}")
        return StorageError(f"S3 storage error for key '{key}': {e}")

    def save_file(self, project_id: str | UUID, version: int, filename: str, content: bytes) -> str:
        safe_filename = Path(filename).name
        relative_key = f"datasets/{project_id}/{version}/{safe_filename}"
        return self.save_bytes(relative_key, content)

    def save_bytes(self, relative_key: str, content: bytes) -> str:
        key = self._clean_key(relative_key)
        client = self._get_client()
        try:
            client.put_object(
                Bucket=self.bucket_name,
                Key=key,
                Body=content,
            )
            return key
        except Exception as e:
            raise self._map_s3_error(e, key) from e

    def get_file_bytes(self, storage_path: str) -> bytes:
        key = self._clean_key(storage_path)
        client = self._get_client()
        try:
            resp = client.get_object(Bucket=self.bucket_name, Key=key)
            return resp["Body"].read()
        except Exception as e:
            raise self._map_s3_error(e, key) from e

    def get_file_path(self, storage_path: str) -> str:
        self._evict_cache_if_needed()
        key = self._clean_key(storage_path)
        local_cached = (self._cache_dir / key).resolve()
        if not local_cached.is_relative_to(self._cache_dir.resolve()):
            raise PermissionError(f"Cache traversal detected for S3 key: {storage_path}")
        if not local_cached.exists():
            local_cached.parent.mkdir(parents=True, exist_ok=True)
            content = self.get_file_bytes(key)
            local_cached.write_bytes(content)
        return str(local_cached)

    def delete_file(self, storage_path: str) -> bool:
        key = self._clean_key(storage_path)
        client = self._get_client()
        try:
            client.delete_object(Bucket=self.bucket_name, Key=key)
            return True
        except Exception as e:
            logger.warning(f"Failed to delete S3 object {key}: {e}")
            return False

    def exists(self, storage_path: str) -> bool:
        key = self._clean_key(storage_path)
        client = self._get_client()
        try:
            client.head_object(Bucket=self.bucket_name, Key=key)
            return True
        except Exception as e:
            mapped = self._map_s3_error(e, key)
            if isinstance(mapped, ObjectNotFoundError):
                return False
            # Never disguise network, authorization, or timeout failures as missing objects!
            raise mapped


_global_storage: StorageService | None = None


def get_storage_service() -> StorageService:
    global _global_storage
    if _global_storage is None:
        if settings.STORAGE_BACKEND.lower() == "s3":
            _global_storage = S3StorageService()
        else:
            _global_storage = LocalStorageService()
    return _global_storage
