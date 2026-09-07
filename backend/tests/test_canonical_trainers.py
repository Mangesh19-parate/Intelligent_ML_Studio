"""
Unit Tests for Day 5 Canonical Algorithm Names & BaseModelTrainer / RegressionTrainer / ClassificationTrainer (SRS v9 §2.8 & Architecture Contract §2).

Verifies:
1. Canonical algorithm catalog:
   - Regression: LinearRegression, Ridge, RandomForestRegressor, GradientBoostingRegressor
   - Classification: LogisticRegression, RandomForestClassifier, GradientBoostingClassifier
2. Strict prohibition and rejection of bare 'RF' anywhere.
3. Proper canonical resolution across casing and aliases (snake_case, Title Case, etc.).
4. Cross-task rejection (e.g. LogisticRegression in RegressionTrainer).
5. Fresh, unfit pipeline generation from get_pipeline().
6. End-to-end fit, predict, and predict_proba execution.
"""

import numpy as np
import pytest
from sklearn.pipeline import Pipeline
from sklearn.linear_model import LinearRegression, Ridge, LogisticRegression
from sklearn.ensemble import (
    RandomForestRegressor,
    RandomForestClassifier,
    GradientBoostingRegressor,
    GradientBoostingClassifier,
)

from app.services.trainers import (
    BaseModelTrainer,
    RegressionTrainer,
    ClassificationTrainer,
    FeatureSelector,
)


# =============================================================================
# 1. Regression Canonical Names & Resolution
# =============================================================================

@pytest.mark.parametrize(
    "alias,expected_canonical,expected_cls",
    [
        ("LinearRegression", "LinearRegression", LinearRegression),
        ("linear_regression", "LinearRegression", LinearRegression),
        ("Linear Regression", "LinearRegression", LinearRegression),
        ("linearregression", "LinearRegression", LinearRegression),
        ("Ridge", "Ridge", Ridge),
        ("ridge", "Ridge", Ridge),
        ("ridge_regression", "Ridge", Ridge),
        ("Ridge Regression", "Ridge", Ridge),
        ("RidgeRegression", "Ridge", Ridge),
        ("RandomForestRegressor", "RandomForestRegressor", RandomForestRegressor),
        ("random_forest_regressor", "RandomForestRegressor", RandomForestRegressor),
        ("Random Forest Regressor", "RandomForestRegressor", RandomForestRegressor),
        ("Random Forest", "RandomForestRegressor", RandomForestRegressor),
        ("GradientBoostingRegressor", "GradientBoostingRegressor", GradientBoostingRegressor),
        ("gradient_boosting_regressor", "GradientBoostingRegressor", GradientBoostingRegressor),
        ("Gradient Boosting Regressor", "GradientBoostingRegressor", GradientBoostingRegressor),
        ("Gradient Boosting", "GradientBoostingRegressor", GradientBoostingRegressor),
    ],
)
def test_regression_canonical_resolution(alias, expected_canonical, expected_cls):
    """Test all valid aliases resolve to canonical name and correct scikit-learn class."""
    assert RegressionTrainer.is_supported(alias) is True
    assert RegressionTrainer.to_canonical_name(alias) == expected_canonical

    trainer = RegressionTrainer(alias, random_state=42)
    assert trainer.task_type == "REGRESSION"
    assert trainer.canonical_name == expected_canonical
    assert isinstance(trainer.get_estimator(), expected_cls)


def test_regression_supported_algorithms_list():
    """Verify get_supported_algorithms returns the expected canonical set."""
    supported = RegressionTrainer.get_supported_algorithms()
    assert supported == [
        "GradientBoostingRegressor",
        "LinearRegression",
        "RandomForestRegressor",
        "Ridge",
    ]


# =============================================================================
# 2. Classification Canonical Names & Resolution
# =============================================================================

@pytest.mark.parametrize(
    "alias,expected_canonical,expected_cls",
    [
        ("LogisticRegression", "LogisticRegression", LogisticRegression),
        ("logistic_regression", "LogisticRegression", LogisticRegression),
        ("Logistic Regression", "LogisticRegression", LogisticRegression),
        ("logisticregression", "LogisticRegression", LogisticRegression),
        ("RandomForestClassifier", "RandomForestClassifier", RandomForestClassifier),
        ("random_forest_classifier", "RandomForestClassifier", RandomForestClassifier),
        ("Random Forest Classifier", "RandomForestClassifier", RandomForestClassifier),
        ("Random Forest", "RandomForestClassifier", RandomForestClassifier),
        ("GradientBoostingClassifier", "GradientBoostingClassifier", GradientBoostingClassifier),
        ("gradient_boosting_classifier", "GradientBoostingClassifier", GradientBoostingClassifier),
        ("Gradient Boosting Classifier", "GradientBoostingClassifier", GradientBoostingClassifier),
        ("Gradient Boosting", "GradientBoostingClassifier", GradientBoostingClassifier),
    ],
)
def test_classification_canonical_resolution(alias, expected_canonical, expected_cls):
    """Test all valid classification aliases resolve to canonical name and correct scikit-learn class."""
    assert ClassificationTrainer.is_supported(alias) is True
    assert ClassificationTrainer.to_canonical_name(alias) == expected_canonical

    trainer = ClassificationTrainer(alias, random_state=42)
    assert trainer.task_type == "CLASSIFICATION"
    assert trainer.canonical_name == expected_canonical
    assert isinstance(trainer.get_estimator(), expected_cls)


def test_classification_supported_algorithms_list():
    """Verify get_supported_algorithms returns the expected canonical set."""
    supported = ClassificationTrainer.get_supported_algorithms()
    assert supported == [
        "GradientBoostingClassifier",
        "LogisticRegression",
        "RandomForestClassifier",
    ]


# =============================================================================
# 3. Strict Prohibition of Bare 'RF'
# =============================================================================

@pytest.mark.parametrize("bare_rf", ["RF", "rf", "Rf", "rf_regressor", "rf_classifier"])
def test_strict_prohibition_of_bare_rf(bare_rf):
    """
    CRITICAL GROUND RULE:
    Bare 'RF' is strictly prohibited across all trainers and must raise ValueError
    with an explicit diagnostic message instructing canonical name usage.
    """
    assert RegressionTrainer.is_supported(bare_rf) is False
    assert ClassificationTrainer.is_supported(bare_rf) is False

    with pytest.raises(ValueError, match="Prohibited bare abbreviation"):
        RegressionTrainer(bare_rf)

    with pytest.raises(ValueError, match="Prohibited bare abbreviation"):
        ClassificationTrainer(bare_rf)

    with pytest.raises(ValueError, match="Prohibited bare abbreviation"):
        RegressionTrainer.to_canonical_name(bare_rf)

    with pytest.raises(ValueError, match="Prohibited bare abbreviation"):
        ClassificationTrainer.to_canonical_name(bare_rf)


# =============================================================================
# 4. Unknown & Cross-Task Rejection
# =============================================================================

@pytest.mark.parametrize(
    "invalid_name",
    ["XGBoost", "LightGBM", "CatBoost", "NeuralNet", "SVM", "DecisionTree", "invalid", "", None],
)
def test_unsupported_algorithm_names_rejected(invalid_name):
    """Verify unknown or empty algorithm names are rejected."""
    assert RegressionTrainer.is_supported(invalid_name) is False
    assert ClassificationTrainer.is_supported(invalid_name) is False

    with pytest.raises(ValueError):
        RegressionTrainer(invalid_name)

    with pytest.raises(ValueError):
        ClassificationTrainer(invalid_name)


def test_cross_task_algorithm_rejection():
    """Verify classification algorithms are rejected in RegressionTrainer and vice versa."""
    # Classification model passed to RegressionTrainer
    with pytest.raises(ValueError, match="Unsupported regression algorithm"):
        RegressionTrainer("LogisticRegression")

    with pytest.raises(ValueError, match="Unsupported regression algorithm"):
        RegressionTrainer("RandomForestClassifier")

    # Regression model passed to ClassificationTrainer
    with pytest.raises(ValueError, match="Unsupported classification algorithm"):
        ClassificationTrainer("LinearRegression")

    with pytest.raises(ValueError, match="Unsupported classification algorithm"):
        ClassificationTrainer("Ridge")

    with pytest.raises(ValueError, match="Unsupported classification algorithm"):
        ClassificationTrainer("RandomForestRegressor")


# =============================================================================
# 5. Pipeline Freshness & Architecture
# =============================================================================

def test_pipeline_generation_freshness():
    """
    Verifies that get_pipeline() returns fresh, unfit Pipeline instances
    combining transformer, selector, and estimator.
    """
    trainer = RegressionTrainer("Ridge", hyperparameters={"alpha": 2.5}, random_state=123)
    pipe1 = trainer.get_pipeline()
    pipe2 = trainer.get_pipeline()

    assert isinstance(pipe1, Pipeline)
    assert isinstance(pipe2, Pipeline)
    assert pipe1 is not pipe2
    assert pipe1.named_steps["estimator"] is not pipe2.named_steps["estimator"]

    # Fit pipe1 on dummy data and verify pipe2 remains unfit
    X = np.array([[1.0, 2.0], [3.0, 4.0], [5.0, 6.0]])
    y = np.array([10.0, 20.0, 30.0])
    pipe1.fit(X, y)

    assert hasattr(pipe1.named_steps["estimator"], "coef_")
    assert not hasattr(pipe2.named_steps["estimator"], "coef_")


# =============================================================================
# 6. End-to-End Fit & Predict on All Canonical Algorithms
# =============================================================================

def test_end_to_end_regression_algorithms():
    """Verify all canonical regression algorithms fit and predict accurately."""
    np.random.seed(42)
    X = np.random.randn(50, 4)
    y = 2.0 * X[:, 0] + 0.5 * X[:, 1] + np.random.randn(50) * 0.1

    for alg in RegressionTrainer.get_supported_algorithms():
        trainer = RegressionTrainer(alg, random_state=42)
        trainer.fit(X, y)
        preds = trainer.predict(X)
        assert len(preds) == 50
        assert trainer.predict_proba(X) is None  # Regression has no predict_proba


def test_end_to_end_classification_algorithms():
    """Verify all canonical classification algorithms fit, predict, and predict_proba."""
    np.random.seed(42)
    X = np.random.randn(60, 4)
    y = (X[:, 0] + X[:, 1] > 0).astype(int)

    for alg in ClassificationTrainer.get_supported_algorithms():
        trainer = ClassificationTrainer(alg, random_state=42)
        trainer.fit(X, y)
        preds = trainer.predict(X)
        assert len(preds) == 60
        proba = trainer.predict_proba(X)
        assert proba is not None
        assert proba.shape == (60, 2)
        assert np.allclose(proba.sum(axis=1), 1.0)
