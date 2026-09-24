"""
Storage Containment and S3 Cache Eviction Security Invariant Tests.
"""

import os
import pytest
from pathlib import Path
from app.infrastructure.storage.object_store import LocalStorageService, S3StorageService


def test_local_storage_traversal_subpath_escape_blocked(tmp_path):
    """
    INVARIANT: Directory traversal using prefix collision (e.g. /tmp/base_evil vs /tmp/base)
    must be strictly blocked by path containment (Path.is_relative_to).
    """
    base_dir = tmp_path / "base"
    base_dir.mkdir()
    
    evil_sibling = tmp_path / "base_evil"
    evil_sibling.mkdir()
    (evil_sibling / "pwned.txt").write_text("compromised")

    storage = LocalStorageService(base_dir=str(base_dir))

    # Test parent directory escape
    with pytest.raises(PermissionError, match="Directory traversal detected"):
        storage.get_file_bytes("../base_evil/pwned.txt")

    with pytest.raises(PermissionError, match="Directory traversal detected"):
        storage.save_bytes("../base_evil/attack.txt", b"evil")

    # Test root directory escape
    with pytest.raises(PermissionError, match="Directory traversal detected"):
        storage.get_file_bytes("../../etc/passwd")



def test_object_store_local_traversal_blocked(tmp_path):
    base_dir = tmp_path / "data"
    base_dir.mkdir()
    
    storage = LocalStorageService(base_dir=str(base_dir))

    
    with pytest.raises(PermissionError, match="Directory traversal detected"):
        storage.get_file_bytes("../outside.txt")

    with pytest.raises(PermissionError, match="Directory traversal detected"):
        storage.save_bytes("../outside.txt", b"evil")


def test_s3_storage_cache_eviction(tmp_path):
    """
    INVARIANT: S3 temporary cache enforces maximum cache size and evicts oldest items.
    """
    s3_storage = S3StorageService(bucket_name="test-bucket", max_cache_bytes=1000)
    # Set cache dir to test tmp path
    s3_storage._cache_dir = tmp_path / "s3_cache"
    s3_storage._cache_dir.mkdir()

    # Create dummy cached files exceeding 1000 bytes
    f1 = s3_storage._cache_dir / "old_file.bin"
    f2 = s3_storage._cache_dir / "new_file.bin"
    
    f1.write_bytes(b"A" * 600)
    os.utime(f1, (1000, 1000))
    # Give f2 newer atime
    f2.write_bytes(b"B" * 600)
    os.utime(f2, (2000, 2000))

    assert f1.exists()
    assert f2.exists()

    s3_storage._evict_cache_if_needed()

    # Old file should have been evicted to bring total under 750 bytes
    assert not f1.exists()
    assert f2.exists()

    # Test clear_cache
    s3_storage.clear_cache()
    assert s3_storage._cache_dir.exists()
    assert len(list(s3_storage._cache_dir.glob("*"))) == 0


def test_s3_storage_cache_traversal_blocked(tmp_path):
    """
    INVARIANT: S3 object keys containing traversal sequences ('..') must be rejected
    before filesystem cache path construction.
    """
    s3_storage = S3StorageService(bucket_name="test-bucket")
    s3_storage._cache_dir = tmp_path / "s3_cache"
    s3_storage._cache_dir.mkdir()

    with pytest.raises(PermissionError, match="Directory traversal detected in S3 object key"):
        s3_storage._clean_key("../escape.bin")

    with pytest.raises(PermissionError, match="Directory traversal detected in S3 object key"):
        s3_storage._clean_key("datasets/../../etc/passwd")


def test_typed_storage_exceptions_mapping():
    """
    P1.2 INVARIANT: Storage errors must be strongly typed:
    - NoSuchKey -> ObjectNotFoundError (404)
    - Connection/Endpoint -> StorageUnavailableError (503)
    - AccessDenied -> StoragePermissionDeniedError (403/500)
    """
    from app.infrastructure.storage.object_store import (
        ObjectNotFoundError,
        StorageUnavailableError,
        StoragePermissionDeniedError,
        S3StorageService,
    )

    s3 = S3StorageService(bucket_name="test-bucket")

    # 1. 404 / NoSuchKey
    err_404 = Exception("An error occurred (NoSuchKey) when calling the GetObject operation")
    mapped_404 = s3._map_s3_error(err_404, "models/proj/model.joblib")
    assert isinstance(mapped_404, ObjectNotFoundError)

    # 2. 503 / Endpoint outage
    err_503 = Exception("Could not connect to the endpoint URL: https://s3.amazonaws.com")
    mapped_503 = s3._map_s3_error(err_503, "models/proj/model.joblib")
    assert isinstance(mapped_503, StorageUnavailableError)

    # 3. 403 / AccessDenied
    err_403 = Exception("An error occurred (AccessDenied) when calling the PutObject operation")
    mapped_403 = s3._map_s3_error(err_403, "models/proj/model.joblib")
    assert isinstance(mapped_403, StoragePermissionDeniedError)


def test_local_storage_absolute_path_escape_blocked_in_all_envs(tmp_path):
    """
    P1.3 INVARIANT: Absolute path traversal outside the storage root is rejected
    with PermissionError across all environments (no dev/testing bypass).
    """
    base_dir = tmp_path / "sandbox"
    base_dir.mkdir()
    outside_file = tmp_path / "outside_secret.txt"
    outside_file.write_text("secret")

    storage = LocalStorageService(base_dir=str(base_dir))

    with pytest.raises(PermissionError, match="Directory traversal detected for absolute path"):
        storage._resolve_safe_path(str(outside_file))

