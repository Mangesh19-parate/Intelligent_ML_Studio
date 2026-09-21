from datetime import datetime, timedelta, timezone
from uuid import UUID
from typing import Any
import numpy as np
from sqlalchemy.orm import Session

from app.models.deployment import Deployment
from app.models.prediction_log import PredictionLog


class MonitoringService:
    """
    Monitoring Service (Day 11).
    
    ARCHITECTURAL NOTE:
    Aggregates inference observability and performance telemetry over `prediction_logs`:
    1. volume_over_time: bucketed request counts with status breakdowns.
    2. latency_summary: decoupled metrics (avg, p50, p95) separately for base predictions
       and explained predictions to clearly expose SHAP computation cost profiles.
    3. error_rate: distinct separation between VALIDATION_ERROR (client payload failure)
       and SERVER_ERROR (internal inference execution crash).
    """

    def __init__(self, db: Session):
        self.db = db

    def _get_cutoff(self, lookback_hours: int) -> datetime:
        return datetime.now(timezone.utc) - timedelta(hours=lookback_hours)

    def _compute_percentiles(self, values: list[float | int]) -> dict[str, float | None]:
        if not values:
            return {
                "avg_ms": 0.0,
                "p50_ms": 0.0,
                "p95_ms": 0.0,
                "min_ms": 0.0,
                "max_ms": 0.0,
                "count": 0,
            }
        arr = np.array(values, dtype=float)
        return {
            "avg_ms": float(np.round(np.mean(arr), 2)),
            "p50_ms": float(np.round(np.percentile(arr, 50), 2)),
            "p95_ms": float(np.round(np.percentile(arr, 95), 2)),
            "min_ms": float(np.round(np.min(arr), 2)),
            "max_ms": float(np.round(np.max(arr), 2)),
            "count": len(values),
        }

    def volume_over_time(
        self,
        deployment_id: UUID | str,
        bucket: str = "hour",
        lookback_hours: int = 24
    ) -> list[dict[str, Any]]:
        """
        Calculates bucketed request volume and status breakdowns over time.
        """
        dep_id = UUID(str(deployment_id)) if not isinstance(deployment_id, UUID) else deployment_id
        cutoff = self._get_cutoff(lookback_hours)

        logs = (
            self.db.query(PredictionLog)
            .filter(
                PredictionLog.deployment_id == dep_id,
                PredictionLog.requested_at >= cutoff
            )
            .order_by(PredictionLog.requested_at.asc())
            .all()
        )

        # Bucket by hour
        buckets: dict[str, dict[str, Any]] = {}
        for log in logs:
            req_time = log.requested_at
            if req_time.tzinfo is None:
                req_time = req_time.replace(tzinfo=timezone.utc)
            bucket_key = req_time.strftime("%Y-%m-%dT%H:00:00Z")

            if bucket_key not in buckets:
                buckets[bucket_key] = {
                    "timestamp": bucket_key,
                    "total_requests": 0,
                    "success_count": 0,
                    "validation_error_count": 0,
                    "server_error_count": 0,
                }

            buckets[bucket_key]["total_requests"] += 1
            if log.status == "SUCCESS":
                buckets[bucket_key]["success_count"] += 1
            elif log.status == "VALIDATION_ERROR":
                buckets[bucket_key]["validation_error_count"] += 1
            elif log.status == "SERVER_ERROR":
                buckets[bucket_key]["server_error_count"] += 1

        # Return sorted list of buckets
        result = [buckets[k] for k in sorted(buckets.keys())]
        return result

    def latency_summary(
        self,
        deployment_id: UUID | str,
        lookback_hours: int = 24
    ) -> dict[str, Any]:
        """
        Calculates latency metrics separately for base predictions and explained predictions.
        Base predictions: latency_ms where explanation_requested=False
        Explained predictions: (latency_ms + explanation_latency_ms) where explanation_requested=True
        """
        dep_id = UUID(str(deployment_id)) if not isinstance(deployment_id, UUID) else deployment_id
        cutoff = self._get_cutoff(lookback_hours)

        logs = (
            self.db.query(PredictionLog)
            .filter(
                PredictionLog.deployment_id == dep_id,
                PredictionLog.requested_at >= cutoff
            )
            .all()
        )

        base_latencies: list[int] = []
        explained_total_latencies: list[int] = []
        explained_base_latencies: list[int] = []
        explained_shap_latencies: list[int] = []

        for log in logs:
            if not log.explanation_requested:
                if log.latency_ms is not None:
                    base_latencies.append(log.latency_ms)
            else:
                base_lat = log.latency_ms or 0
                shap_lat = log.explanation_latency_ms or 0
                explained_base_latencies.append(base_lat)
                explained_shap_latencies.append(shap_lat)
                explained_total_latencies.append(base_lat + shap_lat)

        base_stats = self._compute_percentiles(base_latencies)
        explained_stats = self._compute_percentiles(explained_total_latencies)

        # Add subcomponent breakdown for explained path
        if explained_shap_latencies:
            explained_stats["base_avg_ms"] = float(np.round(np.mean(explained_base_latencies), 2))
            explained_stats["explanation_avg_ms"] = float(np.round(np.mean(explained_shap_latencies), 2))
        else:
            explained_stats["base_avg_ms"] = 0.0
            explained_stats["explanation_avg_ms"] = 0.0

        return {
            "base_predictions": base_stats,
            "explained_predictions": explained_stats,
            "total_measured_requests": len(base_latencies) + len(explained_total_latencies),
        }

    def error_rate(
        self,
        deployment_id: UUID | str,
        lookback_hours: int = 24
    ) -> dict[str, Any]:
        """
        Calculates error rates with explicit status breakdown:
        error_rate = (VALIDATION_ERROR + SERVER_ERROR count) / total requests
        """
        dep_id = UUID(str(deployment_id)) if not isinstance(deployment_id, UUID) else deployment_id
        cutoff = self._get_cutoff(lookback_hours)

        logs = (
            self.db.query(PredictionLog)
            .filter(
                PredictionLog.deployment_id == dep_id,
                PredictionLog.requested_at >= cutoff
            )
            .all()
        )

        total = len(logs)
        success_count = sum(1 for l in logs if l.status == "SUCCESS")
        validation_error_count = sum(1 for l in logs if l.status == "VALIDATION_ERROR")
        server_error_count = sum(1 for l in logs if l.status == "SERVER_ERROR")
        total_errors = validation_error_count + server_error_count

        return {
            "total_requests": total,
            "success_count": success_count,
            "validation_error_count": validation_error_count,
            "server_error_count": server_error_count,
            "error_rate": float(np.round(total_errors / total, 4)) if total > 0 else 0.0,
            "validation_error_rate": float(np.round(validation_error_count / total, 4)) if total > 0 else 0.0,
            "server_error_rate": float(np.round(server_error_count / total, 4)) if total > 0 else 0.0,
            "lookback_hours": lookback_hours,
        }

    def get_monitoring_dashboard(
        self,
        deployment_id: UUID | str,
        lookback_hours: int = 24,
        log_limit: int = 50
    ) -> dict[str, Any]:
        """
        Combines volume, latency summary, error rate breakdown, and recent logs into one payload.
        """
        dep_id = UUID(str(deployment_id)) if not isinstance(deployment_id, UUID) else deployment_id
        deployment = self.db.query(Deployment).filter(Deployment.id == dep_id).first()

        recent_logs = (
            self.db.query(PredictionLog)
            .filter(PredictionLog.deployment_id == dep_id)
            .order_by(PredictionLog.requested_at.desc())
            .limit(log_limit)
            .all()
        )

        serialized_logs = [
            {
                "id": str(l.id),
                "deployment_id": str(l.deployment_id),
                "request_id": str(l.request_id),
                "schema_hash": l.schema_hash,
                "payload_mode": l.payload_mode,
                "input_payload": l.input_payload,
                "prediction_output": l.prediction_output,
                "latency_ms": l.latency_ms,
                "explanation_requested": l.explanation_requested,
                "explanation_latency_ms": l.explanation_latency_ms,
                "status": l.status,
                "requested_at": l.requested_at.isoformat() if l.requested_at else None,
            }
            for l in recent_logs
        ]

        return {
            "deployment_id": str(dep_id),
            "status": deployment.status if deployment else "UNKNOWN",
            "endpoint_path": deployment.endpoint_path if deployment else "",
            "deployed_at": deployment.deployed_at.isoformat() if deployment and deployment.deployed_at else None,
            "volume_over_time": self.volume_over_time(dep_id, lookback_hours=lookback_hours),
            "latency_summary": self.latency_summary(dep_id, lookback_hours=lookback_hours),
            "error_rate": self.error_rate(dep_id, lookback_hours=lookback_hours),
            "recent_logs": serialized_logs,
        }
