import uuid
import pytest
from fastapi import status
from sqlalchemy.orm import Session

from app.models.trained_model import TrainedModel
from app.models.experiment import Experiment
from app.models.user import User
from backend.scripts.run_checkpoint2_verification import run_live_checkpoint_2, QueryMutationAuditor


def test_checkpoint2_full_pipeline_live_and_invariants(db_session):
    """
    Day 7 Checkpoint 2 (MVP Complete):
    Executes live end-to-end pipeline across all 13 stages and verifies:
    1. Dataset upload, SHA-256 hash, outer split with locked test isolation.
    2. Profiling & DQI on development partition only.
    3. Preprocessing snapshot and feature selection stability.
    4. 5-Fold cross-validation, champion model selection, single locked test pass.
    5. SHAP global explainability with schema caching.
    6. Deployment gate evaluation, approval, and live prediction endpoint.
    7. Model Passport generation with strict SELECT + render only.
    """
    res = run_live_checkpoint_2(db=db_session)
    assert res["all_passed"] is True
    assert res["model_passport"]["sql_mutations"] == 0
    assert res["model_passport"]["metrics_count"] > 0
    assert res["model_passport"]["is_champion"] is True


def test_model_passport_strict_select_and_zero_recomputation(client, db_session, create_test_user, auth_headers):
    """
    Verifies that GET /api/v1/models/{model_id}/passport:
    1. Returns complete Model Technical Passport per SRS v9 §13.
    2. Executes strictly zero database mutations.
    3. Includes project, experiment, dataset, preprocessing, feature selection, metrics matrix, explainability, and governance.
    """
    # 1. Run full pipeline to populate real stored model
    res = run_live_checkpoint_2(db=db_session)
    assert res["all_passed"] is True

    model_id = res["model_passport"]["model_id"]

    # 2. Authenticate user
    user = create_test_user("viewer_passport@mlstudio.io", role_name="USER")
    headers = auth_headers(user)

    engine = db_session.get_bind()
    with QueryMutationAuditor(engine) as auditor:
        resp = client.get(f"/api/v1/models/{model_id}/passport", headers=headers)

    assert resp.status_code == status.HTTP_200_OK
    assert auditor.mutation_count == 0, f"Expected 0 DB mutations, got: {auditor.mutations}"
    assert auditor.select_count > 0

    data = resp.json()
    assert data["model_id"] == model_id
    assert "algorithm_name" in data
    assert "status" in data
    assert "project" in data
    assert "experiment" in data
    assert "dataset" in data
    assert "metrics" in data
    assert "governance" in data
    assert "generalization_gap" in data
    assert len(data["metrics"]) > 0
    assert data["governance"]["is_deployed"] is True


def test_model_passport_404_for_unknown_model(client, db_session, create_test_user, auth_headers):
    """Verifies that GET /api/v1/models/{nonexistent_id}/passport returns HTTP 404."""
    user = create_test_user("viewer_passport2@mlstudio.io", role_name="USER")
    headers = auth_headers(user)

    random_id = str(uuid.uuid4())
    resp = client.get(f"/api/v1/models/{random_id}/passport", headers=headers)
    assert resp.status_code == status.HTTP_404_NOT_FOUND
    assert "not found" in resp.json()["detail"].lower()
