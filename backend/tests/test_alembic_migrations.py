"""
Test Alembic Database Migration Path (P1.6).
Verifies that the full migration chain (upgrade head -> downgrade base -> upgrade head)
executes deterministically against a clean database without errors or orphaned constraints.
"""

import os
from pathlib import Path
import pytest
from sqlalchemy import create_engine, inspect
from alembic.config import Config
from alembic import command

BASE_DIR = Path(__file__).resolve().parent.parent
ALEMBIC_INI_PATH = BASE_DIR / "alembic.ini"


def test_alembic_upgrade_downgrade_cycle(tmp_path):
    """
    P1.6 INVARIANT: Full Alembic migration lifecycle from revision 001 to head
    and back to base works cleanly on a fresh database.
    """
    db_file = tmp_path / "test_migration.db"
    db_url = f"sqlite:///{db_file.as_posix()}"

    alembic_cfg = Config(str(ALEMBIC_INI_PATH))
    alembic_cfg.set_main_option("sqlalchemy.url", db_url)
    alembic_cfg.set_main_option("script_location", str(BASE_DIR / "alembic"))

    # 1. Run upgrade to head
    command.upgrade(alembic_cfg, "head")

    engine = create_engine(db_url)
    inspector = inspect(engine)
    tables = inspector.get_table_names()

    # Verify expected tables are present
    assert "users" in tables
    assert "roles" in tables
    assert "projects" in tables
    assert "datasets" in tables
    assert "experiments" in tables
    assert "durable_tasks" in tables
    assert "revoked_tokens" in tables
    assert "reproducibility_runs" in tables
    assert "feature_selection_fold_results" in tables
    assert "model_metrics" in tables

    # Verify user auth and 2FA columns
    user_cols = [c["name"] for c in inspector.get_columns("users")]
    assert "password_changed_at" in user_cols
    assert "is_two_factor_enabled" in user_cols
    assert "two_factor_secret" in user_cols
    assert "two_factor_backup_codes" in user_cols

    # Verify provenance columns in feature_selection_fold_results
    fs_cols = [c["name"] for c in inspector.get_columns("feature_selection_fold_results")]
    assert "train_row_hash" in fs_cols
    assert "validation_row_hash" in fs_cols
    assert "locked_test_accessed" in fs_cols

    engine.dispose()

    # 2. Run downgrade to base
    command.downgrade(alembic_cfg, "base")

    engine = create_engine(db_url)
    inspector = inspect(engine)
    tables_after_downgrade = inspector.get_table_names()
    assert "durable_tasks" not in tables_after_downgrade
    assert "revoked_tokens" not in tables_after_downgrade
    assert "model_metrics" not in tables_after_downgrade
    engine.dispose()

    # 3. Upgrade back to head (re-verification)
    command.upgrade(alembic_cfg, "head")
    engine = create_engine(db_url)
    inspector = inspect(engine)
    assert "durable_tasks" in inspector.get_table_names()
    assert "model_metrics" in inspector.get_table_names()
    user_cols_final = [c["name"] for c in inspector.get_columns("users")]
    assert "password_changed_at" in user_cols_final
    engine.dispose()
