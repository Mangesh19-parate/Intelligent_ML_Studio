import uuid
import os
import io
import time
from unittest.mock import patch
import pandas as pd
import pytest
from sqlalchemy.orm import Session
from fastapi.testclient import TestClient

from app.core.database import get_db, SessionLocal
from app.core.security import create_access_token
from app.main import app
from app.models.project import Project
from app.models.user import User
from app.models.role import Role
from app.models.dataset import Dataset
from app.models.dataset_split import DatasetSplit
from app.models.profiling_report import ProfilingReport
from app.models.transformation_config import TransformationConfig
from app.models.experiment import Experiment
from app.models.trained_model import TrainedModel
from app.models.model_metric import ModelMetric
from app.models.deployment import Deployment
from app.models.deployment_gate import DeploymentGate
from app.models.prediction_log import PredictionLog
from app.services.dataset_service import DatasetService
from app.services.dataset_split_service import DatasetSplitService
from app.services.data_profiling_service import DataProfilingService
from app.services.transformation_service import TransformationService
from app.services.experiment_service import ExperimentService
from app.services.evaluation_service import EvaluationService
from app.services.deployment_gate_service import DeploymentGateService
from app.services.deployment_service import DeploymentService
from app.services.prediction_service import PredictionService
from app.services.monitoring_service import MonitoringService
from app.services.workspace_analytics_service import (
    WorkspaceAnalyticsService,
    derive_pipeline_stage,
)


def create_synthetic_csv(n_rows: int = 100) -> bytes:
    df = pd.DataFrame({
        "num1": [float(i) for i in range(n_rows)],
        "num2": [float(i * 2.5) for i in range(n_rows)],
        "cat1": ["TypeA" if i % 2 == 0 else "TypeB" for i in range(n_rows)],
        "target": [float(i * 1.5 + (1 if i % 2 == 0 else -1)) for i in range(n_rows)],
    })
    buf = io.BytesIO()
    df.to_csv(buf, index=False)
    return buf.getvalue()


@pytest.fixture
def client_and_users(db_session: Session):
    admin_role = db_session.query(Role).filter(Role.role_name == "ADMIN").first()
    engineer_role = db_session.query(Role).filter(Role.role_name == "ML_ENGINEER").first()
    viewer_role = db_session.query(Role).filter(Role.role_name == "VIEWER").first()

    admin_user = User(
        id=uuid.uuid4(),
        full_name="Admin User",
        email=f"admin_{uuid.uuid4().hex[:6]}@test.com",
        password_hash="fake",
        role_id=admin_role.id,
    )
    engineer_user = User(
        id=uuid.uuid4(),
        full_name="Engineer User",
        email=f"eng_{uuid.uuid4().hex[:6]}@test.com",
        password_hash="fake",
        role_id=engineer_role.id,
    )
    viewer_user = User(
        id=uuid.uuid4(),
        full_name="Viewer User",
        email=f"viewer_{uuid.uuid4().hex[:6]}@test.com",
        password_hash="fake",
        role_id=viewer_role.id,
    )
    db_session.add_all([admin_user, engineer_user, viewer_user])
    db_session.commit()

    admin_token = create_access_token(str(admin_user.id))
    eng_token = create_access_token(str(engineer_user.id))
    viewer_token = create_access_token(str(viewer_user.id))

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)

    yield {
        "client": client,
        "admin_user": admin_user,
        "eng_user": engineer_user,
        "viewer_user": viewer_user,
        "admin_headers": {"Authorization": f"Bearer {admin_token}"},
        "eng_headers": {"Authorization": f"Bearer {eng_token}"},
        "viewer_headers": {"Authorization": f"Bearer {viewer_token}"},
    }

    app.dependency_overrides.clear()


def test_acceptance_check_a_walkthrough_all_derived_stages(db_session: Session):
    """
    Check a) Create a project, walk it through every stage from upload to a LIVE deployment,
    checking derive_pipeline_stage()'s output after EACH step and confirming it advances
    correctly at every transition.
    """
    eng_role = db_session.query(Role).filter(Role.role_name == "ML_ENGINEER").first()
    user = User(
        id=uuid.uuid4(),
        full_name="Stage Tester",
        email=f"stage_{uuid.uuid4().hex[:6]}@test.com",
        password_hash="fake",
        role_id=eng_role.id,
    )
    db_session.add(user)
    db_session.commit()

    # Step 0: Project creation (no dataset)
    project = Project(
        id=uuid.uuid4(),
        owner_id=user.id,
        project_name="Full Walkthrough Project",
        task_type="REGRESSION",
        target_column="target",
        pipeline_stage="DATA",
    )
    db_session.add(project)
    db_session.commit()

    assert derive_pipeline_stage(project.id, db_session) == "DATA", "Empty project must be DATA"

    # Step 1: Upload dataset, no split
    csv_bytes = create_synthetic_csv(100)
    ds_service = DatasetService(db_session)
    dataset = ds_service.upload(project.id, "synthetic.csv", csv_bytes, uploaded_by_id=user.id)
    ds_service.detect_structural_schema(dataset.id)

    assert derive_pipeline_stage(project.id, db_session) == "DATA", "Uploaded dataset without split must remain DATA"

    # Step 2: Create Outer Split (no profiling yet)
    split_service = DatasetSplitService(db_session)
    split_res = split_service.create_outer_split(dataset.id, locked_test_pct=20, seed=42)

    assert derive_pipeline_stage(project.id, db_session) == "SPLIT", "Split without profiling must be SPLIT"

    # Step 3: Run Profiling & DQI (no active transformation configs)
    prof_service = DataProfilingService(db_session)
    prof_service.generate_report(dataset.id)

    assert derive_pipeline_stage(project.id, db_session) == "PROFILED", "Profiled dataset without active transforms must be PROFILED"

    # Step 4: Configure active transformations (no experiments)
    trans_service = TransformationService(db_session)
    trans_service.set_encoding_strategy(project.id, "cat1", "one_hot")

    assert derive_pipeline_stage(project.id, db_session) == "TRANSFORMED", "Active transformations without experiments must be TRANSFORMED"

    # Step 5: Start experiment (RUNNING)
    exp_service = ExperimentService(db_session)
    exp = Experiment(
        id=uuid.uuid4(),
        project_id=project.id,
        status="RUNNING",
        task_type="REGRESSION",
        fold_count=5,
        selection_metric="rmse",
        selection_direction="MINIMIZE",
    )
    db_session.add(exp)
    db_session.commit()

    assert derive_pipeline_stage(project.id, db_session) == "TRAINING", "Running experiment must be TRAINING"

    # Step 6: Complete experiment training (COMPLETED, but not finalized / no locked test metrics)
    exp.status = "COMPLETED"
    trained_model = TrainedModel(
        id=uuid.uuid4(),
        experiment_id=exp.id,
        algorithm_name="Ridge",
        quick_cv_score=0.85,
        status="COMPLETED",
        fit_diagnosis="GOOD_FIT",
    )
    db_session.add(trained_model)
    db_session.commit()

    # Add CV_MEAN metric
    cv_metric = ModelMetric(
        model_id=trained_model.id,
        metric_name="rmse",
        split="CV_MEAN",
        metric_value=0.25,
    )
    db_session.add(cv_metric)
    db_session.commit()

    assert derive_pipeline_stage(project.id, db_session) == "TRAINED", "Completed experiment without locked test metric must be TRAINED"

    # Step 7: Locked Test Evaluation (EVALUATED)
    locked_metric = ModelMetric(
        model_id=trained_model.id,
        metric_name="rmse",
        split="LOCKED_TEST",
        metric_value=0.27,
    )
    exp.selected_model_id = trained_model.id
    exp.locked_test_consumed = True
    db_session.add(locked_metric)
    db_session.commit()

    assert derive_pipeline_stage(project.id, db_session) == "EVALUATED", "Model with LOCKED_TEST metric must be EVALUATED"

    # Step 8: Deployment Gate Passed (GATE_PASSED)
    gate = DeploymentGate(
        id=uuid.uuid4(),
        model_id=trained_model.id,
        locked_test_evaluated=True,
        schema_locked=True,
        artifact_verified=True,
        lineage_complete=True,
        performance_threshold_passed="PASS",
        user_approved=True,
        gate_passed=True,
    )
    db_session.add(gate)
    db_session.commit()

    assert derive_pipeline_stage(project.id, db_session) == "GATE_PASSED", "Passed gate must be GATE_PASSED"

    # Step 9: Model Deployed LIVE (DEPLOYED)
    deployment = Deployment(
        id=uuid.uuid4(),
        model_id=trained_model.id,
        endpoint_path=f"/models/{trained_model.id}/predict",
        status="LIVE",
    )
    db_session.add(deployment)
    db_session.commit()

    assert derive_pipeline_stage(project.id, db_session) == "DEPLOYED", "LIVE deployment must be DEPLOYED"


def test_acceptance_check_b_workspace_analytics_user_scoping(db_session: Session, client_and_users):
    """
    Check b) Confirm WorkspaceAnalyticsService.get_summary for a non-ADMIN user only counts
    that user's own projects, and confirm an ADMIN sees the platform-wide total.
    """
    admin_user = client_and_users["admin_user"]
    eng_user = client_and_users["eng_user"]
    viewer_user = client_and_users["viewer_user"]

    # Create 2 projects for eng_user
    proj1 = Project(id=uuid.uuid4(), owner_id=eng_user.id, project_name="Eng Project 1")
    proj2 = Project(id=uuid.uuid4(), owner_id=eng_user.id, project_name="Eng Project 2")

    # Create 1 project for admin_user
    proj3 = Project(id=uuid.uuid4(), owner_id=admin_user.id, project_name="Admin Project")

    # Create 1 project for viewer_user
    proj4 = Project(id=uuid.uuid4(), owner_id=viewer_user.id, project_name="Viewer Project")

    db_session.add_all([proj1, proj2, proj3, proj4])
    db_session.commit()

    analytics = WorkspaceAnalyticsService(db_session)

    # 1. Non-admin engineer summary
    eng_summary = analytics.get_summary(eng_user)
    assert eng_summary["total_projects"] == 2
    assert eng_summary["is_platform_wide"] is False

    # 2. Viewer summary
    viewer_summary = analytics.get_summary(viewer_user)
    assert viewer_summary["total_projects"] == 1
    assert viewer_summary["is_platform_wide"] is False

    # 3. Admin summary -> sees all 4 projects
    admin_summary = analytics.get_summary(admin_user)
    assert admin_summary["total_projects"] >= 4
    assert admin_summary["is_platform_wide"] is True

    # 4. API verification
    client = client_and_users["client"]
    res_eng = client.get("/api/v1/workspace/summary", headers=client_and_users["eng_headers"])
    assert res_eng.status_code == 200
    assert res_eng.json()["total_projects"] == 2

    res_admin = client.get("/api/v1/workspace/summary", headers=client_and_users["admin_headers"])
    assert res_admin.status_code == 200
    assert res_admin.json()["total_projects"] >= 4


def test_acceptance_check_c_error_rate_separation(db_session: Session):
    """
    Check c) Generate a mix of successful, validation-error, and server-error prediction requests
    against a live deployment; confirm error_rate correctly separates the two error types.
    """
    dep_id = uuid.uuid4()
    deployment = Deployment(
        id=dep_id,
        model_id=uuid.uuid4(),
        endpoint_path=f"/models/{dep_id}/predict",
        status="LIVE",
    )
    db_session.add(deployment)

    # 6 SUCCESS logs
    for _ in range(6):
        db_session.add(PredictionLog(
            deployment_id=dep_id,
            schema_hash="hash123",
            latency_ms=15,
            status="SUCCESS",
        ))

    # 3 VALIDATION_ERROR logs
    for _ in range(3):
        db_session.add(PredictionLog(
            deployment_id=dep_id,
            schema_hash="hash123",
            latency_ms=5,
            status="VALIDATION_ERROR",
        ))

    # 1 SERVER_ERROR log
    db_session.add(PredictionLog(
        deployment_id=dep_id,
        schema_hash="hash123",
        latency_ms=45,
        status="SERVER_ERROR",
    ))

    db_session.commit()

    monitoring = MonitoringService(db_session)
    stats = monitoring.error_rate(dep_id, lookback_hours=24)

    assert stats["total_requests"] == 10
    assert stats["success_count"] == 6
    assert stats["validation_error_count"] == 3
    assert stats["server_error_count"] == 1
    assert stats["error_rate"] == 0.4  # (3 + 1) / 10
    assert stats["validation_error_rate"] == 0.3  # 3 / 10
    assert stats["server_error_rate"] == 0.1  # 1 / 10


def test_acceptance_check_d_latency_summary_decoupled_profiles(db_session: Session):
    """
    Check d) Confirm latency_summary shows a clear, measurable difference between the
    base-predict path and the explain path (the explain path is visibly slower due to SHAP).
    """
    dep_id = uuid.uuid4()
    deployment = Deployment(
        id=dep_id,
        model_id=uuid.uuid4(),
        endpoint_path=f"/models/{dep_id}/predict",
        status="LIVE",
    )
    db_session.add(deployment)

    # 10 Base predictions (fast ~ 10-20ms)
    for lat in [10, 12, 14, 15, 16, 18, 19, 20, 22, 25]:
        db_session.add(PredictionLog(
            deployment_id=dep_id,
            schema_hash="hash123",
            latency_ms=lat,
            explanation_requested=False,
            explanation_latency_ms=None,
            status="SUCCESS",
        ))

    # 5 Explained predictions (base ~ 15ms + SHAP ~ 120-180ms)
    for shap_lat in [120, 140, 150, 160, 180]:
        db_session.add(PredictionLog(
            deployment_id=dep_id,
            schema_hash="hash123",
            latency_ms=15,
            explanation_requested=True,
            explanation_latency_ms=shap_lat,
            status="SUCCESS",
        ))

    db_session.commit()

    monitoring = MonitoringService(db_session)
    summary = monitoring.latency_summary(dep_id, lookback_hours=24)

    base = summary["base_predictions"]
    explained = summary["explained_predictions"]

    assert base["count"] == 10
    assert explained["count"] == 5
    assert base["avg_ms"] < 25.0
    assert explained["avg_ms"] > 130.0
    assert explained["avg_ms"] > base["avg_ms"] * 5, "Explained path must be visibly slower than base path"
    assert explained["p95_ms"] > base["p95_ms"]


def test_acceptance_check_e_viewer_role_permission_gating(client_and_users):
    """
    Check e) Confirm VIEWER-role user has READ permission but cannot execute mutation actions.
    """
    client = client_and_users["client"]
    viewer_headers = client_and_users["viewer_headers"]

    # 1. VIEWER can read workspace summary
    res_summary = client.get("/api/v1/workspace/summary", headers=viewer_headers)
    assert res_summary.status_code == 200

    # 2. VIEWER cannot create projects (requires EDIT_DATA)
    res_create = client.post(
        "/api/v1/projects",
        json={"project_name": "Forbidden Project"},
        headers=viewer_headers
    )
    assert res_create.status_code == 403

    # 3. VIEWER cannot deploy (requires DEPLOY)
    fake_model_id = uuid.uuid4()
    res_deploy = client.post(
        f"/api/v1/models/{fake_model_id}/deploy",
        headers=viewer_headers
    )
    assert res_deploy.status_code == 403


def test_acceptance_check_f_no_activity_logs_or_experiment_timeline():
    """
    Check f) Confirm no code path today reads `activity_logs` or references an
    "Experiment Timeline" widget — grep for it; today's dashboard should have no
    dependency on a table that was never built.
    """
    code_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

    target_phrase_1 = "activity" + "_logs"
    target_phrase_2 = "Experiment" + " Timeline"

    found_activity_logs = []
    found_timeline = []

    for root, _, files in os.walk(code_root):
        # Skip doc files, tests, and build dirs
        if any(ignored in root for ignored in [".git", "node_modules", ".gemini", "tests", "dist"]):
            continue
        for f in files:
            if f.endswith((".py", ".jsx", ".js", ".html")):
                filepath = os.path.join(root, f)
                with open(filepath, "r", encoding="utf-8", errors="ignore") as file:
                    content = file.read()
                    if target_phrase_1 in content:
                        found_activity_logs.append(filepath)
                    if target_phrase_2 in content:
                        found_timeline.append(filepath)

    assert len(found_activity_logs) == 0, f"Found activity_logs references in code: {found_activity_logs}"
    assert len(found_timeline) == 0, f"Found Experiment Timeline references in code: {found_timeline}"


def test_acceptance_check_g_standing_leakage_check_no_new_locked_test_calls(db_session: Session):
    """
    Check g) The standing leakage check: confirm nothing built today introduces any new
    call to get_locked_test_data() — the call count from Day 7's finalize logic should
    be completely unchanged by anything added today.
    """
    import ast

    code_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "backend", "app"))
    callers = []

    for root, _, files in os.walk(code_root):
        for f in files:
            if f.endswith(".py"):
                filepath = os.path.join(root, f)
                with open(filepath, "r", encoding="utf-8") as file:
                    tree = ast.parse(file.read(), filename=filepath)
                for node in ast.walk(tree):
                    if isinstance(node, ast.Call):
                        func = node.func
                        if isinstance(func, ast.Attribute) and func.attr == "get_locked_test_data":
                            callers.append((f, node.lineno))
                        elif isinstance(func, ast.Name) and func.id == "get_locked_test_data":
                            callers.append((f, node.lineno))

    # The ONLY allowed callers in backend/app are in finalize_experiment and diagnostic_rerun in experiment_service.py
    caller_files = {c[0] for c in callers}
    assert caller_files == {"experiment_service.py"}, f"Unexpected caller files of get_locked_test_data: {callers}"
    assert len(callers) == 2, f"Expected exactly 2 call sites (finalize and diagnostic-rerun), got: {callers}"

