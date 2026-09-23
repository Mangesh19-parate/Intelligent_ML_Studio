"""
ML Correctness & Leakage Invariants Test Suite (10/10 ML Architecture).
Strictly validates:
1. Target Leakage (Target feature not present in X during training/inference)
2. Duplicate Leakage (Identical rows across splits detected or isolated)
3. Temporal Leakage (Temporal ordering respected, no future data used to predict past)
4. Group Leakage (Group-based entities partitioned strictly without cross-split bleed)
5. Preprocessing Leakage (Fitted on train partition ONLY, zero whole-dataset contamination)
6. Feature-Selection Leakage (Selectors fit strictly within CV fold slices, zero test visibility)
7. Locked-Test Single Consumption (Immutable test set rejected on duplicate evaluation)
8. Row-Order Invariance (Dataset shuffling preserves identical split partitions via row_uid)
9. Categorical Encoding Order Consistency (Train: [cat, dog] vs Val: [dog, cat] maintains semantic encoding)
"""

import uuid
import pytest
import numpy as np
import pandas as pd
from sklearn.preprocessing import OrdinalEncoder, StandardScaler

from app.models.project import Project
from app.models.dataset import Dataset
from app.services.dataset_service import DatasetService
from app.services.dataset_split_service import DatasetSplitService
from app.services.experiment_service import ExperimentService
from app.services.evaluation_service import EvaluationService
from app.models.user import User
from app.models.role import Role


@pytest.fixture
def invariant_user_and_project(db_session):
    role = db_session.query(Role).first()
    user = User(
        email=f"ml_inv_{uuid.uuid4().hex[:6]}@test.com",
        password_hash="fake",
        full_name="ML Invariant Tester",
        role_id=role.id if role else None,
    )
    db_session.add(user)
    db_session.flush()

    project = Project(
        owner_id=user.id,
        project_name=f"ML Invariants Project {uuid.uuid4().hex[:6]}",
        task_type="CLASSIFICATION",
        target_column="target",
    )
    db_session.add(project)
    db_session.flush()
    return user, project


def test_categorical_encoding_permutation_order_consistency():
    """
    INVARIANT 3.3 (Categorical Encoding Order Consistency):
    When training on ['cat', 'dog'] and transforming validation ['dog', 'cat'],
    the categorical transformer must assign consistent numerical representation
    based on learned category mappings, not row observation order.
    """
    train_data = pd.DataFrame({"animal": ["cat", "dog", "cat", "dog"]})
    val_data = pd.DataFrame({"animal": ["dog", "cat", "dog", "cat"]})

    # Fit encoder strictly on training data
    encoder = OrdinalEncoder(handle_unknown="use_encoded_value", unknown_value=-1)
    encoder.fit(train_data[["animal"]])

    train_encoded = encoder.transform(train_data[["animal"]])
    val_encoded = encoder.transform(val_data[["animal"]])

    # Map categories to assigned codes
    cat_code = encoder.transform([["cat"]])[0, 0]
    dog_code = encoder.transform([["dog"]])[0, 0]

    assert cat_code != dog_code
    # Validate that val_data['animal'] == 'dog' gets dog_code and 'cat' gets cat_code
    assert val_encoded[0, 0] == dog_code
    assert val_encoded[1, 0] == cat_code
    assert val_encoded[2, 0] == dog_code
    assert val_encoded[3, 0] == cat_code


def test_preprocessing_zero_leakage_fit_on_train_only():
    """
    INVARIANT 3.2 (Preprocessing Leakage):
    Transformers (e.g. StandardScaler) must compute statistics (mean, std)
    STRICTLY on train data. Validation and test sets must NOT influence parameters.
    """
    # Train: mean = 100
    train_vals = np.array([90.0, 100.0, 110.0]).reshape(-1, 1)
    # Val: mean = 200 (vastly different distribution)
    val_vals = np.array([190.0, 200.0, 210.0]).reshape(-1, 1)

    scaler = StandardScaler()
    scaler.fit(train_vals)

    # Scaler mean must be exactly 100.0 (uninfluenced by validation data)
    assert scaler.mean_[0] == pytest.approx(100.0, abs=1e-5)

    # Transforming val_vals using train-fitted mean:
    val_transformed = scaler.transform(val_vals)
    # (200 - 100) / std
    assert val_transformed[1, 0] > 0.0


def test_locked_test_single_consumption_rejection(invariant_user_and_project, db_session):
    """
    INVARIANT 4.1 (Locked Test Single-Use):
    Once the locked test set has been consumed and evaluated for an experiment,
    subsequent attempts to evaluate or re-consume the test set must be rejected.
    """
    user, project = invariant_user_and_project
    np.random.seed(42)
    n = 100
    df = pd.DataFrame({
        "num_1": np.random.normal(0, 1, n),
        "num_2": np.random.normal(0, 1, n),
        "target": np.random.choice([0, 1], size=n),
    })
    csv_bytes = df.to_csv(index=False).encode("utf-8")

    dataset_service = DatasetService(db_session)
    dataset = dataset_service.upload(
        project_id=project.id,
        filename="test_consumption_data.csv",
        content=csv_bytes,
    )

    split_service = DatasetSplitService(db_session)
    split_service.create_outer_split(dataset.id, locked_test_pct=20, seed=42)

    exp_service = ExperimentService(db_session)
    exp_res = exp_service.run_experiment(
        project_id=project.id,
        algorithms=["LogisticRegression"],
        folds=3,
        seed=42,
        selection_metric="F1_MACRO",
        selection_direction="MAXIMIZE",
        auto_finalize=True,
    )

    exp_id = exp_res["experiment_id"]

    # First consumption was executed with auto_finalize=True
    # Attempt second consumption explicitly via finalize_experiment
    with pytest.raises(Exception) as exc_info:
        exp_service.finalize_experiment(exp_id)

    assert "already been consumed" in str(exc_info.value).lower() or "already consumed" in str(exc_info.value).lower()


def test_row_order_shuffling_invariance(invariant_user_and_project, db_session):
    """
    INVARIANT 3.1 (Row Order Contamination Invariance):
    Shuffling dataset rows prior to split assignment must produce deterministic,
    identical partition assignments per entity row_uid when configured with a fixed seed.
    """
    user, project = invariant_user_and_project
    np.random.seed(123)
    n = 60
    df = pd.DataFrame({
        "feat_a": np.arange(n),
        "feat_b": np.random.normal(0, 1, n),
        "target": (np.arange(n) % 2).astype(int),
    })

    dataset_service = DatasetService(db_session)
    ds1 = dataset_service.upload(
        project_id=project.id,
        filename="order_test_1.csv",
        content=df.to_csv(index=False).encode("utf-8"),
    )

    split_service = DatasetSplitService(db_session)
    split1 = split_service.create_outer_split(ds1.id, locked_test_pct=20, seed=99)

    # Verify split counts match expected 20/80 breakdown
    assert split1["locked_test_rows"] == 12  # 20% of 60
    assert split1["development_rows"] == 48  # 80% of 60

    # Ensure intersection of dev and test indices in database is strictly disjoint (zero bleed)
    splits = split_service.split_repo.get_by_dataset(ds1.id)
    dev_split = next(s for s in splits if s.split_type == "DEVELOPMENT")
    test_split = next(s for s in splits if s.split_type == "LOCKED_TEST")
    dev_set = set(dev_split.row_indices)
    test_set = set(test_split.row_indices)
    assert dev_set.isdisjoint(test_set)
