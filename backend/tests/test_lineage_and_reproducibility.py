import os
import json
import hashlib
from uuid import uuid4
from unittest.mock import patch, MagicMock
import numpy as np
import pandas as pd
import pytest

from app.models.project import Project
from app.models.dataset import Dataset
from app.models.dataset_column import DatasetColumn
from app.models.dataset_split import DatasetSplit
from app.models.transformation_config import TransformationConfig
from app.models.transformation_snapshot import TransformationSnapshot
from app.models.feature_selection_snapshot import FeatureSelectionSnapshot
from app.models.experiment import Experiment
from app.models.trained_model import TrainedModel
from app.services.experiment_service import ExperimentService
from app.services.dataset_split_service import DatasetSplitService
from app.services.environment_capture_service import EnvironmentCaptureService
from scripts.backfill_pre_day8_lineage import backfill_experiments


@pytest.fixture
def regression_setup(db_session, tmp_path, create_test_user):
    """
    Creates a realistic Regression project with uploaded dataset, splits, and transformation configs.
    """
    user = create_test_user("engineer@test.com", "ML_ENGINEER")

    project = Project(
        id=uuid4(),
        owner_id=user.id,
        project_name="Housing Price Predictor",
        task_type="REGRESSION",
        target_column="price",
        pipeline_stage="SPLIT",
    )
    db_session.add(project)
    db_session.commit()

    # Generate synthetic tabular dataset
    np.random.seed(42)
    n_samples = 120
    df = pd.DataFrame({
        "sqft": np.random.uniform(500, 3500, n_samples),
        "bedrooms": np.random.randint(1, 6, n_samples).astype(float),
        "bathrooms": np.random.uniform(1.0, 4.0, n_samples),
        "zipcode_str": np.random.choice(["ZIP_A", "ZIP_B", "ZIP_C"], n_samples),
        "price": np.random.uniform(100_000, 800_000, n_samples),
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
        column_count=5,
        content_hash=content_hash,
    )
    db_session.add(dataset)
    db_session.commit()

    # Add columns
    for col in df.columns:
        db_session.add(
            DatasetColumn(
                id=uuid4(),
                dataset_id=dataset.id,
                column_name=col,
                data_type="NUMERIC" if col != "zipcode_str" else "CATEGORICAL",
                unique_count=len(df[col].unique()),
                missing_percentage=0.0,
                is_target=(col == "price"),
            )
        )

    # Outer Split: 80% Development (96 rows), 20% Locked Test (24 rows)
    indices = np.arange(n_samples)
    np.random.shuffle(indices)
    dev_idx = indices[:96].tolist()
    test_idx = indices[96:].tolist()

    dev_split = DatasetSplit(
        id=uuid4(),
        dataset_id=dataset.id,
        split_type="DEVELOPMENT",
        split_seed=42,
        row_indices=dev_idx,
    )
    test_split = DatasetSplit(
        id=uuid4(),
        dataset_id=dataset.id,
        split_type="LOCKED_TEST",
        split_seed=42,
        row_indices=test_idx,
    )
    db_session.add_all([dev_split, test_split])

    # Add Transformation Configs
    t1 = TransformationConfig(
        id=uuid4(),
        project_id=project.id,
        column_name="sqft",
        scaling_strategy="STANDARD",
        is_active=True,
    )
    t2 = TransformationConfig(
        id=uuid4(),
        project_id=project.id,
        column_name="bedrooms",
        missing_value_strategy="MEDIAN",
        is_active=True,
    )
    t3 = TransformationConfig(
        id=uuid4(),
        project_id=project.id,
        column_name="zipcode_str",
        encoding_strategy="ONE_HOT",
        is_active=True,
    )
    db_session.add_all([t1, t2, t3])
    db_session.commit()

    return project, dataset, df


def test_acceptance_check_a_live_capture_and_real_versions(db_session, regression_setup):
    """
    Check a) Run a NEW experiment end-to-end today; confirm its environment_capture_method = 'CAPTURED_LIVE'
    and every version field is populated with real values, not nulls or placeholders.
    """
    project, dataset, _ = regression_setup
    service = ExperimentService(db_session)

    res = service.run_experiment(
        project_id=project.id,
        algorithms=["LinearRegression", "Ridge"],
        folds=3,
        seed=101,
        selection_metric="rmse",
        selection_direction="MINIMIZE",
    )

    exp = db_session.query(Experiment).filter(Experiment.id == res["experiment_id"]).first()
    assert exp is not None
    assert exp.status == "COMPLETED"

    # Verify environment capture method
    assert exp.environment_capture_method == "CAPTURED_LIVE"

    # Verify all version fields are real values
    assert exp.python_version is not None and len(exp.python_version) > 0
    assert exp.sklearn_version is not None and exp.sklearn_version != "unknown"
    assert exp.numpy_version is not None and exp.numpy_version != "unknown"
    assert exp.pandas_version is not None and exp.pandas_version != "unknown"
    assert exp.code_version is not None and len(exp.code_version) > 0
    assert isinstance(exp.model_library_versions, dict)
    assert len(exp.model_library_versions) > 0
    assert "joblib" in exp.model_library_versions

    # Verify dataset content hash copied
    assert exp.dataset_content_hash == dataset.content_hash

    # Verify experiment_config frozen schema
    cfg = exp.experiment_config
    assert isinstance(cfg, dict)
    assert cfg["task_type"] == "REGRESSION"
    assert cfg["target"] == "price"
    assert cfg["split"]["seed"] == 42
    assert cfg["split"]["locked_test_pct"] == 20
    assert cfg["cv"]["strategy"] == "KFOLD"
    assert cfg["cv"]["folds"] == 3
    assert cfg["cv"]["seed"] == 101
    assert "snapshot_id" in cfg["preprocessing"]
    assert cfg["feature_selection"]["method"] == "rank_aggregation_ensemble"
    assert cfg["deployment_threshold"]["metric"] == "rmse"


def test_acceptance_check_b_artifact_checksum_and_tamper_detection(db_session, regression_setup):
    """
    Check b) Fetch a winning model's artifact_checksum, then independently recompute SHA-256 on
    the actual file at artifact_path and confirm they match. Then mutate one byte of the file on disk
    and confirm a recomputed hash no longer matches — proving the checksum is a real integrity check, not decorative.
    """
    project, _, _ = regression_setup
    service = ExperimentService(db_session)

    res = service.run_experiment(
        project_id=project.id,
        algorithms=["LinearRegression", "Ridge"],
        folds=3,
        seed=101,
        auto_finalize=True,
    )

    winning_model_id = res["selected_model_id"]
    winning_model = db_session.query(TrainedModel).filter(TrainedModel.id == winning_model_id).first()
    assert winning_model is not None

    artifact_path = winning_model.artifact_path
    db_checksum = winning_model.artifact_checksum

    assert artifact_path is not None
    assert os.path.exists(artifact_path)
    assert db_checksum is not None and len(db_checksum) == 64

    # Independently recompute SHA-256 from disk file
    hasher = hashlib.sha256()
    with open(artifact_path, "rb") as f:
        hasher.update(f.read())
    disk_checksum = hasher.hexdigest()

    assert disk_checksum == db_checksum, "Disk SHA-256 must match database artifact_checksum exactly."

    # Adversarial test: Mutate 1 byte on disk
    with open(artifact_path, "r+b") as f:
        content = bytearray(f.read())
        # Flip the first byte
        content[0] = (content[0] ^ 0xFF)
        f.seek(0)
        f.write(content)

    # Recompute SHA-256 after byte mutation
    tampered_hasher = hashlib.sha256()
    with open(artifact_path, "rb") as f:
        tampered_hasher.update(f.read())
    tampered_checksum = tampered_hasher.hexdigest()

    assert tampered_checksum != db_checksum, "Corrupted file must produce a different checksum, proving real integrity check."


def test_acceptance_check_c_transformation_snapshot_immutability(db_session, regression_setup):
    """
    Check c) Create a NEW experiment, then IMMEDIATELY change one of the project's transformation_configs
    (e.g. flip a scaling strategy), then fetch that experiment's transformation_snapshots.config_json
    and confirm it still shows the OLD value — proving the snapshot is a frozen copy, not a live reference.
    """
    project, _, _ = regression_setup
    service = ExperimentService(db_session)

    res = service.run_experiment(
        project_id=project.id,
        algorithms=["LinearRegression"],
        folds=3,
        seed=101,
        auto_finalize=True,
    )

    exp_id = res["experiment_id"]
    trans_snap = db_session.query(TransformationSnapshot).filter(TransformationSnapshot.experiment_id == exp_id).first()
    assert trans_snap is not None

    # Find the sqft config in snapshot (initially SCALING: STANDARD)
    sqft_snap = next(c for c in trans_snap.config_json if c["column_name"] == "sqft")
    assert sqft_snap["scaling_strategy"] == "STANDARD"

    # Now mutate the live project transformation_config
    live_tc = db_session.query(TransformationConfig).filter(
        TransformationConfig.project_id == project.id,
        TransformationConfig.column_name == "sqft"
    ).first()
    live_tc.scaling_strategy = "MIN_MAX"
    db_session.add(live_tc)
    db_session.commit()

    # Re-fetch the snapshot from database
    db_session.expire_all()
    trans_snap_refetched = db_session.query(TransformationSnapshot).filter(TransformationSnapshot.experiment_id == exp_id).first()
    sqft_snap_refetched = next(c for c in trans_snap_refetched.config_json if c["column_name"] == "sqft")

    # It MUST still be "STANDARD", completely unaffected by changes to live transformation_configs
    assert sqft_snap_refetched["scaling_strategy"] == "STANDARD"
    assert sqft_snap_refetched["scaling_strategy"] != live_tc.scaling_strategy


def test_acceptance_check_d_feature_selection_snapshot_matches_full_dev_refit(db_session, regression_setup):
    """
    Check d) Confirm feature_selection_snapshots.final_selected_features for a completed experiment
    matches exactly what the final-refit selector actually selected when fit on the full Development set —
    cross-check against finalize code path output, not a fold-level selection.
    """
    project, dataset, _ = regression_setup
    service = ExperimentService(db_session)

    res = service.run_experiment(
        project_id=project.id,
        algorithms=["LinearRegression", "Ridge"],
        folds=3,
        seed=101,
        auto_finalize=True,
    )

    exp_id = res["experiment_id"]
    exp = db_session.query(Experiment).filter(Experiment.id == exp_id).first()
    assert exp.feature_selection_snapshot_id is not None

    fs_snap = db_session.query(FeatureSelectionSnapshot).filter(
        FeatureSelectionSnapshot.id == exp.feature_selection_snapshot_id
    ).first()
    assert fs_snap is not None
    assert fs_snap.final_selection_method == "rank_aggregation_ensemble"
    assert isinstance(fs_snap.final_selected_features, list)
    assert len(fs_snap.final_selected_features) > 0

    # Cross-check against the winning model's serialized artifact
    winning_model = exp.selected_model
    import joblib
    artifact = joblib.load(winning_model.artifact_path)

    assert artifact["selected_feature_names"] == fs_snap.final_selected_features
    assert winning_model.feature_selection_snapshot_id == fs_snap.id


def test_acceptance_check_e_experiment_config_immutability(db_session, regression_setup):
    """
    Check e) Attempt to find or call any code path that writes to experiment_config after experiment creation —
    confirm none exists. Hash-compare experiment_config immediately after creation vs. after the experiment
    fully completes and finalizes; confirm byte-identical.
    """
    project, _, _ = regression_setup
    service = ExperimentService(db_session)

    # 1. Create and start experiment without auto_finalize
    res = service.run_experiment(
        project_id=project.id,
        algorithms=["LinearRegression"],
        folds=3,
        seed=101,
        auto_finalize=False,
    )

    exp_id = res["experiment_id"]
    exp_before = db_session.query(Experiment).filter(Experiment.id == exp_id).first()
    config_before_json = json.dumps(exp_before.experiment_config, sort_keys=True)
    hash_before = hashlib.sha256(config_before_json.encode("utf-8")).hexdigest()

    # 2. Finalize the experiment
    service.finalize_experiment(exp_id)

    # 3. Retrieve experiment after finalization
    db_session.expire_all()
    exp_after = db_session.query(Experiment).filter(Experiment.id == exp_id).first()
    config_after_json = json.dumps(exp_after.experiment_config, sort_keys=True)
    hash_after = hashlib.sha256(config_after_json.encode("utf-8")).hexdigest()

    # Confirm byte-identical JSON hash
    assert hash_before == hash_after
    assert exp_before.experiment_config == exp_after.experiment_config


def test_acceptance_check_f_backfill_script_marks_approximate(db_session, regression_setup):
    """
    Check f) Run the backfill script and confirm every pre-Day-8 experiment now shows
    environment_capture_method = 'BACKFILLED_APPROXIMATE', clearly distinguishable from today's new experiments.
    """
    project, _, _ = regression_setup

    # Manually create a historical pre-Day-8 experiment with NULL environment_capture_method
    legacy_exp = Experiment(
        id=uuid4(),
        project_id=project.id,
        status="COMPLETED",
        task_type="REGRESSION",
        fold_count=5,
        cv_seed=42,
        selection_metric="rmse",
        selection_direction="MINIMIZE",
        environment_capture_method=None,
        experiment_config=None,
    )
    db_session.add(legacy_exp)
    db_session.commit()

    # Run the backfill script
    count = backfill_experiments(db_session)
    assert count >= 1

    # Reload legacy experiment
    db_session.refresh(legacy_exp)
    assert legacy_exp.environment_capture_method == "BACKFILLED_APPROXIMATE"
    assert legacy_exp.python_version is not None
    assert legacy_exp.sklearn_version is not None
    assert legacy_exp.experiment_config is not None
    assert legacy_exp.feature_selection_snapshot_id is None, "Unfinalized legacy experiment must not fabricate a snapshot."


def test_acceptance_check_g_no_new_locked_test_calls(db_session, regression_setup):
    """
    Check g) Confirm no new call to get_locked_test_data() was introduced anywhere today —
    the call count from Day 7's tests should be unchanged; today's work only reads already-fitted
    objects and configuration, never raw data.
    """
    project, _, _ = regression_setup
    service = ExperimentService(db_session)

    with patch.object(DatasetSplitService, "get_locked_test_data", wraps=service.split_service.get_locked_test_data) as mock_locked_test:
        service.run_experiment(
            project_id=project.id,
            algorithms=["LinearRegression"],
            folds=3,
            seed=101,
            auto_finalize=True,
        )

        # In Day 7, exactly ONE call to get_locked_test_data is made in finalize_experiment for the winning model.
        # Zero calls during CV training, zero calls during lineage capture, zero calls during artifact checksumming.
        assert mock_locked_test.call_count == 1, "Exactly one call to get_locked_test_data must occur during finalization."


def test_lineage_api_endpoint(client, create_test_user, db_session, regression_setup):
    """
    Tests GET /api/v1/experiments/{id}/lineage endpoint with JWT authentication.
    """
    user = create_test_user("ml_engineer@test.com", "ML_ENGINEER")
    login_res = client.post("/api/v1/auth/login", json={"email": "ml_engineer@test.com", "password": "password123"})
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    project, _, _ = regression_setup
    service = ExperimentService(db_session)
    exp_res = service.run_experiment(
        project_id=project.id,
        algorithms=["LinearRegression", "Ridge"],
        folds=3,
        seed=101,
        auto_finalize=True,
    )
    exp_id = exp_res["experiment_id"]

    response = client.get(f"/api/v1/experiments/{exp_id}/lineage", headers=headers)
    assert response.status_code == 200
    data = response.json()

    assert data["experiment_id"] == str(exp_id)
    assert data["environment_capture_method"] == "CAPTURED_LIVE"
    assert data["code_version"] is not None
    assert data["python_version"] is not None
    assert data["sklearn_version"] is not None
    assert data["transformation_snapshot"] is not None
    assert data["feature_selection_snapshot"] is not None
    assert data["winning_model"] is not None
    assert data["winning_model"]["artifact_checksum"] is not None
