from typing import Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict

class SubsystemHealth(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    status: str = Field(..., description="UP, DOWN, or DEGRADED")
    latency_ms: float = Field(..., description="Latency of health check in milliseconds")
    details: Optional[Dict[str, Any]] = Field(default=None, description="Detailed metrics and diagnostic metadata")

class LivenessResponse(BaseModel):
    status: str = Field(default="alive", description="Process liveness indicator")
    service: str
    uptime_seconds: float
    timestamp: str

class ReadinessResponse(BaseModel):
    status: str = Field(..., description="ready or unready")
    ready: bool
    service: str
    dependencies: Dict[str, SubsystemHealth]
    timestamp: str

class DetailedHealthResponse(BaseModel):
    status: str = Field(..., description="HEALTHY, DEGRADED, or UNHEALTHY")
    service: str
    api_version: str
    code_version: str
    uptime_seconds: float
    dependencies: Dict[str, SubsystemHealth]
    timestamp: str
