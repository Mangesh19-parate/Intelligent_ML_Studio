"""
Unit tests for ML Studio Architecture Contract.
Validates constants, enums, serialization schemas, and tolerance definitions.
"""

import pytest
from app.config.contract import (
    ALGORITHM_SET,
    FEATURE_SELECTION_DEFAULTS,
    HASH_ALGORITHM,
    API_VERSION_STR,
    API_VERSION,
    TIMESTAMP_FORMAT,
    UUID_VERSION,
    PAGINATION_DEFAULTS,
    HTTP_STATUS_CONVENTIONS,
    METRICS,
    PRIMARY_METRIC_DEFAULTS,
    ARTIFACT_NAMING_PATTERNS,
    STORAGE_DIRECTORIES,
    REPRODUCIBILITY_TOLERANCE,
    TaskType,
    RoleType,
    PermissionType,
    SplitType,
    FeatureSelectionMethod,
    FitDiagnosis,
    PayloadLoggingMode,
    RecommendationStatus,
    ConfidenceLevel,
    SelectionDirection,
    ErrorResponse,
    ErrorBody,
    ErrorDetail,
    CursorPaginationResponse,
    CursorPaginationParams,
)


def test_algorithm_set_composition():
    """Verify algorithm catalog contains expected models and canonical metadata."""
    assert len(ALGORITHM_SET) >= 6
    
    # Check Regression Suite
    regression_algos = [k for k, v in ALGORITHM_SET.items() if v.task_type == TaskType.REGRESSION]
    assert "linear_regression" in regression_algos
    assert "ridge_regression" in regression_algos
    assert "random_forest_regressor" in regression_algos
    assert "gradient_boosting_regressor" in regression_algos
    
    # Check Classification Suite
    classification_algos = [k for k, v in ALGORITHM_SET.items() if v.task_type == TaskType.CLASSIFICATION]
    assert "logistic_regression" in classification_algos
    assert "random_forest_classifier" in classification_algos
    assert "gradient_boosting_classifier" in classification_algos

    # Baseline flags
    assert ALGORITHM_SET["linear_regression"].is_baseline is True
    assert ALGORITHM_SET["logistic_regression"].is_baseline is True
    assert ALGORITHM_SET["random_forest_classifier"].is_baseline is False


def test_feature_selection_defaults():
    """Verify feature selection parameters adhere to the specification."""
    assert FEATURE_SELECTION_DEFAULTS["strategy"] == "TOP_K_PERCENT"
    assert FEATURE_SELECTION_DEFAULTS["alpha"] == 0.25
    assert FEATURE_SELECTION_DEFAULTS["k_min"] == 5
    assert FEATURE_SELECTION_DEFAULTS["k_max"] == 50
    assert FEATURE_SELECTION_DEFAULTS["min_applied_methods"] == 2
    assert len(FEATURE_SELECTION_DEFAULTS["active_methods"]) == 4
    assert len(FEATURE_SELECTION_DEFAULTS["deferred_methods"]) == 2


def test_hash_and_versioning_policy():
    """Verify hashing, UUID and API versioning parameters."""
    assert HASH_ALGORITHM == "sha256"
    assert UUID_VERSION == "uuid4"
    assert API_VERSION_STR == "/api/v1"
    assert API_VERSION == "v1"
    assert TIMESTAMP_FORMAT == "ISO-8601"


def test_reproducibility_tolerances():
    """Verify tolerance constants and environment lineage requirements."""
    assert REPRODUCIBILITY_TOLERANCE["metric_absolute_tolerance"] == 1e-3
    assert REPRODUCIBILITY_TOLERANCE["metric_relative_tolerance"] == 0.01
    assert "dataset_content_hash" in REPRODUCIBILITY_TOLERANCE["environment_keys"]
    assert "split_seed" in REPRODUCIBILITY_TOLERANCE["environment_keys"]
    assert "code_version" in REPRODUCIBILITY_TOLERANCE["environment_keys"]


def test_metrics_definition():
    """Verify metrics catalog for both regression and classification."""
    reg_metrics = METRICS[TaskType.REGRESSION]
    assert "rmse" in reg_metrics
    assert "mae" in reg_metrics
    assert reg_metrics["rmse"]["direction"] == SelectionDirection.MINIMIZE
    assert PRIMARY_METRIC_DEFAULTS[TaskType.REGRESSION] == "rmse"

    clf_metrics = METRICS[TaskType.CLASSIFICATION]
    assert "macro_f1" in clf_metrics
    assert "weighted_f1" in clf_metrics
    assert clf_metrics["macro_f1"]["direction"] == SelectionDirection.MAXIMIZE
    assert PRIMARY_METRIC_DEFAULTS[TaskType.CLASSIFICATION] == "macro_f1"


def test_error_response_schema():
    """Verify canonical error response schema serialization."""
    err = ErrorResponse(
        error=ErrorBody(
            code="RESOURCE_NOT_FOUND",
            message="Item not found",
            details=[ErrorDetail(field="id", message="Invalid ID", code="NOT_FOUND")],
            request_id="1234-uuid",
            timestamp="2026-09-06T12:00:00Z",
        )
    )
    dumped = err.model_dump()
    assert dumped["error"]["code"] == "RESOURCE_NOT_FOUND"
    assert len(dumped["error"]["details"]) == 1
    assert dumped["error"]["request_id"] == "1234-uuid"


def test_cursor_pagination_schema():
    """Verify cursor pagination response schema."""
    paginated = CursorPaginationResponse[str](
        items=["item1", "item2"],
        next_cursor="cursor_abc",
        prev_cursor=None,
        has_more=True,
        total_count=100,
    )
    assert len(paginated.items) == 2
    assert paginated.has_more is True
    assert paginated.next_cursor == "cursor_abc"
