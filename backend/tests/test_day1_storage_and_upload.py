import io
import json
import pytest
import pandas as pd
from uuid import uuid4
from pathlib import Path
from app.services.storage_service import LocalStorageService, get_storage_service

def test_local_storage_service_unit(tmp_path):
    storage = LocalStorageService(base_dir=str(tmp_path))
    project_id = uuid4()
    content = b"col1,col2\n1,2\n3,4\n"
    
    # 1. Save file
    saved_path = storage.save_file(project_id, 1, "data.csv", content)
    assert Path(saved_path).exists()
    assert storage.exists(saved_path)
    
    # 2. Path resolution
    resolved_path = storage.get_file_path(saved_path)
    assert resolved_path == saved_path
    
    # 3. Read bytes
    retrieved_bytes = storage.get_file_bytes(saved_path)
    assert retrieved_bytes == content
    
    # 4. Path traversal protection
    traversal_path = storage.save_file(project_id, 1, "../../../malicious.csv", content)
    assert ".." not in Path(traversal_path).name
    assert Path(traversal_path).name == "malicious.csv"
    assert Path(traversal_path).parent.resolve() == (tmp_path / "datasets" / str(project_id) / "1").resolve()
    
    # 5. Delete file
    assert storage.delete_file(saved_path) is True
    assert not storage.exists(saved_path)
    assert storage.delete_file(saved_path) is False
    
    # 6. Non-existent file raises FileNotFoundError
    with pytest.raises(FileNotFoundError):
        storage.get_file_bytes(saved_path)
    with pytest.raises(FileNotFoundError):
        storage.get_file_path(saved_path)

def test_storage_service_singleton():
    storage = get_storage_service()
    assert storage is not None
    assert isinstance(storage, LocalStorageService)

def test_dataset_upload_csv(client, create_test_user):
    user = create_test_user("steward_d1@example.com", role_name="DATA_STEWARD")
    login_resp = client.post(
        "/api/v1/auth/login",
        json={"email": "steward_d1@example.com", "password": "password123"}
    ).json()
    headers = {"Authorization": f"Bearer {login_resp['access_token']}"}

    # Create project
    proj_resp = client.post(
        "/api/v1/projects",
        json={"project_name": "Day 1 Churn Test", "target_column": "churn"},
        headers=headers
    )
    assert proj_resp.status_code == 201
    project_id = proj_resp.json()["id"]

    # CSV data
    csv_bytes = b"id,age,income,churn\n1,25,50000.0,0\n2,40,90000.0,1\n3,30,,0\n"

    # POST /api/v1/datasets/upload
    upload_resp = client.post(
        "/api/v1/datasets/upload",
        data={"project_id": project_id},
        files={"file": ("churn.csv", io.BytesIO(csv_bytes), "text/csv")},
        headers=headers
    )
    assert upload_resp.status_code == 201
    data = upload_resp.json()

    # Verify Day 1 properties and invariants
    assert data["project_id"] == project_id
    assert data["version_number"] == 1
    assert data["stage"] == "RAW"
    assert data["row_count"] == 3
    assert data["column_count"] == 4
    assert data["content_hash"] is not None
    assert len(data["content_hash"]) == 64

    # Structural columns
    columns = {c["column_name"]: c for c in data["columns"]}
    assert "id" in columns and columns["id"]["data_type"] == "NUMERIC"
    assert "age" in columns and columns["age"]["data_type"] == "NUMERIC"
    assert "income" in columns and columns["income"]["data_type"] == "NUMERIC"
    assert float(columns["income"]["missing_percentage"]) > 0
    assert "churn" in columns and columns["churn"]["is_target"] is True

    # Pre-split boundary invariant check: No profiling metrics
    forbidden = ["skewness", "kurtosis", "data_quality_index", "correlation", "suggested_task_type"]
    for col in data["columns"]:
        for f in forbidden:
            assert f not in col
    for f in forbidden:
        assert f not in data

def test_dataset_upload_version_increment(client, create_test_user):
    user = create_test_user("mle_d1@example.com", role_name="ML_ENGINEER")
    login_resp = client.post(
        "/api/v1/auth/login",
        json={"email": "mle_d1@example.com", "password": "password123"}
    ).json()
    headers = {"Authorization": f"Bearer {login_resp['access_token']}"}

    proj_resp = client.post(
        "/api/v1/projects",
        json={"project_name": "Multi-version Project"},
        headers=headers
    )
    project_id = proj_resp.json()["id"]

    csv_v1 = b"a,b\n1,2\n3,4\n"
    csv_v2 = b"a,b,c\n1,2,3\n4,5,6\n7,8,9\n"

    # Upload v1
    resp1 = client.post(
        "/api/v1/datasets/upload",
        data={"project_id": project_id},
        files={"file": ("data_v1.csv", io.BytesIO(csv_v1), "text/csv")},
        headers=headers
    )
    assert resp1.status_code == 201
    assert resp1.json()["version_number"] == 1
    assert resp1.json()["row_count"] == 2
    assert resp1.json()["column_count"] == 2

    # Upload v2
    resp2 = client.post(
        "/api/v1/datasets/upload",
        data={"project_id": project_id},
        files={"file": ("data_v2.csv", io.BytesIO(csv_v2), "text/csv")},
        headers=headers
    )
    assert resp2.status_code == 201
    assert resp2.json()["version_number"] == 2
    assert resp2.json()["row_count"] == 3
    assert resp2.json()["column_count"] == 3

def test_dataset_upload_excel_and_json(client, create_test_user):
    user = create_test_user("admin_d1@example.com", role_name="ADMIN")
    login_resp = client.post(
        "/api/v1/auth/login",
        json={"email": "admin_d1@example.com", "password": "password123"}
    ).json()
    headers = {"Authorization": f"Bearer {login_resp['access_token']}"}

    proj_resp = client.post(
        "/api/v1/projects",
        json={"project_name": "Formats Test Project"},
        headers=headers
    )
    project_id = proj_resp.json()["id"]

    # 1. JSON upload
    json_data = [
        {"feature_a": 10, "feature_b": "Alpha", "timestamp": "2026-01-01T00:00:00Z"},
        {"feature_a": 20, "feature_b": "Beta", "timestamp": "2026-01-02T00:00:00Z"},
    ]
    json_bytes = json.dumps(json_data).encode("utf-8")

    json_resp = client.post(
        "/api/v1/datasets/upload",
        data={"project_id": project_id},
        files={"file": ("records.json", io.BytesIO(json_bytes), "application/json")},
        headers=headers
    )
    assert json_resp.status_code == 201
    j_data = json_resp.json()
    assert j_data["row_count"] == 2
    assert j_data["column_count"] == 3
    assert j_data["stage"] == "RAW"

    # 2. Excel (XLSX) upload
    df = pd.DataFrame({
        "metric_x": [1.5, 2.7, 3.9],
        "category": ["A", "B", "C"]
    })
    excel_buffer = io.BytesIO()
    df.to_excel(excel_buffer, index=False, engine="openpyxl")
    excel_bytes = excel_buffer.getvalue()

    excel_resp = client.post(
        "/api/v1/datasets/upload",
        data={"project_id": project_id},
        files={"file": ("metrics.xlsx", io.BytesIO(excel_bytes), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        headers=headers
    )
    assert excel_resp.status_code == 201
    e_data = excel_resp.json()
    assert e_data["row_count"] == 3
    assert e_data["column_count"] == 2
    assert e_data["version_number"] == 2

def test_dataset_upload_errors_and_rbac(client, create_test_user):
    steward = create_test_user("steward_err@example.com", role_name="DATA_STEWARD")
    viewer = create_test_user("viewer_err@example.com", role_name="VIEWER")
    
    steward_token = client.post("/api/v1/auth/login", json={"email": "steward_err@example.com", "password": "password123"}).json()["access_token"]
    viewer_token = client.post("/api/v1/auth/login", json={"email": "viewer_err@example.com", "password": "password123"}).json()["access_token"]

    steward_headers = {"Authorization": f"Bearer {steward_token}"}
    viewer_headers = {"Authorization": f"Bearer {viewer_token}"}

    proj = client.post("/api/v1/projects", json={"project_name": "Error Checks"}, headers=steward_headers).json()
    project_id = proj["id"]

    # 1. Empty file
    res_empty = client.post(
        "/api/v1/datasets/upload",
        data={"project_id": project_id},
        files={"file": ("empty.csv", io.BytesIO(b""), "text/csv")},
        headers=steward_headers
    )
    assert res_empty.status_code == 400

    # 2. Unsupported extension
    res_unsupported = client.post(
        "/api/v1/datasets/upload",
        data={"project_id": project_id},
        files={"file": ("test.pdf", io.BytesIO(b"%PDF-1.4..."), "application/pdf")},
        headers=steward_headers
    )
    assert res_unsupported.status_code == 400
    assert "Unsupported file format" in res_unsupported.json()["detail"]

    # 3. Non-existent project
    random_id = str(uuid4())
    res_no_proj = client.post(
        "/api/v1/datasets/upload",
        data={"project_id": random_id},
        files={"file": ("data.csv", io.BytesIO(b"a,b\n1,2\n"), "text/csv")},
        headers=steward_headers
    )
    assert res_no_proj.status_code == 404

    # 4. RBAC: Viewer lacks EDIT_DATA
    res_viewer = client.post(
        "/api/v1/datasets/upload",
        data={"project_id": project_id},
        files={"file": ("data.csv", io.BytesIO(b"a,b\n1,2\n"), "text/csv")},
        headers=viewer_headers
    )
    assert res_viewer.status_code == 403
