"""add task_type, fold_count, cv_seed to experiments and create trained_models table

Revision ID: 006_add_model_training
Revises: 005_add_experiments_and_feature_selection
Create Date: 2026-09-04 19:30:00.000000

"""
from typing import Sequence, Union
import uuid
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '006_add_model_training'
down_revision: Union[str, None] = '005_add_experiments_and_feature_selection'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    # 1. Add columns to experiments shell table
    op.add_column('experiments', sa.Column('task_type', sa.String(length=30), nullable=True))
    op.add_column('experiments', sa.Column('fold_count', sa.Integer(), nullable=True))
    op.add_column('experiments', sa.Column('cv_seed', sa.Integer(), nullable=True))

    # 2. Create trained_models table
    op.create_table(
        'trained_models',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('experiment_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('experiments.id', ondelete='CASCADE'), nullable=False),
        sa.Column('algorithm_name', sa.String(length=60), nullable=False),
        sa.Column('hyperparameters', sa.JSON(), nullable=False),
        sa.Column('quick_cv_score', sa.Numeric(precision=10, scale=5), nullable=True),
        sa.Column('status', sa.String(length=20), server_default='COMPLETED', nullable=False),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index(op.f('ix_trained_models_experiment_id'), 'trained_models', ['experiment_id'], unique=False)

def downgrade() -> None:
    op.drop_index(op.f('ix_trained_models_experiment_id'), table_name='trained_models')
    op.drop_table('trained_models')
    op.drop_column('experiments', 'cv_seed')
    op.drop_column('experiments', 'fold_count')
    op.drop_column('experiments', 'task_type')
