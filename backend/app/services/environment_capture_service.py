import importlib.metadata
import platform
from typing import Any
from app.core.versioning import get_code_version

class EnvironmentCaptureService:
    """
    Environment and Library Version Capture Service (Day 8).
    
    ARCHITECTURAL NOTE (SRS §2.17):
    Reproducibility is environment-qualified, not absolute.
    Captures installed versions of Python, scikit-learn, numpy, pandas,
    supporting execution libraries, and the git commit hash.
    """

    MODEL_LIBRARIES: list[str] = [
        "scipy",
        "joblib",
        "threadpoolctl",
        "pydantic",
        "fastapi",
        "sqlalchemy",
    ]

    @classmethod
    def get_library_version(cls, package_name: str) -> str | None:
        try:
            return importlib.metadata.version(package_name)
        except importlib.metadata.PackageNotFoundError:
            return None
        except Exception:
            return None

    @classmethod
    def capture_current_environment(cls) -> dict[str, Any]:
        """
        Captures the exact runtime versions of Python, scikit-learn, numpy,
        pandas, additional model libraries, and code version hash.
        Returns a dictionary matching the lineage schema of Experiment.
        """
        python_ver = platform.python_version()
        sklearn_ver = cls.get_library_version("scikit-learn") or "unknown"
        numpy_ver = cls.get_library_version("numpy") or "unknown"
        pandas_ver = cls.get_library_version("pandas") or "unknown"
        code_ver = get_code_version()

        model_libs: dict[str, str] = {}
        for lib in cls.MODEL_LIBRARIES:
            ver = cls.get_library_version(lib)
            if ver:
                model_libs[lib] = ver

        return {
            "python_version": python_ver,
            "sklearn_version": sklearn_ver,
            "numpy_version": numpy_ver,
            "pandas_version": pandas_ver,
            "code_version": code_ver,
            "model_library_versions": model_libs,
        }
