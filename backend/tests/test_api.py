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
    # Create a VIEWER user (has only 'READ' permission)
    viewer = create_test_user("viewer@example.com", role_name="VIEWER")
    
    # Login as VIEWER
    viewer_login = client.post(
        "/api/v1/auth/login",
        json={"email": "viewer@example.com", "password": "password123"}
    ).json()
    viewer_token = viewer_login["access_token"]
    viewer_headers = {"Authorization": f"Bearer {viewer_token}"}

    # VIEWER can read projects list
    read_resp = client.get("/api/v1/projects", headers=viewer_headers)
    assert read_resp.status_code == 200

    # VIEWER cannot create projects (requires EDIT_DATA permission)
    create_resp = client.post(
        "/api/v1/projects",
        json={"project_name": "Unauthorized Project"},
        headers=viewer_headers
    )
    assert create_resp.status_code == 403
    assert "EDIT_DATA" in create_resp.json()["detail"]

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

    # INVARIANT CHECK: Explicitly ensure response contains ZERO profiling, correlation, or health score metrics
    forbidden_keys = {"health_score", "correlation", "suggested_task_type", "distribution", "skewness", "outliers"}
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
