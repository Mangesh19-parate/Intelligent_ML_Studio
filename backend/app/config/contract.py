"""
ML Studio — Canonical Architecture & System Contract (Frozen)
Reference: Software Requirements Specification (SRS) v4 / Architectural Contract §8

This file is the single authoritative programmatic source of truth for:
- Canonical algorithm set definitions & metadata
- Feature selection defaults and heuristics
- Cryptographic hash algorithms
- Dataset identifier and versioning semantics
- API routing versions and conventions
- System timestamp & timezone policies
- Identifier generation (UUIDv4) strategy
- Cursor-based pagination protocols
- Canonical RFC-7807 compatible error envelope schemas
- Standard HTTP status code conventions
- Authoritative metric naming and selection directions
- Standardized artifact paths and storage hierarchies
- Environment-qualified reproducibility tolerances
"""

from __future__ import annotations

import datetime
from enum import Enum
from typing import Any, Generic, List, Literal, Optional, TypeVar
from pydantic import BaseModel, ConfigDict, Field


# ============================================================================
# 1. ENUMS & CANONICAL TYPES
# ============================================================================

class TaskType(str, Enum):
    """Canonical modeling task types."""
    REGRESSION = "REGRESSION"
    CLASSIFICATION = "CLASSIFICATION"
    UNDETERMINED = "UNDETERMINED"


class RoleType(str, Enum):
    """Canonical user roles (§1.3). Never use role names for logic directly in code."""
    ADMIN = "ADMIN"
    ML_ENGINEER = "ML_ENGINEER"
    DATA_STEWARD = "DATA_STEWARD"
    DEPLOYMENT_MANAGER = "DEPLOYMENT_MANAGER"
    VIEWER = "VIEWER"


class PermissionType(str, Enum):
    """Canonical permissions (§1.3). Authorization primitive is require_permission."""
    READ = "READ"
    EDIT_DATA = "EDIT_DATA"
    TRAIN = "TRAIN"
    DEPLOY = "DEPLOY"
    MANAGE_USERS = "MANAGE_USERS"
    EXPORT = "EXPORT"


class SplitType(str, Enum):
    """Dataset partition types (§2.2, §2.12)."""
    DEVELOPMENT = "DEVELOPMENT"
    LOCKED_TEST = "LOCKED_TEST"
    TEST_REUSED_DIAGNOSTIC = "TEST_REUSED_DIAGNOSTIC"


class FeatureSelectionMethod(str, Enum):
    """Feature selection technique identifiers (§2.7, §8)."""
    CORRELATION = "correlation"
    LASSO = "lasso"
    RANDOM_FOREST = "random_forest"
    PERMUTATION = "permutation"
    # Deferred methods (§8)
    RFE = "rfe"
    SHAP = "shap"


class TechniqueStatus(str, Enum):
    """Feature selection status per fold (§2.7)."""
    APPLIED = "APPLIED"
    SKIPPED = "SKIPPED"
    FAILED = "FAILED"


class FitDiagnosis(str, Enum):
    """Overfitting/Underfitting diagnostic categories (§2.10)."""
    GOOD_FIT = "GOOD_FIT"
    POTENTIAL_OVERFIT = "POTENTIAL_OVERFIT"
    POTENTIAL_UNDERFIT_WEAK_SIGNAL = "POTENTIAL_UNDERFIT_WEAK_SIGNAL"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"


class PayloadLoggingMode(str, Enum):
    """Prediction log payload storage modes (§2.15)."""
    OFF = "OFF"
    HASHED = "HASHED"
    REDACTED = "REDACTED"
    FULL = "FULL"


class RecommendationStatus(str, Enum):
    """Status lifecycle for surfaced recommendations (§2.16)."""
    SUGGESTED = "SUGGESTED"
    ACCEPTED = "ACCEPTED"
    DISMISSED = "DISMISSED"


class ConfidenceLevel(str, Enum):
    """Confidence level for diagnostics and heuristics (§2.4, §2.16)."""
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    AMBIGUOUS = "AMBIGUOUS"


class SelectionDirection(str, Enum):
    """Optimization direction for leaderboard sorting and model selection (§2.9)."""
    MAXIMIZE = "MAXIMIZE"
    MINIMIZE = "MINIMIZE"


# ============================================================================
# 2. ALGORITHM SET (§2.8, §7)
# ============================================================================

class AlgorithmMetadata(BaseModel):
    id: str
    display_name: str
    task_type: TaskType
    is_baseline: bool
    sklearn_class: str
    description: str

    model_config = ConfigDict(frozen=True)


ALGORITHM_SET: dict[str, AlgorithmMetadata] = {
    # Regression Suite
    "linear_regression": AlgorithmMetadata(
        id="linear_regression",
        display_name="Linear Regression",
        task_type=TaskType.REGRESSION,
        is_baseline=True,
        sklearn_class="sklearn.linear_model.LinearRegression",
        description="Standard ordinary least squares regression baseline.",
    ),
    "ridge_regression": AlgorithmMetadata(
        id="ridge_regression",
        display_name="Ridge Regression",
        task_type=TaskType.REGRESSION,
        is_baseline=False,
        sklearn_class="sklearn.linear_model.Ridge",
        description="Linear least squares with L2 regularization.",
    ),
    "random_forest_regressor": AlgorithmMetadata(
        id="random_forest_regressor",
        display_name="Random Forest Regressor",
        task_type=TaskType.REGRESSION,
        is_baseline=False,
        sklearn_class="sklearn.ensemble.RandomForestRegressor",
        description="Ensemble averaging of randomized decision tree regressors.",
    ),
    "gradient_boosting_regressor": AlgorithmMetadata(
        id="gradient_boosting_regressor",
        display_name="Gradient Boosting Regressor",
        task_type=TaskType.REGRESSION,
        is_baseline=False,
        sklearn_class="sklearn.ensemble.GradientBoostingRegressor",
        description="Additive stage-wise gradient boosting regression model.",
    ),
    # Classification Suite
    "logistic_regression": AlgorithmMetadata(
        id="logistic_regression",
        display_name="Logistic Regression",
        task_type=TaskType.CLASSIFICATION,
        is_baseline=True,
        sklearn_class="sklearn.linear_model.LogisticRegression",
        description="Standard regularized logistic regression classification baseline.",
    ),
    "random_forest_classifier": AlgorithmMetadata(
        id="random_forest_classifier",
        display_name="Random Forest Classifier",
        task_type=TaskType.CLASSIFICATION,
        is_baseline=False,
        sklearn_class="sklearn.ensemble.RandomForestClassifier",
        description="Ensemble averaging of randomized decision tree classifiers.",
    ),
    "gradient_boosting_classifier": AlgorithmMetadata(
        id="gradient_boosting_classifier",
        display_name="Gradient Boosting Classifier",
        task_type=TaskType.CLASSIFICATION,
        is_baseline=False,
        sklearn_class="sklearn.ensemble.GradientBoostingClassifier",
        description="Additive stage-wise gradient boosting classification model.",
    ),
}


# ============================================================================
# 3. FEATURE SELECTION DEFAULTS (§2.7, §8)
# ============================================================================

FEATURE_SELECTION_DEFAULTS = {
    "strategy": "TOP_K_PERCENT",
    "alpha": 0.25,                  # Top 25% of ranked features
    "k_min": 5,                     # Minimum number of features to retain
    "k_max": 50,                    # Maximum number of features to retain
    "min_applied_methods": 2,       # Minimum required techniques contributing per fold
    "active_methods": [
        FeatureSelectionMethod.CORRELATION.value,
        FeatureSelectionMethod.LASSO.value,
        FeatureSelectionMethod.RANDOM_FOREST.value,
        FeatureSelectionMethod.PERMUTATION.value,
    ],
    "deferred_methods": [
        FeatureSelectionMethod.RFE.value,
        FeatureSelectionMethod.SHAP.value,
    ],
}


# ============================================================================
# 4. HASHING & IDENTIFIER SEMANTICS (§2.1, §2.17)
# ============================================================================

HASH_ALGORITHM: str = "sha256"
UUID_VERSION: str = "uuid4"

DATASET_SEMANTICS = {
    "dataset_id": "UUIDv4 representing a logical dataset resource (collection of versions)",
    "dataset_version_id": "UUIDv4 representing an immutable physical snapshot",
    "version_number": "Positive monotonically increasing integer starting at 1 per project/dataset",
    "content_hash": "Hex-encoded SHA-256 digest computed over raw uploaded file bytes",
    "deduplication_policy": "Content hash match within project flags identical version or deduplicates",
}


# ============================================================================
# 5. API ROUTING, TIMESTAMPS & PAGINATION
# ============================================================================

API_VERSION_STR: str = "/api/v1"
API_VERSION: str = "v1"

TIMESTAMP_POLICY = {
    "standard": "UTC",
    "format": "ISO-8601",
    "string_pattern": "%Y-%m-%dT%H:%M:%S.%fZ",
}
TIMESTAMP_FORMAT: str = "ISO-8601"

PAGINATION_STRATEGY: str = "cursor-based"
PAGINATION_DEFAULTS = {
    "strategy": PAGINATION_STRATEGY,
    "default_limit": 20,
    "min_limit": 1,
    "max_limit": 100,
    "cursor_encoding": "base64(created_at_iso,id_uuid)",
}


# ============================================================================
# 6. HTTP STATUS CONVENTIONS
# ============================================================================

HTTP_STATUS_CONVENTIONS = {
    "200_OK": "Resource retrieved or updated successfully",
    "201_CREATED": "New resource created successfully (returns representation + id)",
    "204_NO_CONTENT": "Resource deleted or operation completed with empty response body",
    "400_BAD_REQUEST": "Malformed payload or violation of domain pre-condition",
    "401_UNAUTHORIZED": "Authentication token missing, expired, or malformed",
    "403_FORBIDDEN": "Caller lacks required permission for this operation",
    "404_NOT_FOUND": "Requested entity identifier does not exist",
    "409_CONFLICT": "State conflict (e.g. unique violation, consumed locked-test partition)",
    "422_UNPROCESSABLE_ENTITY": "Pydantic schema validation failure or parameter type mismatch",
    "500_INTERNAL_SERVER_ERROR": "Unexpected unhandled server-side error",
}


# ============================================================================
# 7. CANONICAL ERROR RESPONSE SCHEMA (RFC 7807 COMPATIBLE)
# ============================================================================

class ErrorDetail(BaseModel):
    field: Optional[str] = Field(default=None, description="Path or parameter where error occurred")
    message: str = Field(..., description="Human-readable description of the specific issue")
    code: Optional[str] = Field(default=None, description="Granular error classification code")


class ErrorBody(BaseModel):
    code: str = Field(..., description="High-level machine-readable error classification")
    message: str = Field(..., description="Summary human-readable message")
    details: List[ErrorDetail] = Field(default_factory=list, description="Granular error details")
    request_id: str = Field(..., description="Unique UUIDv4 correlation trace ID")
    timestamp: str = Field(..., description="UTC ISO-8601 timestamp when error occurred")


class ErrorResponse(BaseModel):
    """Single canonical top-level error response envelope."""
    error: ErrorBody

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "error": {
                    "code": "RESOURCE_NOT_FOUND",
                    "message": "Dataset version with ID '9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d' was not found.",
                    "details": [],
                    "request_id": "550e8400-e29b-41d4-a716-446655440000",
                    "timestamp": "2026-09-06T12:00:00.000000Z",
                }
            }
        }
    )


# ============================================================================
# 8. CURSOR PAGINATION SCHEMAS
# ============================================================================

T = TypeVar("T")


class CursorPaginationParams(BaseModel):
    cursor: Optional[str] = Field(default=None, description="Opaque pagination cursor token")
    limit: int = Field(
        default=PAGINATION_DEFAULTS["default_limit"],
        ge=PAGINATION_DEFAULTS["min_limit"],
        le=PAGINATION_DEFAULTS["max_limit"],
        description="Number of items to fetch",
    )


class CursorPaginationResponse(BaseModel, Generic[T]):
    items: List[T] = Field(..., description="List of retrieved records")
    next_cursor: Optional[str] = Field(default=None, description="Cursor for the subsequent page")
    prev_cursor: Optional[str] = Field(default=None, description="Cursor for the preceding page")
    has_more: bool = Field(..., description="True if subsequent pages exist")
    total_count: Optional[int] = Field(default=None, description="Total count if requested/cached")


# ============================================================================
# 9. METRIC-NAMING STRINGS (§2.9)
# ============================================================================

METRICS = {
    TaskType.REGRESSION: {
        "rmse": {"display_name": "Root Mean Squared Error", "direction": SelectionDirection.MINIMIZE, "is_primary_candidate": True},
        "mae": {"display_name": "Mean Absolute Error", "direction": SelectionDirection.MINIMIZE, "is_primary_candidate": True},
        "mse": {"display_name": "Mean Squared Error", "direction": SelectionDirection.MINIMIZE, "is_primary_candidate": False},
        "r2": {"display_name": "R-squared Score", "direction": SelectionDirection.MAXIMIZE, "is_primary_candidate": False},
        "adjusted_r2": {"display_name": "Adjusted R-squared Score", "direction": SelectionDirection.MAXIMIZE, "is_primary_candidate": False},
    },
    TaskType.CLASSIFICATION: {
        "macro_f1": {"display_name": "Macro-Averaged F1 Score", "direction": SelectionDirection.MAXIMIZE, "is_primary_candidate": True},
        "weighted_f1": {"display_name": "Weighted-Averaged F1 Score", "direction": SelectionDirection.MAXIMIZE, "is_primary_candidate": True},
        "accuracy": {"display_name": "Accuracy", "direction": SelectionDirection.MAXIMIZE, "is_primary_candidate": False},
        "precision": {"display_name": "Precision (Weighted)", "direction": SelectionDirection.MAXIMIZE, "is_primary_candidate": False},
        "recall": {"display_name": "Recall (Weighted)", "direction": SelectionDirection.MAXIMIZE, "is_primary_candidate": False},
        "roc_auc": {"display_name": "Area Under ROC Curve (OvR)", "direction": SelectionDirection.MAXIMIZE, "is_primary_candidate": False},
        "log_loss": {"display_name": "Logarithmic Cross-Entropy Loss", "direction": SelectionDirection.MINIMIZE, "is_primary_candidate": False},
        "confusion_matrix": {"display_name": "Confusion Matrix Array", "direction": None, "is_primary_candidate": False},
    },
}

PRIMARY_METRIC_DEFAULTS = {
    TaskType.REGRESSION: "rmse",
    TaskType.CLASSIFICATION: "macro_f1",
}


# ============================================================================
# 10. STORAGE DIRECTORY STRUCTURE & ARTIFACT NAMING SCHEME (§1.1, §2.17)
# ============================================================================

STORAGE_DIRECTORIES = {
    "root": "/data",
    "datasets": "datasets/{project_id}",
    "splits": "splits/{experiment_id}",
    "preprocessors": "preprocessors/{experiment_id}",
    "models": "models/{experiment_id}",
    "reports": "reports/{experiment_id}",
    "shap": "shap/{experiment_id}",
    "scratch": "scratch/{experiment_id}",
}

ARTIFACT_NAMING_PATTERNS = {
    "raw_dataset": "{dataset_id}_v{version}_{hash_prefix}.{ext}",
    "split_indices": "split_indices_{split_type}_{split_seed}.json",
    "preprocessing_pipeline": "preprocessor_pipeline_{snapshot_id}.joblib",
    "feature_selection_snapshot": "feature_selection_snapshot_{snapshot_id}.json",
    "trained_model": "model_{model_id}_{algorithm}.joblib",
    "evaluation_report": "evaluation_{split_type}_{model_id}.json",
    "shap_summary": "shap_global_{model_id}.joblib",
}


# ============================================================================
# 11. REPRODUCIBILITY TOLERANCE & LINEAGE (§2.17, §3)
# ============================================================================

REPRODUCIBILITY_TOLERANCE = {
    "metric_absolute_tolerance": 1e-3,      # 0.001 max absolute metric discrepancy
    "metric_relative_tolerance": 0.01,      # 1.0% max relative metric discrepancy
    "environment_keys": [
        "dataset_content_hash",
        "split_seed",
        "cv_seed",
        "cv_strategy",
        "fold_count",
        "code_version",
        "python_version",
        "sklearn_version",
        "numpy_version",
        "pandas_version",
        "model_library_versions",
    ],
}
