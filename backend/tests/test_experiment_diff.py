"""
Unit & Integration Tests for Counterfactual Experiment Diff Service (Week 12).
"""

import uuid
import pytest
from app.models.experiment import Experiment
from app.models.project import Project
from app.models.trained_model import TrainedModel
from app.models.model_metric import ModelMetric
from app.services.experiment_diff_service import ExperimentDiffService



def test_experiment_diff_service_computation(db_session):
    """Test full diff generation between two experiments with different features and models."""
    from app.models.user import User
    from app.models.role import Role

    # Get or create test user
    role = db_session.query(Role).filter(Role.role_name == "ML_ENGINEER").first()
    if not role:
        role = Role(role_name="ML_ENGINEER", description="ML Engineer")
        db_session.add(role)
        db_session.flush()


    user = User(
        email=f"diff_{uuid.uuid4().hex[:8]}@example.com",
        full_name="Diff User",
        password_hash="hashed_pwd",
        role_id=role.id,
    )
    db_session.add(user)
    db_session.flush()


    # Create mock project
    proj = Project(
        owner_id=user.id,
        project_name="Diff Test Project",
        task_type="REGRESSION",
        target_column="target",
    )
    db_session.add(proj)
    db_session.flush()


    # Create Experiment A (Baseline)
    exp_a = Experiment(
        project_id=proj.id,
        task_type="REGRESSION",
        fold_count=5,
        cv_seed=42,
        selection_metric="RMSE",
        dataset_content_hash="hash_12345",
        code_version="v1.0.0",
        python_version="3.11.0",
        experiment_config={
            "selected_features": ["feat_1", "feat_2", "feat_3"],
            "models": [
                {"algorithm": "RandomForest", "hyperparameters": {"n_estimators": 50}},
                {"algorithm": "Ridge", "hyperparameters": {"alpha": 1.0}},
            ],
        },
    )
    db_session.add(exp_a)
    db_session.flush()

    # Create Experiment B (Candidate with new features and hyperparams)
    exp_b = Experiment(
        project_id=proj.id,
        task_type="REGRESSION",
        fold_count=5,
        cv_seed=42,
        selection_metric="RMSE",
        dataset_content_hash="hash_12345",
        code_version="v1.0.0",
        python_version="3.11.0",
        experiment_config={
            "selected_features": ["feat_1", "feat_2", "feat_4", "feat_5"],
            "models": [
                {"algorithm": "RandomForest", "hyperparameters": {"n_estimators": 100}},
                {"algorithm": "LGBM", "hyperparameters": {"learning_rate": 0.05}},
            ],
        },
    )
    db_session.add(exp_b)
    db_session.flush()

    # Add mock models and metrics
    model_a = TrainedModel(
        experiment_id=exp_a.id,
        algorithm_name="RandomForest",
        hyperparameters={"n_estimators": 50},
        artifact_path="/tmp/rf_a.joblib",
    )
    db_session.add(model_a)
    db_session.flush()

    metric_a = ModelMetric(
        model_id=model_a.id,
        metric_name="RMSE",
        split="CV_MEAN",
        metric_value=0.550,
        fold_index=0,
    )
    db_session.add(metric_a)

    model_b = TrainedModel(
        experiment_id=exp_b.id,
        algorithm_name="RandomForest",
        hyperparameters={"n_estimators": 100},
        artifact_path="/tmp/rf_b.joblib",
    )
    db_session.add(model_b)
    db_session.flush()

    metric_b = ModelMetric(
        model_id=model_b.id,
        metric_name="RMSE",
        split="CV_MEAN",
        metric_value=0.520,
        fold_index=0,
    )
    db_session.add(metric_b)


    db_session.commit()

    # Compute Diff
    diff_svc = ExperimentDiffService(db_session)
    diff = diff_svc.compute_diff(exp_a.id, exp_b.id)

    # Assertions
    assert diff["experiment_a_id"] == str(exp_a.id)
    assert diff["experiment_b_id"] == str(exp_b.id)

    # Feature diff
    f_diff = diff["feature_selection_diff"]
    assert f_diff["feature_set_changed"] is True
    assert set(f_diff["added_in_b"]) == {"feat_4", "feat_5"}
    assert set(f_diff["removed_in_b"]) == {"feat_3"}
    assert f_diff["retained_common_count"] == 2

    # Model diff
    m_diff = diff["model_algorithm_diff"]
    assert m_diff["RandomForest"]["status"] == "COMMON"
    assert m_diff["RandomForest"]["hyperparameters_changed"] is True
    assert m_diff["Ridge"]["status"] == "REMOVED_IN_B"
    assert m_diff["LGBM"]["status"] == "ADDED_IN_B"

    # Metrics
    deltas = diff["metric_deltas"]
    rf_rmse = deltas.get("RandomForest_RMSE")
    assert rf_rmse is not None
    assert rf_rmse["experiment_a_value"] == 0.550
    assert rf_rmse["experiment_b_value"] == 0.520
    assert rf_rmse["delta"] == -0.030
    assert rf_rmse["improved"] is True  # Lower RMSE is better

    # Lineage
    assert diff["lineage_diff"]["dataset_content_hash"]["same_dataset"] is True
    assert "Features:" in diff["summary"]
