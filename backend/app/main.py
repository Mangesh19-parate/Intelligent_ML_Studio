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
        logger.warning(f"Database initialization deferred or skipped: {e}")
    yield

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="ML Studio: Leakage-controlled, no-code tabular machine learning platform",
    version="1.0.0",
    lifespan=lifespan,
)

from app.core.logging_middleware import StructuredLoggingMiddleware

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

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
    msg = exc.detail if isinstance(exc.detail, str) else str(exc.detail)
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "detail": exc.detail,
            "error": {
                "status_code": exc.status_code,
                "code": f"HTTP_{exc.status_code}",
                "message": msg,
                "details": [
                    {"loc": [str(request.url.path)], "message": msg, "code": f"HTTP_{exc.status_code}"}
                ],
                "path": str(request.url.path),
                "request_id": request_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        },
        headers=getattr(exc, "headers", None),
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
    formatted_details = [
        {
            "loc": [str(x) for x in err.get("loc", [])],
            "message": err.get("msg", "Validation error"),
            "code": err.get("type", "VALUE_ERROR"),
        }
        for err in exc.errors()
    ]
    return JSONResponse(
        status_code=422,
        content={
            "detail": exc.errors(),
            "error": {
                "status_code": 422,
                "code": "REQUEST_VALIDATION_ERROR",
                "message": "Request validation failed",
                "details": formatted_details,
                "path": str(request.url.path),
                "request_id": request_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        },
    )

@app.get("/health", tags=["Health"])
@app.get("/api/v1/health", tags=["Health"])
def health_check():
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "api_version": "v1",
        "code_version": get_code_version(),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
