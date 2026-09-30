"""
Typed Domain Exception Hierarchy for Intelligent ML Studio.
Maps domain failures to explicit HTTP semantics and structured error payloads.
"""

from typing import Any


class StudioBaseException(Exception):
    """Base exception for all Intelligent ML Studio domain errors."""

    def __init__(
        self,
        message: str,
        status_code: int = 500,
        error_code: str = "INTERNAL_ERROR",
        details: list[dict[str, Any]] | None = None,
    ):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        self.details = details or []


class StudioNotFoundError(StudioBaseException):
    """Raised when an entity, model, dataset, or object is not found (HTTP 404)."""

    def __init__(self, message: str = "Resource not found", details: list[dict[str, Any]] | None = None):
        super().__init__(message=message, status_code=404, error_code="NOT_FOUND", details=details)


class StudioPermissionDeniedError(StudioBaseException):
    """Raised when an operation violates RBAC permissions or tenancy boundary (HTTP 403)."""

    def __init__(self, message: str = "Permission denied", details: list[dict[str, Any]] | None = None):
        super().__init__(message=message, status_code=403, error_code="PERMISSION_DENIED", details=details)


class StudioValidationError(StudioBaseException):
    """Raised when business logic or domain constraints fail validation (HTTP 422)."""

    def __init__(self, message: str = "Validation error", details: list[dict[str, Any]] | None = None):
        super().__init__(message=message, status_code=422, error_code="VALIDATION_ERROR", details=details)


class StudioConflictError(StudioBaseException):
    """Raised when an entity with unique constraints or locked state conflicts (HTTP 409)."""

    def __init__(self, message: str = "Resource state conflict", details: list[dict[str, Any]] | None = None):
        super().__init__(message=message, status_code=409, error_code="CONFLICT", details=details)


class StudioStorageIntegrityError(StudioBaseException):
    """Raised when cryptographic verification, HMAC signature, or storage integrity fails (HTTP 502/500)."""

    def __init__(self, message: str = "Storage integrity failure", details: list[dict[str, Any]] | None = None):
        super().__init__(message=message, status_code=502, error_code="STORAGE_INTEGRITY_ERROR", details=details)


class StudioWorkerTimeoutError(StudioBaseException):
    """Raised when background durable task exceeds execution deadline (HTTP 504)."""

    def __init__(self, message: str = "Worker task execution timed out", details: list[dict[str, Any]] | None = None):
        super().__init__(message=message, status_code=504, error_code="GATEWAY_TIMEOUT", details=details)


class StudioUnavailableError(StudioBaseException):
    """Raised when an upstream subsystem, database pool, or storage service is unavailable (HTTP 503)."""

    def __init__(self, message: str = "Service temporarily unavailable", details: list[dict[str, Any]] | None = None):
        super().__init__(message=message, status_code=503, error_code="SERVICE_UNAVAILABLE", details=details)
