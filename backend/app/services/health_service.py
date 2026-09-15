import time
import os
import shutil
import tempfile
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.core.config import settings
from app.schemas.health import (
    SubsystemHealth,
    LivenessResponse,
    ReadinessResponse,
    DetailedHealthResponse,
)

# Record process startup timestamp
PROCESS_START_TIME = time.time()

def get_process_uptime() -> float:
    return round(time.time() - PROCESS_START_TIME, 2)

class HealthService:
    def __init__(self, db: Session | None = None):
        self.db = db

    def check_liveness(self) -> LivenessResponse:
        return LivenessResponse(
            status="alive",
            service=settings.PROJECT_NAME,
            uptime_seconds=get_process_uptime(),
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

    def check_database(self, db: Session | None = None) -> SubsystemHealth:
        session = db or self.db
        start = time.perf_counter()
        if not session:
            return SubsystemHealth(
                status="DOWN",
                latency_ms=0.0,
                details={"error": "Database session unavailable"},
            )
        try:
            session.execute(text("SELECT 1"))
            latency_ms = round((time.perf_counter() - start) * 1000, 2)
            
            pool_info = {}
            bind = session.get_bind()
            if hasattr(bind, "pool"):
                pool = bind.pool
                pool_info = {
                    "pool_size": getattr(pool, "size", lambda: None)(),
                    "checked_in": getattr(pool, "checkedin", lambda: None)(),
                    "checked_out": getattr(pool, "checkedout", lambda: None)(),
                    "overflow": getattr(pool, "overflow", lambda: None)(),
                }

            return SubsystemHealth(
                status="UP",
                latency_ms=latency_ms,
                details={
                    "dialect": bind.dialect.name if bind else "unknown",
                    "pool": pool_info,
                },
            )
        except Exception as e:
            latency_ms = round((time.perf_counter() - start) * 1000, 2)
            return SubsystemHealth(
                status="DOWN",
                latency_ms=latency_ms,
                details={"error": str(e)},
            )

    def check_storage(self) -> SubsystemHealth:
        start = time.perf_counter()
        storage_dir = Path(settings.STORAGE_LOCAL_DIR)
        try:
            storage_dir.mkdir(parents=True, exist_ok=True)
            
            # Atomic write/read test
            test_file = storage_dir / f".health_probe_{os.getpid()}_{int(time.time())}.tmp"
            test_file.write_text("health_check_ok", encoding="utf-8")
            read_back = test_file.read_text(encoding="utf-8")
            if test_file.exists():
                test_file.unlink(missing_ok=True)
                
            if read_back != "health_check_ok":
                raise IOError("Storage write verification failed: read content did not match written probe.")

            # Measure disk capacity
            disk = shutil.disk_usage(str(storage_dir))
            latency_ms = round((time.perf_counter() - start) * 1000, 2)
            
            return SubsystemHealth(
                status="UP",
                latency_ms=latency_ms,
                details={
                    "path": str(storage_dir),
                    "writeable": True,
                    "total_gb": round(disk.total / (1024 ** 3), 2),
                    "free_gb": round(disk.free / (1024 ** 3), 2),
                    "used_percent": round((disk.used / disk.total) * 100, 1),
                },
            )
        except Exception as e:
            latency_ms = round((time.perf_counter() - start) * 1000, 2)
            return SubsystemHealth(
                status="DOWN",
                latency_ms=latency_ms,
                details={
                    "path": str(storage_dir),
                    "writeable": False,
                    "error": str(e),
                },
            )

    def check_task_queue(self, db: Session | None = None) -> SubsystemHealth:
        session = db or self.db
        start = time.perf_counter()
        if not session:
            return SubsystemHealth(
                status="DOWN",
                latency_ms=0.0,
                details={"error": "Database session unavailable for task queue"},
            )
        try:
            from app.models.durable_task import DurableTask
            from sqlalchemy import func
            
            counts = (
                session.query(DurableTask.status, func.count(DurableTask.task_id))
                .group_by(DurableTask.status)
                .all()
            )
            count_map = {status: count for status, count in counts}
            latency_ms = round((time.perf_counter() - start) * 1000, 2)
            
            return SubsystemHealth(
                status="UP",
                latency_ms=latency_ms,
                details={
                    "engine": "DurableTask",
                    "queued_tasks": count_map.get("QUEUED", 0),
                    "running_tasks": count_map.get("RUNNING", 0),
                    "succeeded_tasks": count_map.get("SUCCEEDED", 0),
                    "failed_tasks": count_map.get("FAILED", 0),
                },
            )
        except Exception as e:
            latency_ms = round((time.perf_counter() - start) * 1000, 2)
            return SubsystemHealth(
                status="DOWN",
                latency_ms=latency_ms,
                details={"error": str(e)},
            )

    def check_ml_runtime(self) -> SubsystemHealth:
        start = time.perf_counter()
        try:
            import sklearn
            import shap
            import pandas as pd
            import numpy as np

            latency_ms = round((time.perf_counter() - start) * 1000, 2)
            return SubsystemHealth(
                status="UP",
                latency_ms=latency_ms,
                details={
                    "sklearn_version": sklearn.__version__,
                    "shap_version": shap.__version__,
                    "pandas_version": pd.__version__,
                    "numpy_version": np.__version__,
                },
            )
        except Exception as e:
            latency_ms = round((time.perf_counter() - start) * 1000, 2)
            return SubsystemHealth(
                status="DOWN",
                latency_ms=latency_ms,
                details={"error": str(e)},
            )

    def check_readiness(self, db: Session | None = None) -> Tuple[bool, ReadinessResponse]:
        db_health = self.check_database(db)
        storage_health = self.check_storage()
        task_health = self.check_task_queue(db)

        dependencies = {
            "database": db_health,
            "storage": storage_health,
            "task_queue": task_health,
        }

        # Ready only if critical dependencies (database and storage) are UP
        is_ready = (db_health.status == "UP" and storage_health.status == "UP")
        status_label = "ready" if is_ready else "unready"

        response = ReadinessResponse(
            status=status_label,
            ready=is_ready,
            service=settings.PROJECT_NAME,
            dependencies=dependencies,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
        return is_ready, response

    def get_detailed_status(self, db: Session | None = None, code_version: str = "unknown") -> Tuple[int, DetailedHealthResponse]:
        db_health = self.check_database(db)
        storage_health = self.check_storage()
        task_health = self.check_task_queue(db)
        ml_health = self.check_ml_runtime()

        dependencies = {
            "database": db_health,
            "storage": storage_health,
            "task_queue": task_health,
            "ml_runtime": ml_health,
        }

        # Determine overall system status
        critical_statuses = [db_health.status, storage_health.status]
        all_statuses = [h.status for h in dependencies.values()]

        if any(s == "DOWN" for s in critical_statuses):
            overall_status = "UNHEALTHY"
            http_status = 503
        elif any(s in ("DOWN", "DEGRADED") for s in all_statuses):
            overall_status = "DEGRADED"
            http_status = 200
        else:
            overall_status = "HEALTHY"
            http_status = 200

        response = DetailedHealthResponse(
            status=overall_status,
            service=settings.PROJECT_NAME,
            api_version="v1",
            code_version=code_version,
            uptime_seconds=get_process_uptime(),
            dependencies=dependencies,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
        return http_status, response
