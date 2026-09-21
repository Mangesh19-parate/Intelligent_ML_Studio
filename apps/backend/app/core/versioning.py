import os
import subprocess
from functools import lru_cache
from app.core.config import settings

@lru_cache()
def get_code_version() -> str:
    """
    Returns the current git commit hash.
    First checks the build-time/runtime environment variable GIT_COMMIT_HASH.
    Falls back to running `git rev-parse HEAD`.
    If git is unavailable or fails, returns a fallback deterministic identifier.
    """
    if settings.GIT_COMMIT_HASH:
        return settings.GIT_COMMIT_HASH
    
    env_hash = os.getenv("GIT_COMMIT_HASH")
    if env_hash:
        return env_hash
    
    try:
        commit_hash = subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            stderr=subprocess.DEVNULL
        ).decode("ascii").strip()
        if commit_hash:
            return commit_hash
    except Exception:
        pass
    
    return "0000000000000000000000000000000000000000"
