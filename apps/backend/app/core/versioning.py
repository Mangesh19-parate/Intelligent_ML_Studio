import os
import subprocess
from typing import Any
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


@lru_cache()
def get_environment_metadata() -> dict[str, Any]:
    """Captures runtime runtime library versions for reproducibility snapshot."""
    import sys
    meta = {
        "python_version": sys.version.split()[0],
        "environment_capture_method": "RUNTIME_INSPECTION",
        "model_library_versions": {},
    }
    try:
        import sklearn
        meta["sklearn_version"] = sklearn.__version__
        meta["model_library_versions"]["scikit-learn"] = sklearn.__version__
    except ImportError:
        meta["sklearn_version"] = None

    try:
        import numpy
        meta["numpy_version"] = numpy.__version__
        meta["model_library_versions"]["numpy"] = numpy.__version__
    except ImportError:
        meta["numpy_version"] = None

    try:
        import pandas
        meta["pandas_version"] = pandas.__version__
        meta["model_library_versions"]["pandas"] = pandas.__version__
    except ImportError:
        meta["pandas_version"] = None

    return meta
