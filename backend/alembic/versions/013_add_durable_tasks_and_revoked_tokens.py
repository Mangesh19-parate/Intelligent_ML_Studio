"""add durable tasks and revoked tokens
 
Revision ID: 013_add_durable_tasks_and_revoked_tokens
Revises: 012_add_reproducibility_runs_table
Create Date: 2026-09-13 15:30:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '013_add_durable_tasks_and_revoked_tokens'
down_revision: Union[str, None] = '012_add_reproducibility_runs_table'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = inspector.get_table_names()

    # 1. Create durable_tasks table
    if 'durable_tasks' not in tables:
        op.create_table(
            'durable_tasks',
            sa.Column('id', sa.String(length=64), nullable=False),
            sa.Column('experiment_id', sa.Uuid(), nullable=False),
            sa.Column('state', sa.String(length=32), nullable=False, server_default='QUEUED'),
            sa.Column('idempotency_key', sa.String(length=128), nullable=True),
            sa.Column('retry_count', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('max_retries', sa.Integer(), nullable=False, server_default='3'),
            sa.Column('timeout_seconds', sa.Integer(), nullable=False, server_default='600'),
            sa.Column('worker_id', sa.String(length=128), nullable=True),
            sa.Column('queued_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
            sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('finished_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('failure_reason', sa.Text(), nullable=True),
            sa.Column('result_summary', sa.JSON(), nullable=True),
            sa.ForeignKeyConstraint(['experiment_id'], ['experiments.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_durable_tasks_experiment_id'), 'durable_tasks', ['experiment_id'], unique=False)
        op.create_index(op.f('ix_durable_tasks_state'), 'durable_tasks', ['state'], unique=False)
        op.create_index(op.f('ix_durable_tasks_idempotency_key'), 'durable_tasks', ['idempotency_key'], unique=True)

    # 2. Create revoked_tokens table
    if 'revoked_tokens' not in tables:
        op.create_table(
            'revoked_tokens',
            sa.Column('id', sa.Uuid(), nullable=False),
            sa.Column('token_hash', sa.String(length=64), nullable=False),
            sa.Column('user_id', sa.Uuid(), nullable=False),
            sa.Column('revoked_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_revoked_tokens_token_hash'), 'revoked_tokens', ['token_hash'], unique=True)
        op.create_index(op.f('ix_revoked_tokens_user_id'), 'revoked_tokens', ['user_id'], unique=False)

    # 3. Add fold provenance columns to feature_selection_fold_results if not present
    if 'feature_selection_fold_results' in tables:
        cols = [c['name'] for c in inspector.get_columns('feature_selection_fold_results')]
        if 'selector' not in cols:
            op.add_column('feature_selection_fold_results', sa.Column('selector', sa.String(length=100), nullable=True))
        if 'permutation_source' not in cols:
            op.add_column('feature_selection_fold_results', sa.Column('permutation_source', sa.String(length=64), nullable=True))
        if 'locked_test_accessed' not in cols:
            op.add_column('feature_selection_fold_results', sa.Column('locked_test_accessed', sa.Boolean(), server_default='false', nullable=False))
        if 'train_row_hash' not in cols:
            op.add_column('feature_selection_fold_results', sa.Column('train_row_hash', sa.String(length=64), nullable=True))
        if 'validation_row_hash' not in cols:
            op.add_column('feature_selection_fold_results', sa.Column('validation_row_hash', sa.String(length=64), nullable=True))
        if 'test_row_hash' not in cols:
            op.add_column('feature_selection_fold_results', sa.Column('test_row_hash', sa.String(length=64), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = inspector.get_table_names()

    if 'revoked_tokens' in tables:
        op.drop_index(op.f('ix_revoked_tokens_user_id'), table_name='revoked_tokens')
        op.drop_index(op.f('ix_revoked_tokens_token_hash'), table_name='revoked_tokens')
        op.drop_table('revoked_tokens')

    if 'durable_tasks' in tables:
        op.drop_index(op.f('ix_durable_tasks_idempotency_key'), table_name='durable_tasks')
        op.drop_index(op.f('ix_durable_tasks_state'), table_name='durable_tasks')
        op.drop_index(op.f('ix_durable_tasks_experiment_id'), table_name='durable_tasks')
        op.drop_table('durable_tasks')
