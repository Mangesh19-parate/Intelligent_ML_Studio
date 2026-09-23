import json
import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, model_validator, field_validator

_BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
_ROOT_DIR = _BACKEND_DIR.parent

class Settings(BaseSettings):
    PROJECT_NAME: str = "ML Studio"
    API_V1_STR: str = "/api/v1"
    PORT: int = Field(
        default=8000,
        description="Web server listening port (dynamically injected by Render/Heroku)"
    )
    
    # Database configuration
    DATABASE_URL: str = Field(
        default=f"sqlite:///{(_BACKEND_DIR / 'ml_studio.db').as_posix()}",
        description="Database connection string"
    )
    
    ENV: str = Field(
        default="development",
        description="Application environment: development, testing, production"
    )
    AUTO_CREATE_TABLES: bool = Field(
        default=True,
        description="Auto create tables via create_all (only allowed in development/testing; production must use alembic)"
    )
    
    # Demo accounts seeding configuration
    SEED_DEMO_DATA: bool = Field(
        default=False,
        description="Seed demo accounts (development only; prohibited in production)"
    )
    
    # Artifact signing key configuration (isolated from JWT)
    ARTIFACT_SIGNING_KEY: str = Field(
        default="dev-artifact-key-change-in-production-0987654321",
        description="Secret key for signing and verifying model artifacts via HMAC"
    )
    
    # File upload limits
    MAX_UPLOAD_SIZE_MB: int = Field(
        default=50,
        description="Maximum allowed file upload size in megabytes"
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
    STORAGE_BACKEND: str = Field(
        default="local",
        description="Object storage backend: 'local' or 's3'"
    )
    STORAGE_LOCAL_DIR: str = Field(
        default=".",
        description="Base directory for local object storage"
    )
    S3_BUCKET_NAME: str = Field(
        default="ml-studio-artifacts",
        description="S3 bucket name for shared object storage"
    )
    S3_ENDPOINT_URL: str | None = Field(
        default=None,
        description="Custom S3 endpoint URL (MinIO, Cloudflare R2, LocalStack)"
    )
    S3_ACCESS_KEY_ID: str | None = Field(
        default=None,
        description="S3 Access Key ID"
    )
    S3_SECRET_ACCESS_KEY: str | None = Field(
        default=None,
        description="S3 Secret Access Key"
    )
    S3_REGION_NAME: str = Field(
        default="us-east-1",
        description="S3 Region Name"
    )
    
    # Trusted Proxies for Secure Rate Limiting & Client IP Extraction
    TRUSTED_PROXIES: str | list[str] = [
        "127.0.0.1",
        "::1",
        "localhost",
        "10.0.0.0/8",
        "172.16.0.0/12",
        "192.168.0.0/16",
    ]
    
    @field_validator("TRUSTED_PROXIES", mode="after")
    @classmethod
    def assemble_trusted_proxies(cls, v: str | list[str] | None) -> list[str]:
        if not v:
            return ["127.0.0.1", "::1"]
        if isinstance(v, str):
            v_trimmed = v.strip()
            if v_trimmed.startswith("[") and v_trimmed.endswith("]"):
                try:
                    parsed = json.loads(v_trimmed)
                    if isinstance(parsed, list):
                        return [str(item).strip() for item in parsed if str(item).strip()]
                except Exception:
                    pass
            return [item.strip() for item in v_trimmed.split(",") if item.strip()]
        if isinstance(v, list):
            return [str(item).strip() for item in v if str(item).strip()]
        return ["127.0.0.1", "::1"]
    
    # Git versioning
    GIT_COMMIT_HASH: str | None = None
    
    # CORS (explicit origins with local dev defaults)
    BACKEND_CORS_ORIGINS: str | list[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ]
    
    @field_validator("BACKEND_CORS_ORIGINS", mode="after")
    @classmethod
    def assemble_cors_origins(cls, v: str | list[str] | None) -> list[str]:
        if not v:
            return []
        if isinstance(v, str):
            v_trimmed = v.strip()
            if v_trimmed.startswith("[") and v_trimmed.endswith("]"):
                try:
                    parsed = json.loads(v_trimmed)
                    if isinstance(parsed, list):
                        return [str(item).strip() for item in parsed if str(item).strip()]
                except Exception:
                    pass
            return [item.strip() for item in v_trimmed.split(",") if item.strip()]
        if isinstance(v, list):
            return [str(item).strip() for item in v if str(item).strip()]
        return []
    
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

    @model_validator(mode="after")
    def validate_production_hygiene(self) -> "Settings":
        known_dev_secrets = {
            "dev-jwt-secret-key-change-in-production-1234567890",
            "dev-artifact-key-change-in-production-0987654321",
            "secret",
            "password",
            "changeme",
            "default",
            "secretkey",
        }
        if self.ENV.lower() == "production":
            if self.SEED_DEMO_DATA:
                raise ValueError(
                    "Production security hygiene violation: SEED_DEMO_DATA is strictly prohibited in production."
                )
            if self.JWT_SECRET in known_dev_secrets or len(self.JWT_SECRET) < 32:
                raise ValueError(
                    "Production security hygiene violation: JWT_SECRET must be set to a secure, non-default secret with at least 32 characters in production."
                )
            if self.ARTIFACT_SIGNING_KEY in known_dev_secrets or len(self.ARTIFACT_SIGNING_KEY) < 32:
                raise ValueError(
                    "Production security hygiene violation: ARTIFACT_SIGNING_KEY must be set to a secure, non-default secret with at least 32 characters in production."
                )
            if self.ARTIFACT_SIGNING_KEY == self.JWT_SECRET:
                raise ValueError(
                    "Production security hygiene violation: ARTIFACT_SIGNING_KEY must not be identical to JWT_SECRET (key separation required)."
                )
            if "*" in self.BACKEND_CORS_ORIGINS:
                raise ValueError(
                    "Production security hygiene violation: Wildcard CORS origin '*' is strictly prohibited in production."
                )
        return self

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
