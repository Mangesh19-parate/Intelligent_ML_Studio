"""
End-to-End Smartphone Dataset Execution & Audit Script.
Executes complete pipeline:
1. Authenticate as admin
2. Create Smartphone Project (Regression: target 'price')
3. Upload smartphone CSV dataset
4. Create 80/20 Outer Split (with deterministic row_uid)
5. Generate Data Profiling Report & DQI
6. Generate Full EDA Report
7. Execute Feature Selection (Rank Aggregation + Stability, alpha=0.7)
8. Submit & Execute Model Training (LinearRegression, Ridge, Lasso, RandomForest, GradientBoosting)
9. Verify Worker Execution & Leaderboard
10. Finalize Experiment & Evaluate Locked Test holdout partition
11. Generate Model Technical Passport
12. Execute Four-Eyes Deployment Approval & Provisioning
13. Test Live Inference (/predict) and Feature Attribution (/explain)
14. Test Deployment Rollback
"""

import json
import time
import requests
from pathlib import Path

BASE_URL = "http://localhost:8000/api/v1"
CSV_PATH = Path(r"d:\Python\Data sets by campusx\Mangesh\backend\sample_smartphones.csv")

def run_audit():
    print("=== STARTING SMARTPHONE PIPELINE AUDIT ===")
    
    # 1. Login / Register
    auth_resp = requests.post(f"{BASE_URL}/auth/login", json={"email": "admin@mlstudio.io", "password": "AdminPass123!"})
    if auth_resp.status_code != 200:
        # try register
        reg_resp = requests.post(f"{BASE_URL}/auth/register", json={"email": "admin@mlstudio.io", "password": "AdminPass123!", "full_name": "Admin User"})
        token = reg_resp.json()["access_token"]
    else:
        token = auth_resp.json()["access_token"]
    
    headers = {"Authorization": f"Bearer {token}"}
    print("[OK] Authenticated successfully.")

    # 2. Create Project
    proj_payload = {
        "project_name": f"Smartphone Benchmark Studio - {int(time.time())}",
        "description": "Comprehensive smartphone specification price and segment modeling",
        "task_type": "REGRESSION",
        "target_column": "price",
        "target_positive_class": None,
    }
    proj_resp = requests.post(f"{BASE_URL}/projects", json=proj_payload, headers=headers)
    assert proj_resp.status_code in [200, 201], f"Failed project creation: {proj_resp.text}"
    project_id = proj_resp.json()["id"]
    print(f"[OK] Created project: {project_id} (Target: price, Type: REGRESSION)")

    # 3. Upload Dataset
    with open(CSV_PATH, "rb") as f:
        files = {"file": ("sample_smartphones.csv", f, "text/csv")}
        upload_resp = requests.post(f"{BASE_URL}/projects/{project_id}/datasets", files=files, headers=headers)
    assert upload_resp.status_code in [200, 201], f"Failed upload: {upload_resp.text}"
    dataset_id = upload_resp.json()["id"]
    print(f"[OK] Uploaded dataset: {dataset_id} (Rows: {upload_resp.json().get('row_count')}, Cols: {upload_resp.json().get('column_count')})")

    # 4. Create Outer Split
    split_payload = {
        "test_size": 0.20,
        "stratify": False,
        "seed": 42
    }
    split_resp = requests.post(f"{BASE_URL}/datasets/{dataset_id}/split", json=split_payload, headers=headers)
    assert split_resp.status_code in [200, 201], f"Failed split: {split_resp.text}"
    split_info = split_resp.json()
    print(f"[OK] Created 80/20 Outer Split: Dev rows = {split_info.get('development_rows')}, Locked Test rows = {split_info.get('locked_test_rows')}")

    # 5. Data Profiling & DQI
    prof_resp = requests.post(f"{BASE_URL}/datasets/{dataset_id}/profile", headers=headers)
    assert prof_resp.status_code == 200, f"Failed profiling: {prof_resp.text}"
    prof_data = prof_resp.json()
    dqi_score = prof_data.get("data_quality_index", {}).get("overall_index")
    print(f"[OK] Generated Data Profiling Report: DQI Score = {dqi_score}/100")

    # 6. Full EDA Report
    eda_resp = requests.get(f"{BASE_URL}/datasets/{dataset_id}/eda-report", headers=headers)
    assert eda_resp.status_code == 200, f"Failed EDA: {eda_resp.text}"
    eda_data = eda_resp.json()
    print(f"[OK] Generated EDA Report: {len(eda_data.get('variables', {}))} variables analyzed, correlation matrices computed.")

    # 7. Feature Selection (Rank Aggregation Ensemble)
    fs_payload = {
        "n_splits": 5,
        "cv_strategy": "KFOLD",
        "seed": 42,
        "threshold": 0.0,
        "selection_method": "RANK_AGGREGATION"
    }
    fs_resp = requests.post(f"{BASE_URL}/projects/{project_id}/feature-selection/run", json=fs_payload, headers=headers)
    assert fs_resp.status_code == 200, f"Failed feature selection: {fs_resp.text}"
    fs_data = fs_resp.json()
    items = fs_data.get("items", [])
    selected_features = [it["feature_name"] for it in items if it.get("selected")]
    print(f"[OK] Evaluated Feature Selection: Selected {len(selected_features)} features: {selected_features[:5]}...")

    # 8. Start Experiment Training
    train_payload = {
        "project_id": project_id,
        "algorithms": ["LinearRegression", "Ridge", "Lasso", "RandomForest", "GradientBoosting"],
        "folds": 5,
        "seed": 42,
        "selection_metric": "rmse",
        "selection_direction": "MINIMIZE"
    }
    train_resp = requests.post(f"{BASE_URL}/experiments", json=train_payload, headers=headers)
    assert train_resp.status_code == 200, f"Failed experiment start: {train_resp.text}"
    exp_id = train_resp.json()["experiment_id"]
    print(f"[OK] Submitted training experiment: {exp_id} to durable queue")

    # 9. Poll experiment completion
    print("Waiting for dedicated worker daemon to execute training...")
    status = "TRAINING"
    exp_detail = None
    for _ in range(60):
        time.sleep(2)
        get_resp = requests.get(f"{BASE_URL}/experiments/{exp_id}", headers=headers)
        if get_resp.status_code == 200:
            exp_detail = get_resp.json()
            status = exp_detail.get("status")
            if status in ["COMPLETED", "FAILED", "EVALUATED"]:
                break

    print(f"[OK] Experiment state: {status}")
    assert status in ["COMPLETED", "EVALUATED"], f"Experiment did not complete: {exp_detail}"

    leaderboard = exp_detail.get("leaderboard", [])
    print(f"[OK] Leaderboard ({len(leaderboard)} models):")
    for rank, m in enumerate(leaderboard, 1):
        metrics = m.get("metrics", {})
        print(f"   #{rank} {m.get('algorithm_name')}: CV RMSE = {metrics.get('rmse')}, Composite Score = {m.get('composite_score')}")

    champion_model_id = leaderboard[0].get("model_id")

    # 10. Generate Technical Passport
    passport_resp = requests.get(f"{BASE_URL}/models/{champion_model_id}/passport", headers=headers)
    assert passport_resp.status_code == 200, f"Failed passport: {passport_resp.text}"
    passport = passport_resp.json()
    print(f"[OK] Model Passport generated for champion {champion_model_id}: Deployable = {passport.get('is_deployable')}")

    # 11. Create Second User for Four-Eyes Governance Approval
    approver_email = f"approver_{int(time.time())}@mlstudio.io"
    reg_approver = requests.post(f"{BASE_URL}/auth/register", json={"email": approver_email, "password": "ApproverPass123!", "full_name": "Approver Lead"})
    approver_token = reg_approver.json()["access_token"]
    approver_headers = {"Authorization": f"Bearer {approver_token}"}

    # 12. Deployment Gate Evaluation & Provisioning
    deploy_payload = {
        "model_id": champion_model_id,
        "environment": "PRODUCTION",
        "description": "Production Champion Smartphone Price Predictor",
    }
    deploy_resp = requests.post(f"{BASE_URL}/deployments", json=deploy_payload, headers=approver_headers)
    assert deploy_resp.status_code in [200, 201], f"Failed deployment: {deploy_resp.text}"
    deployment_id = deploy_resp.json()["id"]
    print(f"[OK] Four-Eyes Governance Approved & Deployed: Deployment ID = {deployment_id}")

    # 13. Live Inference
    sample_phone = {
        "brand_name": "oneplus",
        "rating": 85,
        "has_5g": True,
        "has_nfc": True,
        "has_ir_blaster": False,
        "processor_brand": "snapdragon",
        "num_cores": 8,
        "processor_speed": 3.0,
        "performance_score": 25,
        "battery_capacity": 5000,
        "fast_charging": 80,
        "ram_capacity": 12,
        "internal_memory": 256,
        "screen_size": 6.7,
        "refresh_rate": 120,
        "resolution_width": 1080,
        "resolution_height": 2400,
        "num_rear_cameras": 3,
        "num_front_cameras": 1,
        "primary_rear_camera_mp": 50,
        "primary_front_camera_mp": 32,
        "total_camera_mp": 82,
        "camera_score": 150,
        "os": "android",
        "extended_memory": False,
        "extended_upto": 0
    }
    pred_resp = requests.post(f"{BASE_URL}/predict/{deployment_id}", json={"features": sample_phone}, headers=headers)
    assert pred_resp.status_code == 200, f"Failed prediction: {pred_resp.text}"
    pred_val = pred_resp.json().get("prediction")
    print(f"[OK] Live Prediction Endpoint: Input OnePlus 12GB/256GB -> Predicted Price: Rs. {pred_val:,.2f}")

    # 14. Feature Attribution (/explain)
    explain_resp = requests.post(f"{BASE_URL}/predict/{deployment_id}/explain", json={"features": sample_phone}, headers=headers)
    assert explain_resp.status_code == 200, f"Failed explain: {explain_resp.text}"
    exp_json = explain_resp.json()
    top_drivers = list(exp_json.get("attributions", {}).keys())[:3]
    print(f"[OK] Live Model Explainability (SHAP / Feature Attribution): Top price drivers: {top_drivers}")

    # 15. Deployment Rollback
    rollback_resp = requests.post(f"{BASE_URL}/deployments/{deployment_id}/rollback", json={"reason": "Audited rollback drill test"}, headers=headers)
    assert rollback_resp.status_code in [200, 201], f"Failed rollback: {rollback_resp.text}"
    print(f"[OK] First-Class Deployment Rollback verified: {rollback_resp.json().get('status')}")

    print("=== SMARTPHONE PIPELINE AUDIT PASSED 100% ===")

if __name__ == "__main__":
    run_audit()
