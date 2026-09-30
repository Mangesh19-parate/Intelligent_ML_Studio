"""enforce canonical entity state constraints and migrate legacy statuses

Revision ID: 016_canonical_states
Revises: 015_missing_schema
Create Date: 2026-09-27 20:30:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '016_canonical_states'
down_revision: Union[str, None] = '015_missing_schema'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    # 1. Clean legacy data in experiments table
    if 'experiments' in tables:
        bind.execute(sa.text("UPDATE experiments SET status = 'TRAINING' WHERE status = 'RUNNING'"))
        bind.execute(sa.text("UPDATE experiments SET status = 'REGISTERED' WHERE status = 'COMPLETED' AND selected_model_id IS NOT NULL"))
        bind.execute(sa.text("UPDATE experiments SET status = 'EVALUATED' WHERE status = 'COMPLETED' AND selected_model_id IS NULL"))
        bind.execute(sa.text("UPDATE experiments SET status = 'TRAINING_FAILED' WHERE status = 'FAILED'"))

    # 2. Clean legacy data in trained_models table
    if 'trained_models' in tables:
        bind.execute(sa.text("UPDATE trained_models SET status = 'TRAINED' WHERE status = 'COMPLETED'"))
        bind.execute(sa.text("UPDATE trained_models SET status = 'ARTIFACT_INVALID' WHERE status = 'FAILED'"))

    # 3. Clean legacy data in durable_tasks table
    if 'durable_tasks' in tables:
        bind.execute(sa.text("UPDATE durable_tasks SET state = 'SUCCEEDED' WHERE state = 'COMPLETED'"))

    # 4. Enforce check constraints using batch_alter_table for SQLite & Postgres compatibility
    if 'experiments' in tables:
        with op.batch_alter_table('experiments') as batch_op:
            batch_op.create_check_constraint(
                'chk_experiment_status',
                "status IN ('CREATED', 'CONFIGURED', 'TRAINING', 'EVALUATED', 'TEST_CONSUMED', 'REGISTERED', 'TRAINING_FAILED', 'ARTIFACT_WRITE_FAILED')"
            )

    if 'trained_models' in tables:
        with op.batch_alter_table('trained_models') as batch_op:
            batch_op.create_check_constraint(
                'chk_trained_model_status',
                "status IN ('TRAINED', 'ARTIFACT_VERIFIED', 'DEPLOYABLE', 'ARTIFACT_INVALID', 'CANDIDATE')"
            )

    if 'durable_tasks' in tables:
        with op.batch_alter_table('durable_tasks') as batch_op:
            batch_op.create_check_constraint(
                'chk_durable_task_state',
                "state IN ('QUEUED', 'RUNNING', 'SUCCEEDED', 'FAILED', 'TIMED_OUT', 'CANCELLED')"
            )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    if 'durable_tasks' in tables:
        with op.batch_alter_table('durable_tasks') as batch_op:
            try:
                batch_op.drop_constraint('chk_durable_task_state', type_='check')
            except Exception:
                pass

    if 'trained_models' in tables:
        with op.batch_alter_table('trained_models') as batch_op:
            try:
                batch_op.drop_constraint('chk_trained_model_status', type_='check')
            except Exception:
                pass

    if 'experiments' in tables:
        with op.batch_alter_table('experiments') as batch_op:
            try:
                batch_op.drop_constraint('chk_experiment_status', type_='check')
            except Exception:
                pass
