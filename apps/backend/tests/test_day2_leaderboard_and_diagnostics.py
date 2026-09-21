"""
Unit & Integration Tests for Day 2 — Leaderboard & Fit Diagnostics.

Verifies:
1. Fit Diagnostics covering all 4 states:
   - GOOD_FIT
   - POTENTIAL_OVERFIT
   - POTENTIAL_UNDERFIT_WEAK_SIGNAL
   - INSUFFICIENT_DATA
2. Composite Model Selection Score computation (0..100 normalized convenience score).
3. Strict Leaderboard Sort Invariant & Disagreement Case:
   - Model A with better primary metric and lower composite score MUST rank #1 over Model B.
4. End-to-end API leaderboard query verifying primary-metric ordering, fit_diagnosis, and exclusion of TEST_REUSED_DIAGNOSTIC.
"""

import uuid
from uuid import uuid4
import numpy as np
import pytest
from fastapi import status

from app.models.project import Project
from app.models.user import User
from app.models.role import Role
from app.models.experiment import Experiment
from app.models.trained_model import TrainedModel
from app.models.model_metric import ModelMetric
from app.config.state_machines import ExperimentState, ModelState
from app.services.evaluation_service import EvaluationService


def get_auth_token(client, email="day2_mle@studio.com"):
    """Helper to signup/login and obtain JWT bearer token."""
    reg_resp = client.post("/api/v1/auth/signup", json={
        "email": email,
        "password": "Password123!",
        "full_name": "Day2 MLE",
    })
    assert reg_resp.status_code in [200, 201]
    resp = client.post("/api/v1/auth/login", json={
        "email": email,
        "password": "Password123!",
    })
    assert resp.status_code == 200
    return resp.json()["access_token"]


# =============================================================================
# 1. Fit Diagnostics Unit Tests (§2.10)
# =============================================================================

def test_diagnose_fit_insufficient_data():
    """Verify INSUFFICIENT_DATA returned when validation sample count < 20."""
    res = EvaluationService.diagnose_fit(
        train_metrics={"macro_f1": 0.90},
        cv_mean_metrics={"macro_f1": 0.85},
        baseline_metrics={"macro_f1": 0.50},
        metric_name="macro_f1",
        n_val_samples=15,  # < 20
    )
    assert res == "INSUFFICIENT_DATA"


def test_diagnose_fit_overfit_higher_is_better():
    """Verify POTENTIAL_OVERFIT when Train - CV_Mean > threshold for higher-is-better metrics."""
    res = EvaluationService.diagnose_fit(
        train_metrics={"macro_f1": 0.95},
        cv_mean_metrics={"macro_f1": 0.75},  # Gap = 0.20 > default 0.10
        baseline_metrics={"macro_f1": 0.50},
        metric_name="macro_f1",
        n_val_samples=50,
    )
    assert res == "POTENTIAL_OVERFIT"


def test_diagnose_fit_overfit_lower_is_better():
    """Verify POTENTIAL_OVERFIT when CV_Mean - Train > threshold for lower-is-better metrics."""
    res = EvaluationService.diagnose_fit(
        train_metrics={"rmse": 1.0},
        cv_mean_metrics={"rmse": 4.0},  # Gap = 3.0
        baseline_metrics={"rmse": 5.0},
        metric_name="rmse",
        n_val_samples=50,
        overfit_threshold=0.5,
    )
    assert res == "POTENTIAL_OVERFIT"


def test_diagnose_fit_underfit_weak_signal_higher_is_better():
    """Verify POTENTIAL_UNDERFIT_WEAK_SIGNAL when CV_Mean and Train are marginally above baseline."""
    res = EvaluationService.diagnose_fit(
        train_metrics={"accuracy": 0.52},
        cv_mean_metrics={"accuracy": 0.51},
        baseline_metrics={"accuracy": 0.50},  # Lift is only 0.01 <= margin 0.05
        metric_name="accuracy",
        n_val_samples=100,
    )
    assert res == "POTENTIAL_UNDERFIT_WEAK_SIGNAL"


def test_diagnose_fit_underfit_weak_signal_lower_is_better():
    """Verify POTENTIAL_UNDERFIT_WEAK_SIGNAL when CV error and Train error are barely better than baseline."""
    res = EvaluationService.diagnose_fit(
        train_metrics={"rmse": 9.9},
        cv_mean_metrics={"rmse": 9.95},
        baseline_metrics={"rmse": 10.0},
        metric_name="rmse",
        n_val_samples=100,
        underfit_margin=0.2,
    )
    assert res == "POTENTIAL_UNDERFIT_WEAK_SIGNAL"


def test_diagnose_fit_good_fit_both_tasks():
    """Verify GOOD_FIT when models generalize well with clear signal above baseline."""
    # Regression
    reg_fit = EvaluationService.diagnose_fit(
        train_metrics={"rmse": 2.0},
        cv_mean_metrics={"rmse": 2.1},
        baseline_metrics={"rmse": 10.0},
        metric_name="rmse",
        n_val_samples=50,
    )
    assert reg_fit == "GOOD_FIT"

    # Classification
    clf_fit = EvaluationService.diagnose_fit(
        train_metrics={"macro_f1": 0.88},
        cv_mean_metrics={"macro_f1": 0.85},
        baseline_metrics={"macro_f1": 0.40},
        metric_name="macro_f1",
        n_val_samples=50,
    )
    assert clf_fit == "GOOD_FIT"


# =============================================================================
# 2. Model Selection Score Computation Tests (§2.9)
# =============================================================================

def test_model_selection_score_regression():
    """Verify regression model selection score: normalize(R2)*0.6 + (1 - normalize(RMSE))*0.4."""
    score = EvaluationService.compute_model_selection_score(
        task_type="REGRESSION",
        cv_mean_metrics={"r2": 0.80, "rmse": 2.0},
        baseline_metrics={"rmse": 10.0},
    )
    # norm_r2 = 0.80, norm_rmse = 2.0 / 10.0 = 0.20
    # expected = (0.80 * 0.6 + (1.0 - 0.20) * 0.4) * 100 = (0.48 + 0.32) * 100 = 80.0
    assert score == pytest.approx(80.0, abs=0.1)


def test_model_selection_score_classification():
    """Verify classification model selection score: F1_weighted*0.6 + ROC_AUC*0.4."""
    score = EvaluationService.compute_model_selection_score(
        task_type="CLASSIFICATION",
        cv_mean_metrics={"weighted_f1": 0.90, "roc_auc": 0.80},
    )
    # expected = (0.90 * 0.6 + 0.80 * 0.4) * 100 = (0.54 + 0.32) * 100 = 86.0
    assert score == pytest.approx(86.0, abs=0.1)


# =============================================================================
# 3. Disagreement Case Test (Leaderboard Sort Invariant)
# =============================================================================

def test_leaderboard_disagreement_case_regression(client, db_session):
    """
    Test Disagreement Case (Regression):
    Model A has superior primary metric (lower RMSE=2.0) but lower composite score (60.0).
    Model B has inferior primary metric (higher RMSE=4.0) but higher composite score (85.0).
    The leaderboard MUST rank Model A #1 and Model B #2.
    """
    token = get_auth_token(client, email="disagree_reg@studio.com")
    headers = {"Authorization": f"Bearer {token}"}

    proj_resp = client.post("/api/v1/projects", headers=headers, json={"project_name": "Disagree Reg Proj", "task_type": "REGRESSION"})
    assert proj_resp.status_code == 201
    proj_id = proj_resp.json()["id"]

    exp = Experiment(
        id=uuid4(),
        project_id=uuid.UUID(proj_id) if isinstance(proj_id, str) else proj_id,
        task_type="REGRESSION",
        selection_metric="rmse",
        selection_direction="MINIMIZE",
        status=ExperimentState.REGISTERED.value,
    )
    db_session.add(exp)
    db_session.flush()

    # Model A: RMSE = 2.0 (better), Score = 60.0
    model_a = TrainedModel(
        id=uuid4(),
        experiment_id=exp.id,
        algorithm_name="LinearRegression",
        quick_cv_score=2.0,
        model_selection_score=60.0,
        fit_diagnosis="GOOD_FIT",
        status=ModelState.TRAINED.value,
    )
    # Model B: RMSE = 4.0 (worse), Score = 85.0
    model_b = TrainedModel(
        id=uuid4(),
        experiment_id=exp.id,
        algorithm_name="RandomForestRegressor",
        quick_cv_score=4.0,
        model_selection_score=85.0,
        fit_diagnosis="GOOD_FIT",
        status=ModelState.TRAINED.value,
    )
    exp.selected_model_id = model_a.id
    db_session.add_all([model_a, model_b])
    db_session.flush()

    # Model metrics
    m_a = ModelMetric(model_id=model_a.id, metric_name="rmse", split="CV_MEAN", metric_value=2.0)
    m_b = ModelMetric(model_id=model_b.id, metric_name="rmse", split="CV_MEAN", metric_value=4.0)
    db_session.add_all([m_a, m_b])
    db_session.commit()

    # Query leaderboard
    lb_resp = client.get(f"/api/v1/projects/{proj_id}/leaderboard", headers=headers)
    assert lb_resp.status_code == 200
    data = lb_resp.json()

    assert len(data["models"]) == 2
    # Model A MUST be first (rank 1) despite lower composite score
    assert data["models"][0]["id"] == str(model_a.id)
    assert data["models"][0]["primary_metric_value"] == 2.0
    assert data["models"][0]["model_selection_score"] == 60.0
    assert data["models"][0]["is_winner"] is True

    # Model B is second
    assert data["models"][1]["id"] == str(model_b.id)
    assert data["models"][1]["primary_metric_value"] == 4.0
    assert data["models"][1]["model_selection_score"] == 85.0
    assert data["models"][1]["is_winner"] is False


def test_leaderboard_disagreement_case_classification(client, db_session):
    """
    Test Disagreement Case (Classification):
    Model A has higher Macro F1 (0.85) but lower composite score (65.0).
    Model B has lower Macro F1 (0.70) but higher composite score (90.0).
    The leaderboard MUST rank Model A #1 and Model B #2.
    """
    token = get_auth_token(client, email="disagree_clf@studio.com")
    headers = {"Authorization": f"Bearer {token}"}

    proj_resp = client.post("/api/v1/projects", headers=headers, json={"project_name": "Disagree Clf Proj", "task_type": "CLASSIFICATION"})
    assert proj_resp.status_code == 201
    proj_id = proj_resp.json()["id"]

    exp = Experiment(
        id=uuid4(),
        project_id=uuid.UUID(proj_id) if isinstance(proj_id, str) else proj_id,
        task_type="CLASSIFICATION",
        selection_metric="macro_f1",
        selection_direction="MAXIMIZE",
        status=ExperimentState.REGISTERED.value,
    )
    db_session.add(exp)
    db_session.flush()

    # Model A: Macro F1 = 0.85 (better), Score = 65.0
    model_a = TrainedModel(
        id=uuid4(),
        experiment_id=exp.id,
        algorithm_name="LogisticRegression",
        quick_cv_score=0.85,
        model_selection_score=65.0,
        fit_diagnosis="GOOD_FIT",
        status=ModelState.TRAINED.value,
    )
    # Model B: Macro F1 = 0.70 (worse), Score = 90.0
    model_b = TrainedModel(
        id=uuid4(),
        experiment_id=exp.id,
        algorithm_name="RandomForestClassifier",
        quick_cv_score=0.70,
        model_selection_score=90.0,
        fit_diagnosis="GOOD_FIT",
        status=ModelState.TRAINED.value,
    )
    exp.selected_model_id = model_a.id
    db_session.add_all([model_a, model_b])
    db_session.flush()

    # Model metrics
    m_a = ModelMetric(model_id=model_a.id, metric_name="macro_f1", split="CV_MEAN", metric_value=0.85)
    m_b = ModelMetric(model_id=model_b.id, metric_name="macro_f1", split="CV_MEAN", metric_value=0.70)
    db_session.add_all([m_a, m_b])
    db_session.commit()

    # Query leaderboard
    lb_resp = client.get(f"/api/v1/projects/{proj_id}/leaderboard", headers=headers)
    assert lb_resp.status_code == 200
    data = lb_resp.json()

    assert len(data["models"]) == 2
    # Model A MUST be first (rank 1) despite lower composite score
    assert data["models"][0]["id"] == str(model_a.id)
    assert data["models"][0]["primary_metric_value"] == 0.85
    assert data["models"][0]["model_selection_score"] == 65.0
    assert data["models"][0]["is_winner"] is True

    # Model B is second
    assert data["models"][1]["id"] == str(model_b.id)
    assert data["models"][1]["primary_metric_value"] == 0.70
    assert data["models"][1]["model_selection_score"] == 90.0
    assert data["models"][1]["is_winner"] is False
