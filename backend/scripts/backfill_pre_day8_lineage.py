"""
Lineage Backfill Script for Pre-Day-8 Experiments (Day 8).

HONESTY & INTEGRITY REQUIREMENT (SRS §2.17 / Day 8):
Days 6–7 ran real experiments without capturing library versions, code_version,
or a transformation snapshot live. We cannot retroactively know what was actually
running at that time with certainty.
Therefore, this script backfills those experiments with current environment values
and sets environment_capture_method = 'BACKFILLED_APPROXIMATE', ensuring that
we never overclaim authentic live capture for historical experiments.

Transformation snapshots created here copy current transformation_configs:
NOTE: This may not reflect what was actually configured at the time those
experiments ran, since transformation_configs are mutable and could have changed since.

For feature_selection_snapshots:
If an experiment never went through finalize_experiment, feature_selection_snapshot_id
remains NULL (never fabricated). If an experiment did finalize, we only attach
a snapshot if final selection details can be genuinely determined.
"""

import sys
from pathlib import Path

# Add backend directory to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

import logging
from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.models.experiment import Experiment
from app.models.project import Project
from app.models.dataset import Dataset
from app.models.dataset_split import DatasetSplit
from app.models.transformation_config import TransformationConfig
from app.models.transformation_snapshot import TransformationSnapshot
from app.models.feature_selection_snapshot import FeatureSelectionSnapshot
from app.models.trained_model import TrainedModel
from app.services.environment_capture_service import EnvironmentCaptureService

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("backfill_lineage")

def backfill_experiments(db: Session) -> int:
    """
    Backfills all historical experiments missing environment_capture_method.
    """
    experiments = (
        db.query(Experiment)
        .filter(Experiment.environment_capture_method.is_(None))
        .all()
    )

    if not experiments:
        logger.info("No unbackfilled pre-Day-8 experiments found.")
        return 0

    logger.info(f"Found {len(experiments)} pre-Day-8 experiments to backfill.")
    env_info = EnvironmentCaptureService.capture_current_environment()

    count = 0
    for exp in experiments:
        logger.info(f"Backfilling lineage for Experiment {exp.id} (Project {exp.project_id})...")
        
        project = db.query(Project).filter(Project.id == exp.project_id).first()
        datasets = db.query(Dataset).filter(Dataset.project_id == exp.project_id).order_by(Dataset.version_number.desc()).all()
        dataset = datasets[0] if datasets else None

        # 1. Dataset Content Hash
        if not exp.dataset_content_hash and dataset:
            exp.dataset_content_hash = dataset.content_hash

        # 2. Approximate environment capture
        exp.environment_capture_method = "BACKFILLED_APPROXIMATE"
        exp.code_version = env_info.get("code_version")
        exp.python_version = env_info.get("python_version")
        exp.sklearn_version = env_info.get("sklearn_version")
        exp.numpy_version = env_info.get("numpy_version")
        exp.pandas_version = env_info.get("pandas_version")
        exp.model_library_versions = env_info.get("model_library_versions")

        # 3. Transformation Snapshot from current transformation_configs
        # CAVEAT: This may not reflect what was configured at the time the historical experiment ran.
        existing_ts = (
            db.query(TransformationSnapshot)
            .filter(TransformationSnapshot.experiment_id == exp.id)
            .first()
        )
        if not existing_ts and project:
            trans_configs = (
                db.query(TransformationConfig)
                .filter(TransformationConfig.project_id == project.id)
                .order_by(TransformationConfig.column_name.asc())
                .all()
            )
            frozen_trans_json = [
                {
                    "id": str(tc.id),
                    "column_name": tc.column_name,
                    "missing_value_strategy": tc.missing_value_strategy,
                    "encoding_strategy": tc.encoding_strategy,
                    "scaling_strategy": tc.scaling_strategy,
                    "outlier_strategy": tc.outlier_strategy,
                    "is_active": tc.is_active,
                }
                for tc in trans_configs
            ]
            new_ts = TransformationSnapshot(
                experiment_id=exp.id,
                config_json=frozen_trans_json,
            )
            db.add(new_ts)
            db.flush()
            trans_snapshot_id = str(new_ts.id)
        else:
            trans_snapshot_id = str(existing_ts.id) if existing_ts else None

        # 4. Construct approximate experiment_config if absent
        if not exp.experiment_config and project:
            dev_split = None
            if dataset:
                dev_split = db.query(DatasetSplit).filter(
                    DatasetSplit.dataset_id == dataset.id,
                    DatasetSplit.split_type == "DEVELOPMENT"
                ).first()
            split_seed = dev_split.split_seed if dev_split else 42
            cv_strat = "STRATIFIED_KFOLD" if (exp.task_type or project.task_type) == "CLASSIFICATION" else "KFOLD"

            exp.experiment_config = {
                "task_type": exp.task_type or project.task_type or "REGRESSION",
                "target": project.target_column,
                "split": {
                    "seed": split_seed,
                    "locked_test_pct": 20,
                },
                "cv": {
                    "strategy": cv_strat,
                    "folds": exp.fold_count or 5,
                    "seed": exp.cv_seed or 42,
                },
                "preprocessing": {
                    "snapshot_id": trans_snapshot_id,
                },
                "feature_selection": {
                    "method": "rank_aggregation_ensemble",
                },
                "threshold_selection": {
                    "objective": "F1",
                    "search_range": [0.10, 0.90],
                    "resolution": 0.01,
                    "tie_break": "closest_to_0.5",
                },
                "deployment_threshold": {
                    "metric": exp.selection_metric or ("rmse" if (exp.task_type or project.task_type) == "REGRESSION" else "f1_macro"),
                    "min_value": None,
                },
            }

        # 5. Feature selection snapshots:
        # If experiment never finalized (no selected_model_id or not locked_test_consumed), leave feature_selection_snapshot_id NULL!
        if not exp.selected_model_id or not exp.locked_test_consumed:
            exp.feature_selection_snapshot_id = None
        
        db.add(exp)
        count += 1

    db.commit()
    logger.info(f"Successfully backfilled {count} experiments with BACKFILLED_APPROXIMATE.")
    return count

if __name__ == "__main__":
    db = SessionLocal()
    try:
        backfill_experiments(db)
    finally:
        db.close()
