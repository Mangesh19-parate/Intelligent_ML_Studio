import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.database import engine, Base, SessionLocal, sync_database_schema
from app.core.seeder import seed_rbac_data
from app.core.versioning import get_code_version
from app.api.v1.router import api_v1_router
import app.models  # Ensure all models are registered with Base.metadata

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Production security guard
    if settings.ENV == "production":
        if not settings.JWT_SECRET or settings.JWT_SECRET.startswith("dev-jwt-secret"):
            raise RuntimeError("CRITICAL: Insecure development JWT_SECRET detected in production environment.")

    # Initialize database tables and seed canonical RBAC permissions
    # In production, schema migrations are strictly managed via Alembic
    try:
        if settings.AUTO_CREATE_TABLES and settings.ENV != "production":
            Base.metadata.create_all(bind=engine)
            sync_database_schema(engine)
        with SessionLocal() as db:
            seed_rbac_data(db)
        logger.info("Database initialized and RBAC seeded successfully.")
    except Exception as e:
        if settings.ENV == "production":
            logger.critical(f"FATAL: Production database initialization/seeding failed: {e}")
            raise RuntimeError(f"FATAL: Production database connection/seeding failed: {e}") from e
        logger.warning(f"Database initialization deferred or skipped: {e}")
    yield

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="ML Studio: Leakage-controlled, no-code tabular machine learning platform",
    version="1.0.0",
    lifespan=lifespan,
)

from app.core.logging_middleware import StructuredLoggingMiddleware
from app.core.security_headers import SecurityHeadersMiddleware

app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(StructuredLoggingMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_v1_router)

from datetime import datetime, timezone
from fastapi import Request, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

import uuid

STATUS_TITLES = {
    400: "Bad Request",
    401: "Unauthorized",
    403: "Forbidden",
    404: "Resource Not Found",
    409: "Conflict",
    422: "Unprocessable Entity",
    429: "Too Many Requests",
    500: "Internal Server Error",
    503: "Service Unavailable",
}

def get_error_type(status_code: int, code: str) -> str:
    slug = code.lower().replace("_", "-")
    return f"https://api.mlstudio.dev/errors/{slug}"

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
    msg = exc.detail if isinstance(exc.detail, str) else str(exc.detail)
    status_title = STATUS_TITLES.get(exc.status_code, "HTTP Error")
    error_code = f"HTTP_{exc.status_code}"
    timestamp = datetime.now(timezone.utc).isoformat()

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "type": get_error_type(exc.status_code, error_code),
            "title": status_title,
            "status": exc.status_code,
            "detail": exc.detail,
            "instance": str(request.url.path),
            "request_id": request_id,
            "timestamp": timestamp,
            "error": {
                "status_code": exc.status_code,
                "code": error_code,
                "message": msg,
                "details": [
                    {"loc": [str(request.url.path)], "message": msg, "code": error_code}
                ],
                "path": str(request.url.path),
                "request_id": request_id,
                "timestamp": timestamp,
            },
        },
        headers=getattr(exc, "headers", None),
    )

from fastapi.encoders import jsonable_encoder

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
    safe_errors = jsonable_encoder(exc.errors())
    timestamp = datetime.now(timezone.utc).isoformat()
    formatted_details = [
        {
            "loc": [str(x) for x in err.get("loc", [])],
            "message": str(err.get("msg", "Validation error")),
            "code": str(err.get("type", "VALUE_ERROR")),
        }
        for err in safe_errors
    ]
    return JSONResponse(
        status_code=422,
        content={
            "type": "https://api.mlstudio.dev/errors/request-validation-error",
            "title": "Unprocessable Entity",
            "status": 422,
            "detail": safe_errors,
            "instance": str(request.url.path),
            "request_id": request_id,
            "timestamp": timestamp,
            "error": {
                "status_code": 422,
                "code": "REQUEST_VALIDATION_ERROR",
                "message": "Request validation failed",
                "details": formatted_details,
                "path": str(request.url.path),
                "request_id": request_id,
                "timestamp": timestamp,
            },
        },
    )

from fastapi import Response, Depends, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.services.health_service import HealthService
from app.schemas.health import (
    SubsystemHealth,
    LivenessResponse,
    ReadinessResponse,
    DetailedHealthResponse,
)

@app.get("/health", tags=["Health"], summary="Backward-compatible baseline health probe")
@app.get("/api/v1/health", tags=["Health"], summary="Backward-compatible baseline health probe")
def health_check():
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "api_version": "v1",
        "code_version": get_code_version(),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

@app.get("/health/live", response_model=LivenessResponse, tags=["Health"], summary="Kubernetes / container liveness probe")
@app.get("/api/v1/health/live", response_model=LivenessResponse, tags=["Health"], summary="Kubernetes / container liveness probe")
def liveness_check():
    service = HealthService()
    return service.check_liveness()

@app.get("/health/ready", response_model=ReadinessResponse, tags=["Health"], summary="Kubernetes / load-balancer deep readiness probe")
@app.get("/api/v1/health/ready", response_model=ReadinessResponse, tags=["Health"], summary="Kubernetes / load-balancer deep readiness probe")
def readiness_check(response: Response, db: Session = Depends(get_db)):
    service = HealthService(db)
    is_ready, data = service.check_readiness(db)
    if not is_ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return data

@app.get("/health/worker", response_model=SubsystemHealth, tags=["Health"], summary="Standalone worker health and heartbeat probe")
@app.get("/api/v1/health/worker", response_model=SubsystemHealth, tags=["Health"], summary="Standalone worker health and heartbeat probe")
def worker_health_check(db: Session = Depends(get_db)):
    service = HealthService(db)
    return service.check_worker(db)

@app.get("/health/status", response_model=DetailedHealthResponse, tags=["Health"], summary="Multi-service subsystem observability and telemetry report")
@app.get("/api/v1/health/status", response_model=DetailedHealthResponse, tags=["Health"], summary="Multi-service subsystem observability and telemetry report")
def detailed_health_status(response: Response, db: Session = Depends(get_db)):
    service = HealthService(db)
    http_code, data = service.get_detailed_status(db, code_version=get_code_version())
    response.status_code = http_code
    return data

