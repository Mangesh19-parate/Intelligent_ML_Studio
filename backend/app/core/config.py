import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

_BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
_ROOT_DIR = _BACKEND_DIR.parent

class Settings(BaseSettings):
    PROJECT_NAME: str = "ML Studio"
    API_V1_STR: str = "/api/v1"
    
    # Database configuration
    DATABASE_URL: str = Field(
        default="sqlite:///./backend/ml_studio.db" if (_BACKEND_DIR / "ml_studio.db").exists() else "sqlite:///./ml_studio.db",
        description="Database connection string"
    )
    
    # JWT Security configuration
    JWT_SECRET: str = Field(
        default="dev-jwt-secret-key-change-in-production-1234567890",
        description="Secret key for signing JWT tokens"
    )
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 1 day
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # Object Storage configuration
    STORAGE_LOCAL_DIR: str = Field(
        default="./data",
        description="Base directory for local object storage"
    )
    
    # Git versioning
    GIT_COMMIT_HASH: str | None = None
    
    # CORS
    BACKEND_CORS_ORIGINS: list[str] = ["*"]
    
    model_config = SettingsConfigDict(
        env_file=(
            str(_ROOT_DIR / ".env"),
            str(_BACKEND_DIR / ".env"),
            ".env",
            "backend/.env",
        ),
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )

    @property
    def sync_database_url(self) -> str:
        url = self.DATABASE_URL
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql://", 1)
        if url.startswith("sqlite:///"):
            raw_path = url[len("sqlite:///"):]
            if raw_path.startswith("./"):
                clean_rel = raw_path[2:]
                backend_candidate = _BACKEND_DIR / clean_rel
                if backend_candidate.exists():
                    return f"sqlite:///{backend_candidate.as_posix()}"
        return url

settings = Settings()
