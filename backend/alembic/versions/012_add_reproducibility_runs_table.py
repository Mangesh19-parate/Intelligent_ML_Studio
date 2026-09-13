"""add reproducibility runs table

Revision ID: 012_add_reproducibility_runs_table
Revises: 011_migrate_legacy_roles_to_two_role_model
Create Date: 2026-09-13 14:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '012_add_reproducibility_runs_table'
down_revision: Union[str, None] = '011_migrate_legacy_roles_to_two_role_model'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = inspector.get_table_names()

    if 'reproducibility_runs' not in tables:
        op.create_table(
            'reproducibility_runs',
            sa.Column('id', sa.Uuid(), nullable=False),
            sa.Column('source_experiment_id', sa.Uuid(), nullable=False),
            sa.Column('status', sa.String(length=30), nullable=False),
            sa.Column('expected_metric', sa.Float(), nullable=True),
            sa.Column('observed_metric', sa.Float(), nullable=True),
            sa.Column('difference', sa.Float(), nullable=True),
            sa.Column('absolute_tolerance', sa.Float(), nullable=False, server_default='0.001'),
            sa.Column('relative_tolerance', sa.Float(), nullable=False, server_default='0.01'),
            sa.Column('code_version', sa.String(length=100), nullable=True),
            sa.Column('dataset_hash', sa.String(length=64), nullable=True),
            sa.Column('config_hash', sa.String(length=64), nullable=True),
            sa.Column('locked_test_accessed', sa.Boolean(), nullable=False, server_default='false'),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
            sa.ForeignKeyConstraint(['source_experiment_id'], ['experiments.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_reproducibility_runs_source_experiment_id'), 'reproducibility_runs', ['source_experiment_id'], unique=False)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = inspector.get_table_names()

    if 'reproducibility_runs' in tables:
        op.drop_index(op.f('ix_reproducibility_runs_source_experiment_id'), table_name='reproducibility_runs')
        op.drop_table('reproducibility_runs')
