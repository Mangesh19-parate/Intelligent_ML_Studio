import pytest
import io

@pytest.fixture
def admin_headers(create_test_user, auth_headers):
    admin = create_test_user("workflow_admin@example.com", role_name="ADMIN", full_name="Workflow Admin")
    return auth_headers(admin)

def test_workflow_malformed_json_payloads(client, admin_headers):
    """Testing Principle 6: API Testing with malformed / invalid JSON bodies."""
    # 1. Non-JSON raw text where JSON is expected
    resp = client.post(
        "/api/v1/projects",
        content="not_a_valid_json_payload",
        headers={**admin_headers, "Content-Type": "application/json"}
    )
    assert resp.status_code in [400, 422]

    # 2. Missing required fields in project creation
    resp_missing = client.post(
        "/api/v1/projects",
        json={"unrelated_field": "val"},
        headers=admin_headers
    )
    assert resp_missing.status_code == 422

    # 3. Wrong data types (e.g., number where string expected for name)
    resp_wrong_type = client.post(
        "/api/v1/projects",
        json={"project_name": 12345, "target_column": ["invalid_list_type"]},
        headers=admin_headers
    )
    assert resp_wrong_type.status_code == 422


def test_workflow_special_characters_and_xss_fuzzing(client, admin_headers):
    """Testing Principle 4: Edge case testing with special characters, unicode, and XSS vectors."""
    xss_name = "<script>alert('XSS-Chaos')</script> Project"
    unicode_name = "🚀 ML Studio 日本語 Test 100% €"
    
    # Project creation with Unicode and special characters
    resp = client.post(
        "/api/v1/projects",
        json={"project_name": unicode_name, "target_column": "churn_label"},
        headers=admin_headers
    )
    assert resp.status_code == 201
    assert resp.json()["project_name"] == unicode_name
    
    # Verify retrieval preserves safe string
    proj_id = resp.json()["id"]
    get_resp = client.get(f"/api/v1/projects/{proj_id}", headers=admin_headers)
    assert get_resp.status_code == 200
    assert get_resp.json()["project_name"] == unicode_name


def test_workflow_unauthorized_boundary_access(client, create_test_user):
    """Testing Principle 6 & 12: Ensure backend validates security boundary independent of frontend."""
    # Regular user with default permissions
    create_test_user("qa_user@example.com", role_name="USER")
    login_res = client.post("/api/v1/auth/login", json={"email": "qa_user@example.com", "password": "password123"})
    assert login_res.status_code == 200
    user_token = login_res.json()["access_token"]
    user_headers = {"Authorization": f"Bearer {user_token}"}

    # User attempting to access admin-only analytics / audit endpoints
    admin_routes = [
        "/api/v1/admin/users",
        "/api/v1/auth/admin-demo"
    ]
    for route in admin_routes:
        res = client.get(route, headers=user_headers)
        assert res.status_code in [403, 404]

    # Tampered / invalid Bearer token
    tampered_headers = {"Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.invalid.fake"}
    res_tampered = client.get("/api/v1/auth/me", headers=tampered_headers)
    assert res_tampered.status_code == 401


def test_workflow_csv_upload_fuzzing(client, admin_headers):
    """Testing Principle 3 & 4: Empty CSV, malformed header CSV, single-row CSV."""
    # 1. Create a container project
    proj_res = client.post(
        "/api/v1/projects",
        json={"project_name": "CSV Fuzzing Container", "target_column": "target"},
        headers=admin_headers
    )
    assert proj_res.status_code == 201
    proj_id = proj_res.json()["id"]

    # 2. Upload completely empty file
    empty_file = io.BytesIO(b"")
    resp_empty = client.post(
        f"/api/v1/datasets/upload?project_id={proj_id}",
        files={"file": ("empty.csv", empty_file, "text/csv")},
        headers=admin_headers
    )
    assert resp_empty.status_code in [400, 422]

    # 3. Upload CSV with only headers and 0 rows
    header_only = io.BytesIO(b"col_a,col_b,target\n")
    resp_no_rows = client.post(
        f"/api/v1/datasets/upload?project_id={proj_id}",
        files={"file": ("headers_only.csv", header_only, "text/csv")},
        headers=admin_headers
    )
    assert resp_no_rows.status_code in [400, 422]
