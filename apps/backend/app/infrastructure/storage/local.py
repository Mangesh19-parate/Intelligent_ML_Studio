"""
Local Filesystem Storage Implementation with Directory Containment Security.
"""

import os
from pathlib import Path
from typing import BinaryIO


class LocalStorageService:
    """Production-hardened local file storage."""

    def __init__(self, base_dir: str | Path = "./data"):
        self.base_dir = Path(base_dir).resolve()
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _resolve_safe_path(self, relative_path: str) -> Path:
        """Guards against directory traversal attacks (e.g. ../../etc/passwd)."""
        clean_rel = os.path.normpath(relative_path).lstrip("/\\")
        target_path = (self.base_dir / clean_rel).resolve()
        if not str(target_path).startswith(str(self.base_dir)):
            raise PermissionError(f"Directory traversal detected for path: {relative_path}")
        return target_path

    def save_file(self, relative_path: str, content: bytes) -> str:
        safe_path = self._resolve_safe_path(relative_path)
        safe_path.parent.mkdir(parents=True, exist_ok=True)
        safe_path.write_bytes(content)
        return str(safe_path)

    def load_file(self, relative_path: str) -> bytes:
        safe_path = self._resolve_safe_path(relative_path)
        if not safe_path.exists():
            raise FileNotFoundError(f"File not found: {relative_path}")
        return safe_path.read_bytes()

    def exists(self, relative_path: str) -> bool:
        try:
            return self._resolve_safe_path(relative_path).exists()
        except PermissionError:
            return False
