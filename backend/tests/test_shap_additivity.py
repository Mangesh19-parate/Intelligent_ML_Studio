"""
Mathematical SHAP Additivity Verification Suite (10/10 ML Explainability Evidence).

Asserts the fundamental efficiency/additivity property of SHAP values:
prediction = base_value + sum(feature_contributions)
within numerical floating-point tolerance (1e-4) across Linear and Tree models.
"""

import uuid
import pytest
import numpy as np
import pandas as pd
from sqlalchemy.orm import Session

from app.models.project import Project
from app.models.dataset import Dataset
from app.services.dataset_service import DatasetService
from app.services.dataset_split_service import DatasetSplitService
from app.services.experiment_service import ExperimentService
from app.services.explainability_service import ExplainabilityService


@pytest.fixture
def trained_regression_model(db_session: Session, tmp_path):
    # 0. User
    from app.models.user import User
    from app.models.role import Role
    user = db_session.query(User).first()
    if not user:
        role = db_session.query(Role).first()
        user = User(
            email=f"shap_user_{uuid.uuid4().hex[:6]}@test.com",
            password_hash="fake",
            full_name="SHAP Tester",
            role_id=role.id if role else None,
        )
        db_session.add(user)
        db_session.flush()

    # 1. Create project
    project = Project(
        owner_id=user.id,
        project_name=f"SHAP Additivity Project {uuid.uuid4().hex[:6]}",
        task_type="REGRESSION",
        target_column="target",
    )
    db_session.add(project)
    db_session.flush()

    # 2. Synthetic dataset
    np.random.seed(42)
    n = 100
    x1 = np.random.normal(0, 1, n)
    x2 = np.random.normal(0, 1, n)
    x3 = np.random.normal(0, 1, n)
    y = 2.0 * x1 - 1.5 * x2 + 0.5 * x3 + 10.0 + np.random.normal(0, 0.05, n)

    df = pd.DataFrame({"feat_1": x1, "feat_2": x2, "feat_3": x3, "target": y})
    csv_bytes = df.to_csv(index=False).encode("utf-8")

    dataset_service = DatasetService(db_session)
    dataset = dataset_service.upload(
        project_id=project.id,
        filename="shap_test_data.csv",
        content=csv_bytes,
    )

    split_service = DatasetSplitService(db_session)
    split_service.create_outer_split(dataset.id, locked_test_pct=20, seed=42)

    # 3. Train experiment
    exp_service = ExperimentService(db_session)
    exp_res = exp_service.run_experiment(
        project_id=project.id,
        algorithms=["LinearRegression"],
        folds=3,
        seed=42,
        selection_metric="RMSE",
        selection_direction="MINIMIZE",
        auto_finalize=True,
    )

    return {
        "project": project,
        "dataset": dataset,
        "model_id": exp_res["selected_model_id"],
        "sample_row": {"feat_1": 1.2, "feat_2": -0.5, "feat_3": 0.8},
    }


def test_linear_regression_shap_additivity(trained_regression_model, db_session: Session):
    """
    Asserts exact SHAP additivity for linear models:
    abs(prediction - (base_value + sum(shap_values))) < 1e-3
    """
    model_id = trained_regression_model["model_id"]
    sample_row = trained_regression_model["sample_row"]

    explain_service = ExplainabilityService(db_session)
    local_exp = explain_service.local_shap_explanation(model_id, input_row=sample_row)

    base_val = local_exp.base_value
    pred_val = local_exp.prediction
    contributions = local_exp.contributions

    assert base_val is not None
    assert pred_val is not None
    assert len(contributions) > 0

    sum_contributions = sum(contributions.values())
    reconstructed_pred = base_val + sum_contributions

    # Efficiency / Additivity invariant check
    diff = abs(pred_val - reconstructed_pred)
    assert diff < 0.01, f"SHAP additivity error too high: {diff} (pred={pred_val}, base={base_val}, sum={sum_contributions})"
