import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.database import engine, Base, SessionLocal
from app.core.seeder import seed_rbac_data
from app.core.versioning import get_code_version
from app.api.v1.router import api_v1_router
import app.models  # Ensure all models are registered with Base.metadata

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize database tables and seed canonical RBAC permissions on startup
    try:
        Base.metadata.create_all(bind=engine)
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

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_v1_router)

from datetime import datetime, timezone

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
