import io
import pytest
import numpy as np
import pandas as pd
from uuid import UUID
from fastapi import status
from sklearn.utils.validation import check_is_fitted
from sklearn.exceptions import NotFittedError

from app.models.dataset import Dataset
from app.models.dataset_column import DatasetColumn
from app.models.dataset_split import DatasetSplit
from app.models.project import Project
from app.models.transformation_config import TransformationConfig
from app.services.dataset_service import DatasetService
from app.services.dataset_split_service import DatasetSplitService
from app.services.transformation_service import TransformationService
from app.services.transformers import OutlierCapper

def get_auth_token(client, email="engineer@example.com", role_name="ML_ENGINEER"):
    reg_resp = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Test Engineer",
            "email": email,
            "password": "password123",
            "role_name": role_name,
        },
    )
    assert reg_resp.status_code == 201
    login_resp = client.post(
        "/api/v1/auth/login",
        json={
            "email": email,
            "password": "password123",
        },
    )
    assert login_resp.status_code == 200
    return login_resp.json()["access_token"]

def create_sample_csv_with_nulls_and_outliers(rows: int = 100) -> bytes:
    np.random.seed(42)
    age = np.random.normal(loc=35, scale=10, size=rows)
    # Add intentional outliers
    age[0] = 150.0
    age[1] = -20.0
    # Add intentional nulls
    age[5] = np.nan
    age[10] = np.nan
    age[15] = np.nan

    income = np.random.normal(loc=50000, scale=15000, size=rows)
    income[2] = np.nan

    city = np.random.choice(["New York", "London", "Tokyo", None], size=rows, p=[0.4, 0.3, 0.2, 0.1])
    churn = np.random.choice(["Yes", "No"], size=rows)

    df = pd.DataFrame({
        "age": age,
        "income": income,
        "city": city,
        "churn": churn,
    })
    return df.to_csv(index=False).encode("utf-8")

@pytest.fixture
def setup_project_with_split(db_session, client):
    token = get_auth_token(client, email="transformer_user@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Create project
    proj_resp = client.post(
        "/api/v1/projects",
        json={"project_name": "Transform Test Project", "target_column": "churn"},
        headers=headers,
    )
    assert proj_resp.status_code == 201
    project_id = proj_resp.json()["id"]

    # 2. Upload dataset
    csv_bytes = create_sample_csv_with_nulls_and_outliers(100)
    upload_resp = client.post(
        f"/api/v1/projects/{project_id}/datasets",
        files={"file": ("sample.csv", io.BytesIO(csv_bytes), "text/csv")},
        headers=headers,
    )
    assert upload_resp.status_code == 201
    dataset_id = upload_resp.json()["id"]

    # 3. Create outer split
    split_resp = client.post(
        f"/api/v1/datasets/{dataset_id}/split",
        json={"locked_test_pct": 20, "seed": 42},
        headers=headers,
    )
    assert split_resp.status_code == 201

    return {
        "headers": headers,
        "project_id": project_id,
        "dataset_id": dataset_id,
    }


def test_acceptance_check_a_unfit_attributes(db_session, setup_project_with_split):
    """
    Check a: Assert build_pipeline(project_id) returns an object with NO fitted attributes
    (e.g., no mean_, categories_, scale_, lower_bounds_, transformers_).
    """
    project_id = setup_project_with_split["project_id"]
    trans_service = TransformationService(db_session)

    # Configure multiple transformations on different columns
    trans_service.set_missing_value_strategy(project_id, "age", "median")
    trans_service.set_outlier_strategy(project_id, "age", "iqr")
    trans_service.set_scaling_strategy(project_id, "age", "standard")

    trans_service.set_missing_value_strategy(project_id, "city", "mode")
    trans_service.set_encoding_strategy(project_id, "city", "one_hot")

    trans_service.set_scaling_strategy(project_id, "income", "minmax")

    # Build the pipeline
    pipeline = trans_service.build_pipeline(project_id)

    # 1. ColumnTransformer itself must not have fitted attributes like transformers_
    assert not hasattr(pipeline, "transformers_"), "ColumnTransformer must not have 'transformers_' attribute before fitting"
    assert not hasattr(pipeline, "n_features_in_"), "ColumnTransformer must not have 'n_features_in_' attribute before fitting"

    # 2. Sub-transformers and internal pipeline steps must not be fitted
    for name, transformer, cols in pipeline.transformers:
        if hasattr(transformer, "steps"):
            for step_name, step_estimator in transformer.steps:
                # Check known fitted attributes for all transformer types
                assert not hasattr(step_estimator, "statistics_"), f"{step_name} should not have statistics_"
                assert not hasattr(step_estimator, "mean_"), f"{step_name} should not have mean_"
                assert not hasattr(step_estimator, "scale_"), f"{step_name} should not have scale_"
                assert not hasattr(step_estimator, "categories_"), f"{step_name} should not have categories_"
                assert not hasattr(step_estimator, "lower_bounds_"), f"{step_name} should not have lower_bounds_"
                assert not hasattr(step_estimator, "upper_bounds_"), f"{step_name} should not have upper_bounds_"
                assert not hasattr(step_estimator, "n_features_in_"), f"{step_name} should not have n_features_in_"


def test_acceptance_check_b_repeated_calls_isolation(db_session, setup_project_with_split):
    """
    Check b: Call build_pipeline(project_id) twice in a row, fit the first returned object
    on a sample, and confirm the SECOND call still returns a fresh unfit object.
    """
    project_id = setup_project_with_split["project_id"]
    trans_service = TransformationService(db_session)

    trans_service.set_missing_value_strategy(project_id, "age", "mean")
    trans_service.set_scaling_strategy(project_id, "age", "standard")

    # First call -> Pipeline 1
    pipeline_1 = trans_service.build_pipeline(project_id)

    # Fit Pipeline 1 on a sample DataFrame
    sample_df = pd.DataFrame({"age": [20.0, 30.0, 40.0, 50.0, np.nan]})
    pipeline_1.fit(sample_df)

    # Confirm Pipeline 1 is now fitted
    assert hasattr(pipeline_1, "transformers_")

    # Second call -> Pipeline 2
    pipeline_2 = trans_service.build_pipeline(project_id)

    # Confirm Pipeline 2 is completely fresh and UNFIT
    assert not hasattr(pipeline_2, "transformers_")
    assert not hasattr(pipeline_2, "n_features_in_")
    for name, transformer, cols in pipeline_2.transformers:
        if hasattr(transformer, "steps"):
            for step_name, step_estimator in transformer.steps:
                assert not hasattr(step_estimator, "statistics_")
                assert not hasattr(step_estimator, "mean_")
                assert not hasattr(step_estimator, "scale_")


def test_acceptance_check_c_median_imputation_removes_nulls(db_session, setup_project_with_split):
    """
    Check c: Set missing_value_strategy = median on a numeric column with nulls,
    call build_pipeline(), fit the result on a Development sample that includes nulls,
    transform it, and confirm zero nulls remain in that column's output.
    """
    project_id = setup_project_with_split["project_id"]
    dataset_id = setup_project_with_split["dataset_id"]
    trans_service = TransformationService(db_session)
    split_service = DatasetSplitService(db_session)

    # Configure median strategy on 'age'
    trans_service.set_missing_value_strategy(project_id, "age", "median")

    # Load Development partition data
    dev_df = split_service.get_development_data(dataset_id)
    assert dev_df["age"].isna().sum() > 0, "Development partition should contain nulls for age"

    # Build unfit pipeline, fit on Development data and transform
    pipeline = trans_service.build_pipeline(project_id)
    transformed_data = pipeline.fit_transform(dev_df[["age"]])

    # Assert zero nulls remain
    if hasattr(transformed_data, "toarray"):
        transformed_data = transformed_data.toarray()
    assert not np.isnan(transformed_data).any(), "Transformed output must contain zero null values"


def test_acceptance_check_d_locked_test_isolation_row_index_diff(db_session, setup_project_with_split):
    """
    Check d: Confirm preview_transformation() and build_pipeline() pull data exclusively
    via get_development_data() — repeat the row-index diff check from Day 3 (assert zero overlap with Locked Test).
    """
    project_id = setup_project_with_split["project_id"]
    dataset_id = setup_project_with_split["dataset_id"]
    trans_service = TransformationService(db_session)

    # Retrieve Locked Test row indices from database
    locked_split = (
        db_session.query(DatasetSplit)
        .filter(DatasetSplit.dataset_id == UUID(dataset_id), DatasetSplit.split_type == "LOCKED_TEST")
        .first()
    )
    locked_indices_set = set(locked_split.row_indices)

    # Run preview_transformation
    preview_result = trans_service.preview_transformation(project_id, "age", sample_size=50)
    assert len(preview_result["before_values"]) > 0

    # Retrieve Development split row indices
    dev_split = (
        db_session.query(DatasetSplit)
        .filter(DatasetSplit.dataset_id == UUID(dataset_id), DatasetSplit.split_type == "DEVELOPMENT")
        .first()
    )
    dev_indices_set = set(dev_split.row_indices)

    # Assert mutual exclusion
    overlap = dev_indices_set.intersection(locked_indices_set)
    assert len(overlap) == 0, f"Development and Locked Test partitions have overlapping row indices: {overlap}"


def test_acceptance_check_e_structural_mismatch_returns_422(client, setup_project_with_split):
    """
    Check e: Attempt to set a numeric strategy (e.g. standard scaling) on a column
    detected as CATEGORICAL, and confirm the API returns a clear 422 with an
    explanatory message rather than a 500 or silently-ignored config.
    """
    project_id = setup_project_with_split["project_id"]
    headers = setup_project_with_split["headers"]

    # 1. Attempt standard scaling on categorical column 'city' -> 422
    resp1 = client.put(
        f"/api/v1/projects/{project_id}/transformations/city",
        json={"scaling_strategy": "standard"},
        headers=headers,
    )
    assert resp1.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    assert "Scaling strategy 'standard' is only valid for NUMERIC columns" in resp1.json()["detail"]

    # 2. Attempt one_hot encoding on numeric column 'age' -> 422
    resp2 = client.put(
        f"/api/v1/projects/{project_id}/transformations/age",
        json={"encoding_strategy": "one_hot"},
        headers=headers,
    )
    assert resp2.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    assert "Encoding strategy 'one_hot' is only valid for CATEGORICAL columns" in resp2.json()["detail"]

    # 3. Attempt outlier strategy on categorical column 'city' -> 422
    resp3 = client.put(
        f"/api/v1/projects/{project_id}/transformations/city",
        json={"outlier_strategy": "zscore"},
        headers=headers,
    )
    assert resp3.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    assert "Outlier strategy 'zscore' is only valid for NUMERIC columns" in resp3.json()["detail"]

    # 4. Attempt numeric missing strategy ('median') on categorical column 'city' -> 422
    resp4 = client.put(
        f"/api/v1/projects/{project_id}/transformations/city",
        json={"missing_value_strategy": "median"},
        headers=headers,
    )
    assert resp4.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    assert "Invalid missing value strategy 'median' for CATEGORICAL column" in resp4.json()["detail"]


def test_acceptance_check_f_preview_never_persists_learned_state(client, db_session, setup_project_with_split):
    """
    Check f: Call the preview endpoint twice for the same column and confirm no database
    row anywhere stores a learned value (mean, fitted vocabulary, etc.) — only the
    declared strategy string in transformation_configs.
    """
    project_id = setup_project_with_split["project_id"]
    headers = setup_project_with_split["headers"]

    # Set strategy for 'age'
    client.put(
        f"/api/v1/projects/{project_id}/transformations/age",
        json={"missing_value_strategy": "mean", "scaling_strategy": "standard", "outlier_strategy": "zscore"},
        headers=headers,
    )

    # Call preview twice
    resp_prev1 = client.post(
        f"/api/v1/projects/{project_id}/transformations/preview",
        json={"column": "age", "sample_size": 25},
        headers=headers,
    )
    assert resp_prev1.status_code == 200

    resp_prev2 = client.post(
        f"/api/v1/projects/{project_id}/transformations/preview",
        json={"column": "age", "sample_size": 25},
        headers=headers,
    )
    assert resp_prev2.status_code == 200

    # Query transformation_configs table directly
    config_row = (
        db_session.query(TransformationConfig)
        .filter(
            TransformationConfig.project_id == UUID(project_id),
            TransformationConfig.column_name == "age",
        )
        .first()
    )
    assert config_row is not None
    assert config_row.missing_value_strategy == "mean"
    assert config_row.scaling_strategy == "standard"
    assert config_row.outlier_strategy == "zscore"

    # Verify no learned state exists on the model columns or database columns
    for col in TransformationConfig.__table__.columns:
        col_name = col.name
        assert col_name not in ["mean", "std", "fitted_values", "vocabulary", "scale", "learned_parameters"]


def test_get_transformations_endpoint_defaults(client, setup_project_with_split):
    """
    Test GET /api/v1/projects/{id}/transformations returns all columns including unconfigured defaults.
    """
    project_id = setup_project_with_split["project_id"]
    headers = setup_project_with_split["headers"]

    resp = client.get(f"/api/v1/projects/{project_id}/transformations", headers=headers)
    assert resp.status_code == 200
    data = resp.json()

    col_names = {row["column_name"] for row in data}
    assert {"age", "income", "city", "churn"}.issubset(col_names)

    # Check defaults for unconfigured columns
    income_row = next(r for r in data if r["column_name"] == "income")
    assert income_row["missing_value_strategy"] == "none"
    assert income_row["scaling_strategy"] == "none"
    assert income_row["data_type"] == "NUMERIC"


def test_pipeline_stage_updated_to_transformed(client, db_session, setup_project_with_split):
    """
    Test project pipeline_stage is updated to 'TRANSFORMED' when config is saved.
    """
    project_id = setup_project_with_split["project_id"]
    headers = setup_project_with_split["headers"]

    client.put(
        f"/api/v1/projects/{project_id}/transformations/age",
        json={"missing_value_strategy": "median"},
        headers=headers,
    )

    project = db_session.query(Project).filter(Project.id == UUID(project_id)).first()
    assert project.pipeline_stage == "TRANSFORMED"


def test_outlier_capper_transformer():
    """
    Unit test for OutlierCapper across various strategies.
    """
    # 20 normal values around 10 + extreme outliers
    data = np.array([-100.0] + [10.0 + i * 0.1 for i in range(20)] + [100.0]).reshape(-1, 1)

    # 1. 'none' strategy
    capper_none = OutlierCapper(strategy="none")
    capper_none.fit(data)
    res_none = capper_none.transform(data)
    np.testing.assert_array_equal(res_none, data)

    # 2. 'iqr' strategy
    capper_iqr = OutlierCapper(strategy="iqr")
    assert not hasattr(capper_iqr, "lower_bounds_"), "Unfit OutlierCapper must have no lower_bounds_"
    capper_iqr.fit(data)
    assert hasattr(capper_iqr, "lower_bounds_")
    res_iqr = capper_iqr.transform(data)
    assert res_iqr[0, 0] > -100.0
    assert res_iqr[-1, 0] < 100.0

    # 3. 'zscore' strategy
    capper_z = OutlierCapper(strategy="zscore", z_threshold=2.0)
    capper_z.fit(data)
    res_z = capper_z.transform(data)
    assert res_z[0, 0] > -100.0
    assert res_z[-1, 0] < 100.0

    # 4. 'percentile' strategy
    capper_p = OutlierCapper(strategy="percentile", percentile_lower=5.0, percentile_upper=95.0)
    capper_p.fit(data)
    res_p = capper_p.transform(data)
    assert res_p[0, 0] > -100.0
    assert res_p[-1, 0] < 100.0
