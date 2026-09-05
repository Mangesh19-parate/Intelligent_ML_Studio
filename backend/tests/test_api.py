import io
import pytest
from app.core.versioning import get_code_version

def test_code_version_utility():
    ver = get_code_version()
    assert isinstance(ver, str)
    assert len(ver) > 0

def test_auth_register_and_login(client):
    # 1. Register new user
    reg_resp = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Alice Engineer",
            "email": "alice@example.com",
            "password": "securepassword123",
            "role_name": "ML_ENGINEER"
        }
    )
    assert reg_resp.status_code == 201
    user_data = reg_resp.json()
    assert user_data["email"] == "alice@example.com"
    assert "EDIT_DATA" in user_data["permissions"]
    assert "READ" in user_data["permissions"]

    # 2. Login
    login_resp = client.post(
        "/api/v1/auth/login",
        json={
            "email": "alice@example.com",
            "password": "securepassword123"
        }
    )
    assert login_resp.status_code == 200
    token_data = login_resp.json()
    assert "access_token" in token_data
    assert "refresh_token" in token_data

    # 3. Get /me
    me_resp = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token_data['access_token']}"}
    )
    assert me_resp.status_code == 200
    assert me_resp.json()["email"] == "alice@example.com"

def test_permission_based_rbac_enforcement(client, create_test_user):
    # 1. VIEWER (has 'READ' only)
    viewer = create_test_user("viewer@example.com", role_name="VIEWER")
    viewer_headers = {"Authorization": f"Bearer {client.post('/api/v1/auth/login', json={'email': 'viewer@example.com', 'password': 'password123'}).json()['access_token']}"}
    
    # VIEWER can READ projects
    assert client.get("/api/v1/projects", headers=viewer_headers).status_code == 200
    # VIEWER cannot CREATE projects (requires EDIT_DATA)
    res_v_create = client.post("/api/v1/projects", json={"project_name": "Unauthorized Project"}, headers=viewer_headers)
    assert res_v_create.status_code == 403
    assert "EDIT_DATA" in res_v_create.json()["detail"]

    # 2. DATA_STEWARD (has 'READ', 'EDIT_DATA')
    steward = create_test_user("steward_rbac@example.com", role_name="DATA_STEWARD")
    steward_headers = {"Authorization": f"Bearer {client.post('/api/v1/auth/login', json={'email': 'steward_rbac@example.com', 'password': 'password123'}).json()['access_token']}"}
    
    # DATA_STEWARD can create projects
    steward_proj = client.post("/api/v1/projects", json={"project_name": "Steward Project", "target_column": "target"}, headers=steward_headers)
    assert steward_proj.status_code == 201
    steward_proj_id = steward_proj.json()["id"]

    # DATA_STEWARD cannot trigger model training (requires TRAIN)
    res_s_train = client.post(f"/api/v1/projects/{steward_proj_id}/experiments", json={"algorithms": ["LogisticRegression"]}, headers=steward_headers)
    assert res_s_train.status_code == 403
    assert "TRAIN" in res_s_train.json()["detail"]

    # 3. ML_ENGINEER (has 'READ', 'EDIT_DATA', 'TRAIN')
    mle = create_test_user("mle_rbac@example.com", role_name="ML_ENGINEER")
    mle_headers = {"Authorization": f"Bearer {client.post('/api/v1/auth/login', json={'email': 'mle_rbac@example.com', 'password': 'password123'}).json()['access_token']}"}
    
    # ML_ENGINEER can create projects and edit transformations
    mle_proj = client.post("/api/v1/projects", json={"project_name": "MLE Project", "target_column": "target"}, headers=mle_headers)
    assert mle_proj.status_code == 201

    # 4. DEPLOYMENT_MANAGER (has 'READ', 'DEPLOY')
    dep_mgr = create_test_user("dep_mgr_rbac@example.com", role_name="DEPLOYMENT_MANAGER")
    dep_mgr_headers = {"Authorization": f"Bearer {client.post('/api/v1/auth/login', json={'email': 'dep_mgr_rbac@example.com', 'password': 'password123'}).json()['access_token']}"}
    
    # DEPLOYMENT_MANAGER can READ projects
    assert client.get("/api/v1/projects", headers=dep_mgr_headers).status_code == 200
    # DEPLOYMENT_MANAGER cannot trigger training (requires TRAIN)
    res_dm_train = client.post(f"/api/v1/projects/{steward_proj_id}/experiments", json={"algorithms": ["LogisticRegression"]}, headers=dep_mgr_headers)
    assert res_dm_train.status_code == 403
    assert "TRAIN" in res_dm_train.json()["detail"]

    # 5. ADMIN (has all permissions)
    admin = create_test_user("admin_rbac@example.com", role_name="ADMIN")
    admin_headers = {"Authorization": f"Bearer {client.post('/api/v1/auth/login', json={'email': 'admin_rbac@example.com', 'password': 'password123'}).json()['access_token']}"}
    
    # ADMIN can create projects
    admin_proj = client.post("/api/v1/projects", json={"project_name": "Admin Project", "target_column": "target"}, headers=admin_headers)
    assert admin_proj.status_code == 201

def test_project_crud_and_invariants(client, create_test_user):
    ml_eng = create_test_user("eng@example.com", role_name="ML_ENGINEER")
    eng_login = client.post(
        "/api/v1/auth/login",
        json={"email": "eng@example.com", "password": "password123"}
    ).json()
    headers = {"Authorization": f"Bearer {eng_login['access_token']}"}

    # 1. Create project
    create_resp = client.post(
        "/api/v1/projects",
        json={"project_name": "Customer Churn Prediction", "target_column": "churn"},
        headers=headers
    )
    assert create_resp.status_code == 201
    proj = create_resp.json()
    project_id = proj["id"]
    
    # Verify invariants on Day 1
    assert proj["project_name"] == "Customer Churn Prediction"
    assert proj["task_type"] == "UNDETERMINED"
    assert proj["pipeline_stage"] == "DATA"
    assert proj["data_quality_index"] is None  # Must remain None on Day 1!

    # 2. Get project
    get_resp = client.get(f"/api/v1/projects/{project_id}", headers=headers)
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == project_id

    # 3. Update project
    update_resp = client.put(
        f"/api/v1/projects/{project_id}",
        json={"project_name": "Churn Model V2"},
        headers=headers
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["project_name"] == "Churn Model V2"

def test_dataset_upload_and_structural_schema_inference(client, create_test_user):
    user = create_test_user("steward@example.com", role_name="DATA_STEWARD")
    login_data = client.post(
        "/api/v1/auth/login",
        json={"email": "steward@example.com", "password": "password123"}
    ).json()
    headers = {"Authorization": f"Bearer {login_data['access_token']}"}

    # Create project
    proj_resp = client.post(
        "/api/v1/projects",
        json={"project_name": "Housing Regression", "target_column": "price"},
        headers=headers
    )
    project_id = proj_resp.json()["id"]

    # Prepare tabular CSV content with various structural data types
    csv_content = (
        "id,price,neighborhood,created_at,is_renovated\n"
        "1,250000.50,Downtown,2023-01-15,True\n"
        "2,310000.00,Suburbs,2023-02-20,False\n"
        "3,,Downtown,2023-03-10,True\n"
        "4,450000.00,Uptown,2023-04-05,False\n"
    ).encode("utf-8")

    # Upload dataset
    upload_resp = client.post(
        f"/api/v1/projects/{project_id}/datasets",
        files={"file": ("housing.csv", io.BytesIO(csv_content), "text/csv")},
        headers=headers
    )
    assert upload_resp.status_code == 201
    dataset_data = upload_resp.json()

    # Structural assertions
    assert dataset_data["row_count"] == 4
    assert dataset_data["column_count"] == 5
    assert dataset_data["version_number"] == 1
    assert dataset_data["stage"] == "RAW"

    # Verify column inferences
    columns = {col["column_name"]: col for col in dataset_data["columns"]}
    assert len(columns) == 5
    
    # ID -> NUMERIC
    assert columns["id"]["data_type"] == "NUMERIC"
    assert columns["id"]["missing_percentage"] == "0.00" or columns["id"]["missing_percentage"] == 0.0

    # Price -> NUMERIC, is_target -> True (matches target_column), missing_percentage = 25.0
    assert columns["price"]["data_type"] == "NUMERIC"
    assert columns["price"]["is_target"] is True
    assert float(columns["price"]["missing_percentage"]) == 25.0
    assert columns["price"]["unique_count"] == 3

    # Neighborhood -> CATEGORICAL
    assert columns["neighborhood"]["data_type"] == "CATEGORICAL"
    assert columns["neighborhood"]["is_target"] is False
    assert columns["neighborhood"]["unique_count"] == 3

    # Created_at -> DATETIME
    assert columns["created_at"]["data_type"] == "DATETIME"

    # INVARIANT CHECK: Explicitly ensure response contains ZERO profiling, correlation, or Data Quality Index (DQI) metrics
    forbidden_keys = {"data_quality_index", "correlation", "suggested_task_type", "distribution", "skewness", "outliers"}
    for col in dataset_data["columns"]:
        for f_key in forbidden_keys:
            assert f_key not in col, f"Forbidden key '{f_key}' found in column payload violates Day 1 invariant!"
    for f_key in forbidden_keys:
        assert f_key not in dataset_data, f"Forbidden key '{f_key}' found in dataset payload violates Day 1 invariant!"

    # Test Version Increment on second upload
    upload_v2_resp = client.post(
        f"/api/v1/projects/{project_id}/datasets",
        files={"file": ("housing_v2.csv", io.BytesIO(csv_content), "text/csv")},
        headers=headers
    )
    assert upload_v2_resp.status_code == 201
    assert upload_v2_resp.json()["version_number"] == 2
