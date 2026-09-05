import os
import sys
import io
import time
import uuid
import json
import hashlib
from pathlib import Path
from datetime import datetime

# Set up backend import paths
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

import numpy as np
import pandas as pd
from sqlalchemy.orm import Session

from app.core.database import Base, engine, SessionLocal
from app.core.seeder import seed_rbac_data
from app.core.security import get_password_hash, create_access_token
from app.models.user import User
from app.models.role import Role
from app.models.project import Project
from app.models.dataset import Dataset
from app.models.dataset_split import DatasetSplit
from app.services.dataset_service import DatasetService
from app.services.dataset_split_service import DatasetSplitService
from app.services.data_profiling_service import DataProfilingService
from app.services.transformation_service import TransformationService
from app.services.feature_selection_service import FeatureSelectionService
from app.services.experiment_service import ExperimentService
from app.services.explainability_service import ExplainabilityService
from app.services.deployment_gate_service import DeploymentGateService
from app.services.deployment_service import DeploymentService
from app.services.prediction_service import PredictionService


def generate_realistic_dataset(n_samples: int = 300, seed: int = 42) -> bytes:
    """Generates realistic tabular customer loan default / credit dataset."""
    np.random.seed(seed)
    age = np.random.normal(42, 12, n_samples).clip(18, 80)
    income = np.random.lognormal(mean=10.8, sigma=0.5, size=n_samples).clip(20000, 250000)
    credit_score = np.random.normal(680, 75, n_samples).clip(300, 850)
    debt_to_income = np.random.uniform(0.05, 0.65, n_samples)
    loan_amount = income * np.random.uniform(0.2, 2.5, n_samples)
    education = np.random.choice(["HighSchool", "Bachelors", "Masters", "Doctorate"], size=n_samples, p=[0.3, 0.45, 0.2, 0.05])
    employment_type = np.random.choice(["Salaried", "SelfEmployed", "Contract", "Unemployed"], size=n_samples, p=[0.6, 0.25, 0.1, 0.05])
    
    # Target: interest_rate (regression) or default_risk
    base_rate = 3.5 + (850 - credit_score) * 0.015 + debt_to_income * 8.0 - (income / 100000.0) * 0.5 + np.random.normal(0, 0.5, n_samples)
    interest_rate = np.round(np.clip(base_rate, 2.5, 28.0), 2)

    df = pd.DataFrame({
        "age": np.round(age, 1),
        "annual_income": np.round(income, 2),
        "credit_score": np.round(credit_score, 0),
        "debt_to_income": np.round(debt_to_income, 3),
        "loan_amount": np.round(loan_amount, 2),
        "education_level": education,
        "employment_type": employment_type,
        "interest_rate": interest_rate,
    })
    
    buf = io.BytesIO()
    df.to_csv(buf, index=False)
    return buf.getvalue()


def run_demo_rehearsal():
    print("=" * 80)
    print(" ML STUDIO — DAY 12 DEMO REHEARSAL & END-TO-END TIMING BENCHMARK")
    print("=" * 80)
    
    overall_start = time.perf_counter()
    timings: dict[str, float] = {}

    # Initialize / Reset database to guarantee a completely clean, fresh empty DB state
    t0 = time.perf_counter()
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db: Session = SessionLocal()
    seed_rbac_data(db)
    timings["DB & RBAC Initialization"] = time.perf_counter() - t0

    # Step 1: Seed 4 Canonical Multi-Role Users
    t0 = time.perf_counter()
    roles = {r.role_name: r for r in db.query(Role).all()}
    
    users = {
        "ADMIN": User(
            id=uuid.uuid4(), full_name="System Admin", email="admin@studio.com",
            password_hash=get_password_hash("AdminPass123!"), role_id=roles["ADMIN"].id, is_active=True
        ),
        "ML_ENGINEER": User(
            id=uuid.uuid4(), full_name="Senior ML Engineer", email="engineer@studio.com",
            password_hash=get_password_hash("EngineerPass123!"), role_id=roles["ML_ENGINEER"].id, is_active=True
        ),
        "DATA_STEWARD": User(
            id=uuid.uuid4(), full_name="Lead Data Steward", email="steward@studio.com",
            password_hash=get_password_hash("StewardPass123!"), role_id=roles["DATA_STEWARD"].id, is_active=True
        ),
        "DEPLOYMENT_MANAGER": User(
            id=uuid.uuid4(), full_name="Release Operations Manager", email="deployment_mgr@studio.com",
            password_hash=get_password_hash("DeployPass123!"), role_id=roles["DEPLOYMENT_MANAGER"].id, is_active=True
        ),
    }
    
    for u in users.values():
        existing = db.query(User).filter(User.email == u.email).first()
        if not existing:
            db.add(u)
    db.commit()
    timings["Multi-Role User Seeding (4 Roles)"] = time.perf_counter() - t0

    mle_user = db.query(User).filter(User.email == "engineer@studio.com").first()

    # Step 2: Create Project
    t0 = time.perf_counter()
    project = Project(
        id=uuid.uuid4(),
        owner_id=mle_user.id,
        project_name="Credit Risk & Interest Rate Optimization",
        task_type="REGRESSION",
        target_column="interest_rate",
        pipeline_stage="DATA",
    )
    db.add(project)
    db.commit()
    timings["Project Creation"] = time.perf_counter() - t0

    # Step 3: Realistic Dataset Upload (300 rows, 8 columns)
    t0 = time.perf_counter()
    csv_bytes = generate_realistic_dataset(n_samples=300, seed=42)
    ds_service = DatasetService(db)
    dataset = ds_service.upload(project.id, "customer_credit_risk.csv", csv_bytes, uploaded_by_id=mle_user.id)
    ds_service.detect_structural_schema(dataset.id)
    timings["Dataset Upload & Schema Detection (300 rows)"] = time.perf_counter() - t0

    # Step 4: Outer Split Creation (80% Dev = 240 rows, 20% Locked Test = 60 rows)
    t0 = time.perf_counter()
    split_service = DatasetSplitService(db)
    split_info = split_service.create_outer_split(dataset.id, locked_test_pct=20, seed=42)
    timings["Outer Split Partitioning (80/20)"] = time.perf_counter() - t0

    # Step 5: Profiling & Data Quality Index (DQI)
    t0 = time.perf_counter()
    prof_service = DataProfilingService(db)
    report = prof_service.generate_report(dataset.id)
    dqi_score = report["data_quality_index"]["overall_index"]
    timings["Data Profiling & DQI Computation"] = time.perf_counter() - t0

    # Step 6: Leakage-Safe Transformation Configuration
    t0 = time.perf_counter()
    trans_service = TransformationService(db)
    trans_service.set_encoding_strategy(project.id, "education_level", "one_hot")
    trans_service.set_encoding_strategy(project.id, "employment_type", "one_hot")
    trans_service.set_scaling_strategy(project.id, "annual_income", "standard")
    trans_service.set_scaling_strategy(project.id, "loan_amount", "standard")
    trans_service.set_scaling_strategy(project.id, "credit_score", "standard")
    trans_service.preview_transformation(project.id, "annual_income", sample_size=50)
    timings["Transformation Configuration & Preview"] = time.perf_counter() - t0

    # Step 7: Cross-Validation Feature Selection (5 folds)
    t0 = time.perf_counter()
    fs_service = FeatureSelectionService(db)
    fs_res = fs_service.run_cv_feature_selection(project.id, n_splits=5, seed=42, threshold=0.25)
    timings["CV Feature Selection (5 Folds, 4 Techniques)"] = time.perf_counter() - t0

    # Step 8: Multi-Algorithm CV Model Training (3 algorithms x 5 folds)
    t0 = time.perf_counter()
    exp_service = ExperimentService(db)
    exp_res = exp_service.run_experiment(
        project_id=project.id,
        algorithms=["LinearRegression", "Ridge", "RandomForestRegressor"],
        folds=5,
        seed=42,
        selection_metric="rmse",
        selection_direction="MINIMIZE",
        auto_finalize=False,
        deployment_threshold={"metric": "rmse", "min_value": 50000.0},
    )
    experiment_id = exp_res["experiment_id"]
    timings["Multi-Model Training (3 Algs x 5 Folds = 15 fits)"] = time.perf_counter() - t0

    # Step 9: Leaderboard Evaluation & Model Selection
    t0 = time.perf_counter()
    from app.api.v1.projects import get_project_leaderboard
    leaderboard = get_project_leaderboard(id=project.id, experiment_id=None, current_user=mle_user, db=db)
    timings["Leaderboard Query & Ranking"] = time.perf_counter() - t0

    # Step 10: Single-Use Locked Test Finalization & Full Refit
    t0 = time.perf_counter()
    fin_res = exp_service.finalize_experiment(experiment_id)
    winning_model_id = fin_res["selected_model_id"]
    timings["Locked Test Evaluation & Full Dev Refit"] = time.perf_counter() - t0

    # Step 11: Decoupled SHAP Explainability (Global + Local)
    t0 = time.perf_counter()
    expl_service = ExplainabilityService(db)
    global_shap = expl_service.global_shap_summary(winning_model_id, background_sample_size=80)
    sample_input = {
        "age": 45.0,
        "annual_income": 85000.0,
        "credit_score": 720.0,
        "debt_to_income": 0.28,
        "loan_amount": 120000.0,
        "education_level": "Bachelors",
        "employment_type": "Salaried",
    }
    local_shap = expl_service.local_shap_explanation(winning_model_id, sample_input)
    timings["SHAP Global & Local Explainability"] = time.perf_counter() - t0

    # Step 12: Deployment Gate Verification & Approval
    t0 = time.perf_counter()
    gate_service = DeploymentGateService(db)
    gate = gate_service.check_gate(winning_model_id, user_approved=True)
    timings["6-Condition Deployment Gate Verification"] = time.perf_counter() - t0

    # Step 13: Live Model Deployment
    t0 = time.perf_counter()
    dep_service = DeploymentService(db)
    deployment = dep_service.deploy(winning_model_id, user_id=mle_user.id)
    timings["Model Registry & Live Deployment"] = time.perf_counter() - t0

    # Step 14: Real-time Live Prediction & Explanation
    t0 = time.perf_counter()
    pred_service = PredictionService(db)
    pred_res, _ = pred_service.predict(deployment.id, sample_input)
    pred_explain_res = pred_service.predict_with_explanation(deployment.id, sample_input)
    timings["Real-time Prediction & Real-time SHAP"] = time.perf_counter() - t0

    total_wall_clock = time.perf_counter() - overall_start

    # Output Structured Results Table
    print("\n" + "-" * 80)
    print(f"{'PIPELINE STAGE / WORKFLOW STEP':<55} | {'LATENCY (s)':<15}")
    print("-" * 80)
    for step_name, elapsed in timings.items():
        print(f"{step_name:<55} | {elapsed:>10.4f}s")
    print("-" * 80)
    print(f"{'TOTAL WALL-CLOCK REHEARSAL TIME':<55} | {total_wall_clock:>10.4f}s")
    print("=" * 80)

    print("\n--- AUDIT INVARIANT HIGHLIGHTS ---")
    print(f"• Seeded Users: ADMIN, ML_ENGINEER, DATA_STEWARD, DEPLOYMENT_MANAGER (4)")
    print(f"• Dataset: {dataset.row_count} rows, {dataset.column_count} columns, SHA-256: {dataset.content_hash[:16]}...")
    print(f"• Partition Sizes: Dev={split_info['development_rows']} rows, Locked Test={split_info['locked_test_rows']} rows")
    print(f"• Data Quality Index (DQI): {dqi_score:.2f} / 100.0")
    print(f"• Winning Model: {fin_res['winning_algorithm']} (RMSE: {fin_res['locked_test_metrics']['rmse']:.4f})")
    print(f"• Deployment Status: {deployment.status} (ID: {deployment.id})")
    print(f"• Live Fast Prediction: {pred_res.prediction} (Latency: {pred_res.latency_ms:.2f} ms)")
    print(f"• Live Explained Prediction: {pred_explain_res.prediction} (SHAP Latency: {pred_explain_res.explanation_latency_ms:.2f} ms)")
    print("=" * 80)

    db.close()
    return total_wall_clock, timings


if __name__ == "__main__":
    run_demo_rehearsal()
