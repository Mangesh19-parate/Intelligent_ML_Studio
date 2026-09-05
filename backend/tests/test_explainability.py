import os
import json
import hashlib
from uuid import uuid4
from unittest.mock import patch, MagicMock
import numpy as np
import pandas as pd
import pytest
import shap
from fastapi import HTTPException

from app.models.project import Project
from app.models.dataset import Dataset
from app.models.dataset_column import DatasetColumn
from app.models.dataset_split import DatasetSplit
from app.models.transformation_config import TransformationConfig
from app.models.transformation_snapshot import TransformationSnapshot
from app.models.feature_selection_snapshot import FeatureSelectionSnapshot
from app.models.experiment import Experiment
from app.models.trained_model import TrainedModel
from app.models.explainability_summary import ExplainabilitySummary
from app.services.experiment_service import ExperimentService
from app.services.explainability_service import ExplainabilityService
from app.services.dataset_split_service import DatasetSplitService


@pytest.fixture
def regression_setup(db_session, tmp_path, create_test_user):
    """
    Creates a realistic Regression project with uploaded dataset, splits, and transformation configs.
    Target: price = 300 * sqft + 5000 * bedrooms + noise
    """
    user = create_test_user("ml_owner@test.com", "ML_ENGINEER")

    project = Project(
        id=uuid4(),
        owner_id=user.id,
        project_name="Housing Pricing Engine",
        task_type="REGRESSION",
        target_column="price",
        pipeline_stage="SPLIT",
    )
    db_session.add(project)
    db_session.commit()

    # Generate synthetic tabular dataset with clear feature relationships
    np.random.seed(42)
    n_samples = 150
    sqft = np.random.uniform(500, 3500, n_samples)
    bedrooms = np.random.randint(1, 6, n_samples).astype(float)
    noise_feat = np.random.uniform(0, 1, n_samples)
    price = 300.0 * sqft + 5000.0 * bedrooms + 1000.0 * np.random.randn(n_samples)

    df = pd.DataFrame({
        "sqft": sqft,
        "bedrooms": bedrooms,
        "noise_feat": noise_feat,
        "price": price,
    })

    data_bytes = df.to_csv(index=False).encode("utf-8")
    content_hash = hashlib.sha256(data_bytes).hexdigest()

    dataset_path = str(tmp_path / "housing.csv")
    with open(dataset_path, "wb") as f:
        f.write(data_bytes)

    dataset = Dataset(
        id=uuid4(),
        project_id=project.id,
        version_number=1,
        file_path=dataset_path,
        row_count=n_samples,
        column_count=4,
        content_hash=content_hash,
    )
    db_session.add(dataset)
    db_session.commit()

    # Columns
    cols = [
        ("sqft", "NUMERIC", False),
        ("bedrooms", "NUMERIC", False),
        ("noise_feat", "NUMERIC", False),
        ("price", "NUMERIC", True),
    ]
    for cname, dtype, is_tgt in cols:
        db_session.add(
            DatasetColumn(
                id=uuid4(),
                dataset_id=dataset.id,
                column_name=cname,
                data_type=dtype,
                unique_count=len(df[cname].unique()),
                missing_percentage=0.0,
                is_target=is_tgt,
            )
        )
    db_session.commit()

    # Splits: 80% Dev (120 rows), 20% Locked Test (30 rows)
    all_indices = list(range(n_samples))
    np.random.seed(42)
    np.random.shuffle(all_indices)
    dev_indices = all_indices[:120]
    test_indices = all_indices[120:]

    db_session.add(
        DatasetSplit(
            id=uuid4(),
            dataset_id=dataset.id,
            split_type="DEVELOPMENT",
            row_indices=dev_indices,
            split_seed=42,
        )
    )
    db_session.add(
        DatasetSplit(
            id=uuid4(),
            dataset_id=dataset.id,
            split_type="LOCKED_TEST",
            row_indices=test_indices,
            split_seed=42,
        )
    )
    db_session.commit()

    # Transformation Configs
    for col in ["sqft", "bedrooms", "noise_feat"]:
        db_session.add(
            TransformationConfig(
                id=uuid4(),
                project_id=project.id,
                column_name=col,
                missing_value_strategy="MEAN",
                scaling_strategy="STANDARD",
                is_active=True,
            )
        )
    db_session.commit()

    return {
        "user": user,
        "project": project,
        "dataset": dataset,
        "dev_indices": dev_indices,
        "test_indices": test_indices,
    }


@pytest.fixture
def classification_setup(db_session, tmp_path, create_test_user):
    """
    Creates a realistic Classification project for checking LogisticRegression & tree explainers.
    """
    user = create_test_user("clf_owner@test.com", "ML_ENGINEER")

    project = Project(
        id=uuid4(),
        owner_id=user.id,
        project_name="Customer Churn Engine",
        task_type="CLASSIFICATION",
        target_column="churn",
        pipeline_stage="SPLIT",
    )
    db_session.add(project)
    db_session.commit()

    np.random.seed(42)
    n_samples = 150
    usage = np.random.uniform(10, 100, n_samples)
    tenure = np.random.uniform(1, 24, n_samples)
    churn = ((usage < 40) & (tenure < 6)).astype(int)

    df = pd.DataFrame({
        "usage": usage,
        "tenure": tenure,
        "churn": churn,
    })

    data_bytes = df.to_csv(index=False).encode("utf-8")
    content_hash = hashlib.sha256(data_bytes).hexdigest()

    dataset_path = str(tmp_path / "churn.csv")
    with open(dataset_path, "wb") as f:
        f.write(data_bytes)

    dataset = Dataset(
        id=uuid4(),
        project_id=project.id,
        version_number=1,
        file_path=dataset_path,
        row_count=n_samples,
        column_count=3,
        content_hash=content_hash,
    )
    db_session.add(dataset)
    db_session.commit()

    for cname, dtype, is_tgt in [("usage", "NUMERIC", False), ("tenure", "NUMERIC", False), ("churn", "CATEGORICAL", True)]:
        db_session.add(
            DatasetColumn(
                id=uuid4(),
                dataset_id=dataset.id,
                column_name=cname,
                data_type=dtype,
                unique_count=len(df[cname].unique()),
                missing_percentage=0.0,
                is_target=is_tgt,
            )
        )
    db_session.commit()

    all_indices = list(range(n_samples))
    dev_indices = all_indices[:120]
    test_indices = all_indices[120:]

    db_session.add(
        DatasetSplit(
            id=uuid4(),
            dataset_id=dataset.id,
            split_type="DEVELOPMENT",
            row_indices=dev_indices,
            split_seed=42,
        )
    )
    db_session.add(
        DatasetSplit(
            id=uuid4(),
            dataset_id=dataset.id,
            split_type="LOCKED_TEST",
            row_indices=test_indices,
            split_seed=42,
        )
    )
    db_session.commit()

    for col in ["usage", "tenure"]:
        db_session.add(
            TransformationConfig(
                id=uuid4(),
                project_id=project.id,
                column_name=col,
                missing_value_strategy="MEAN",
                scaling_strategy="STANDARD",
                is_active=True,
            )
        )
    db_session.commit()

    return {
        "user": user,
        "project": project,
        "dataset": dataset,
        "dev_indices": dev_indices,
        "test_indices": test_indices,
    }


def test_acceptance_check_a_global_shap_summary_and_caching(db_session, regression_setup):
    """
    Check a) Call `global_shap_summary` for the winning model of a completed experiment;
    confirm it succeeds and returns plausible values (features known to matter for test dataset
    should have higher mean-abs-SHAP than irrelevant ones).
    Call it a SECOND time and confirm — via a spy/counter inside computation path — that
    the actual SHAP computation did NOT run again; only the cached `explainability_summaries` row was read.
    """
    project = regression_setup["project"]
    exp_service = ExperimentService(db_session)
    expl_service = ExplainabilityService(db_session)

    # 1. Run full experiment with LinearRegression and RandomForestRegressor (auto_finalize=True)
    exp_res = exp_service.run_experiment(
        project_id=project.id,
        algorithms=["RandomForestRegressor", "LinearRegression"],
        folds=3,
        seed=42,
        selection_metric="rmse",
        selection_direction="MINIMIZE",
        auto_finalize=True,
    )
    winning_model_id = exp_res["selected_model_id"]

    winning_model = db_session.query(TrainedModel).filter(TrainedModel.id == winning_model_id).first()
    assert winning_model.artifact_path is not None
    assert winning_model.artifact_checksum is not None

    # 3. Call global_shap_summary FIRST time
    res1 = expl_service.global_shap_summary(winning_model_id, background_sample_size=100)
    assert res1.model_id == winning_model_id
    assert res1.is_cached is False
    assert res1.explainer_type in ("TREE", "LINEAR")
    assert len(res1.shap_values) > 0

    # Plausibility check: sqft or bedrooms should have significantly higher impact than noise_feat
    shap_vals = res1.shap_values
    sqft_shap = next((val for k, val in shap_vals.items() if "sqft" in k), 0.0)
    noise_shap = next((val for k, val in shap_vals.items() if "noise" in k), 0.0)
    assert sqft_shap > noise_shap, f"Important feature 'sqft' ({sqft_shap}) must have higher SHAP than noise ({noise_shap})"

    # Verify database row was written
    cached_row = db_session.query(ExplainabilitySummary).filter(ExplainabilitySummary.model_id == winning_model_id).first()
    assert cached_row is not None
    assert cached_row.background_sample_size == res1.background_sample_size
    assert cached_row.explainer_type == res1.explainer_type

    # 4. Call global_shap_summary SECOND time with a spy on _load_artifact
    with patch.object(expl_service, "_load_artifact", wraps=expl_service._load_artifact) as spy_load:
        res2 = expl_service.global_shap_summary(winning_model_id, background_sample_size=100)
        assert res2.is_cached is True
        assert res2.shap_values == res1.shap_values
        # Must NOT have reloaded the artifact or recomputed SHAP
        spy_load.assert_not_called()


def test_acceptance_check_b_non_winning_model_returns_422(db_session, regression_setup, client):
    """
    Check b) Call the explainability endpoint for a non-winning `trained_models` row from
    the same experiment (one that has metrics but `artifact_path = NULL`) and confirm
    a clear 422 with an explanatory message, not a crash.
    """
    project = regression_setup["project"]
    user = regression_setup["user"]
    exp_service = ExperimentService(db_session)
    expl_service = ExplainabilityService(db_session)

    # Run experiment
    exp_res = exp_service.run_experiment(
        project_id=project.id,
        algorithms=["RandomForestRegressor", "LinearRegression"],
        folds=3,
        seed=42,
        selection_metric="rmse",
        selection_direction="MINIMIZE",
        auto_finalize=True,
    )
    experiment_id = exp_res["experiment_id"]
    winning_model_id = exp_res["selected_model_id"]

    # Find non-winning model
    non_winning_model = (
        db_session.query(TrainedModel)
        .filter(TrainedModel.experiment_id == experiment_id, TrainedModel.id != winning_model_id)
        .first()
    )
    assert non_winning_model is not None
    assert non_winning_model.artifact_path is None

    # Call ExplainabilityService directly -> raises HTTPException(422)
    with pytest.raises(HTTPException) as exc_info:
        expl_service.global_shap_summary(non_winning_model.id)
    assert exc_info.value.status_code == 422
    assert "This model has no persisted artifact — explainability is only available for the winning model of a completed experiment" in exc_info.value.detail

    # Call via API endpoint with auth headers
    from app.core.security import create_access_token
    token = create_access_token(subject=str(user.id))
    headers = {"Authorization": f"Bearer {token}"}

    response = client.get(f"/api/v1/models/{non_winning_model.id}/explainability", headers=headers)
    assert response.status_code == 422
    assert "This model has no persisted artifact" in response.json()["detail"]


def test_acceptance_check_c_select_explainer_classes(db_session, regression_setup, classification_setup):
    """
    Check c) Confirm `_select_explainer` picks `TreeExplainer` for a RandomForest-backed
    model and `LinearExplainer` for a LogisticRegression-backed model — assert on the actual
    explainer class instantiated in each case, not just that the call succeeded.
    """
    expl_service = ExplainabilityService(db_session)

    # 1. TreeExplainer check (RandomForestRegressor & RandomForestClassifier)
    from sklearn.ensemble import RandomForestRegressor, RandomForestClassifier
    rf_reg = RandomForestRegressor().fit(np.array([[1, 2], [3, 4]]), np.array([10, 20]))
    fitted_tree_pipe = {"estimator": rf_reg}
    tree_exp, tree_type = expl_service._select_explainer("RandomForestRegressor", fitted_tree_pipe)
    assert isinstance(tree_exp, shap.TreeExplainer), f"Expected shap.TreeExplainer, got {type(tree_exp)}"
    assert tree_type == "TREE"

    # 2. LinearExplainer check (LogisticRegression & LinearRegression)
    from sklearn.linear_model import LogisticRegression
    lr_clf = LogisticRegression().fit(np.array([[1, 2], [3, 4]]), np.array([0, 1]))
    bg_data = np.array([[1.5, 2.5], [2.5, 3.5]])
    fitted_linear_pipe = {"estimator": lr_clf}
    lin_exp, lin_type = expl_service._select_explainer("LogisticRegression", fitted_linear_pipe, background_data=bg_data)
    assert isinstance(lin_exp, shap.LinearExplainer), f"Expected shap.LinearExplainer, got {type(lin_exp)}"
    assert lin_type == "LINEAR"


def test_acceptance_check_d_additivity_sanity_check(db_session, regression_setup):
    """
    Check d) Additivity sanity check: for one specific Development-derived input row,
    sum the local SHAP contributions plus the base/expected value and confirm it
    approximately equals the model's actual prediction for that row (within floating-point tolerance).
    """
    project = regression_setup["project"]
    exp_service = ExperimentService(db_session)
    expl_service = ExplainabilityService(db_session)

    # Run and finalize experiment
    exp_res = exp_service.run_experiment(
        project_id=project.id,
        algorithms=["RandomForestRegressor"],
        folds=3,
        seed=42,
        selection_metric="rmse",
        selection_direction="MINIMIZE",
        auto_finalize=True,
    )
    experiment_id = exp_res["experiment_id"]
    winning_model_id = exp_res["selected_model_id"]

    # Retrieve one specific Development-derived input row
    split_service = DatasetSplitService(db_session)
    df_dev = split_service.get_development_data(regression_setup["dataset"].id)
    input_row = df_dev.iloc[0].to_dict()

    # Call local_shap_explanation
    local_exp = expl_service.local_shap_explanation(winning_model_id, input_row)

    base_val = local_exp.base_value
    contrib_sum = sum(local_exp.contributions.values())
    pred = local_exp.prediction

    assert pred is not None
    # Additivity: base + sum(contributions) == prediction
    assert np.isclose(base_val + contrib_sum, pred, atol=1e-3), (
        f"Additivity check failed: base_val ({base_val}) + sum(contribs) ({contrib_sum}) = "
        f"{base_val + contrib_sum} != prediction ({pred})"
    )


def test_acceptance_check_e_leakage_check_zero_locked_test_overlap(db_session, regression_setup):
    """
    Check e) Leakage check: log which Development row indices were used as the background
    sample and confirm zero overlap with the Day 2 Locked Test indices.
    """
    project = regression_setup["project"]
    dataset = regression_setup["dataset"]
    locked_test_indices = set(regression_setup["test_indices"])
    dev_indices = set(regression_setup["dev_indices"])

    exp_service = ExperimentService(db_session)
    expl_service = ExplainabilityService(db_session)

    # Run and finalize
    exp_res = exp_service.run_experiment(
        project_id=project.id,
        algorithms=["RandomForestRegressor"],
        folds=3,
        seed=42,
        selection_metric="rmse",
        selection_direction="MINIMIZE",
        auto_finalize=True,
    )
    winning_model_id = exp_res["selected_model_id"]

    winning_model = db_session.query(TrainedModel).filter(TrainedModel.id == winning_model_id).first()
    artifact, _ = expl_service._load_artifact(winning_model_id)

    # Verify dataset split row indices in database have zero overlap
    dev_split = db_session.query(DatasetSplit).filter(DatasetSplit.dataset_id == dataset.id, DatasetSplit.split_type == "DEVELOPMENT").first()
    test_split = db_session.query(DatasetSplit).filter(DatasetSplit.dataset_id == dataset.id, DatasetSplit.split_type == "LOCKED_TEST").first()
    assert set(dev_split.row_indices).intersection(set(test_split.row_indices)) == set(), "Locked Test indices leaked into Development partition!"

    # Verify ExplainabilityService strictly draws from Development partition and NEVER touches Locked Test data
    with patch.object(DatasetSplitService, "get_locked_test_data") as mock_locked:
        summary = expl_service.global_shap_summary(winning_model_id, background_sample_size=50)
        assert summary.background_sample_size == 50
        mock_locked.assert_not_called()


def test_acceptance_check_f_tampered_artifact_rejection(db_session, regression_setup):
    """
    Check f) Deliberately corrupt one byte of a winning model's artifact file on disk
    and confirm `global_shap_summary`/`local_shap_explanation` refuse to run against it.
    """
    project = regression_setup["project"]
    exp_service = ExperimentService(db_session)
    expl_service = ExplainabilityService(db_session)

    # Run and finalize
    exp_res = exp_service.run_experiment(
        project_id=project.id,
        algorithms=["RandomForestRegressor"],
        folds=3,
        seed=42,
        selection_metric="rmse",
        selection_direction="MINIMIZE",
        auto_finalize=True,
    )
    winning_model_id = exp_res["selected_model_id"]

    winning_model = db_session.query(TrainedModel).filter(TrainedModel.id == winning_model_id).first()
    artifact_path = winning_model.artifact_path
    assert os.path.exists(artifact_path)

    # Deliberately corrupt 1 byte in the file
    with open(artifact_path, "r+b") as f:
        f.seek(15)
        current_byte = f.read(1)
        # Flip the byte
        corrupted_byte = bytes([(current_byte[0] ^ 0xFF)])
        f.seek(15)
        f.write(corrupted_byte)

    # Ensure global_shap_summary and local_shap_explanation fail with 422 SHA-256 mismatch
    with pytest.raises(HTTPException) as exc_global:
        expl_service.global_shap_summary(winning_model_id)
    assert exc_global.value.status_code == 422
    assert "Artifact integrity check failed: SHA-256 checksum mismatch" in exc_global.value.detail

    with pytest.raises(HTTPException) as exc_local:
        expl_service.local_shap_explanation(winning_model_id, {"sqft": 1500, "bedrooms": 3, "noise_feat": 0.5})
    assert exc_local.value.status_code == 422
    assert "Artifact integrity check failed: SHA-256 checksum mismatch" in exc_local.value.detail
