"""add minimal experiments, feature_selection_fold_results, and feature_importance_scores tables

Revision ID: 005_add_experiments_and_feature_selection
Revises: 004_add_transformation_configs
Create Date: 2026-09-04 17:30:00.000000

"""
from typing import Sequence, Union
import uuid
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '005_add_experiments_and_feature_selection'
down_revision: Union[str, None] = '004_add_transformation_configs'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    # 1. Create minimal experiments shell table
    op.create_table(
        'experiments',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('project_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('projects.id', ondelete='CASCADE'), nullable=False),
        sa.Column('status', sa.String(length=20), server_default='RUNNING', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("status IN ('RUNNING', 'COMPLETED', 'FAILED')", name='chk_experiment_status')
    )
    op.create_index(op.f('ix_experiments_project_id'), 'experiments', ['project_id'], unique=False)

    # 2. Create feature_selection_fold_results table
    op.create_table(
        'feature_selection_fold_results',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('experiment_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('experiments.id', ondelete='CASCADE'), nullable=False),
        sa.Column('fold_index', sa.Integer(), nullable=False),
        sa.Column('selected_features', sa.JSON(), nullable=False),
        sa.Column('technique_scores', sa.JSON(), nullable=False),
        sa.UniqueConstraint('experiment_id', 'fold_index', name='uq_fs_fold_results_exp_fold')
    )
    op.create_index(op.f('ix_feature_selection_fold_results_experiment_id'), 'feature_selection_fold_results', ['experiment_id'], unique=False)

    # 3. Create feature_importance_scores table
    op.create_table(
        'feature_importance_scores',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('project_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('projects.id', ondelete='CASCADE'), nullable=False),
        sa.Column('column_name', sa.String(length=150), nullable=False),
        sa.Column('avg_rank_score', sa.Numeric(precision=6, scale=4), nullable=False),
        sa.Column('is_selected', sa.Boolean(), server_default='true', nullable=False),
        sa.UniqueConstraint('project_id', 'column_name', name='uq_feature_importance_project_col')
    )
    op.create_index(op.f('ix_feature_importance_scores_project_id'), 'feature_importance_scores', ['project_id'], unique=False)

def downgrade() -> None:
    op.drop_index(op.f('ix_feature_importance_scores_project_id'), table_name='feature_importance_scores')
    op.drop_table('feature_importance_scores')
    op.drop_index(op.f('ix_feature_selection_fold_results_experiment_id'), table_name='feature_selection_fold_results')
    op.drop_table('feature_selection_fold_results')
    op.drop_index(op.f('ix_experiments_project_id'), table_name='experiments')
    op.drop_table('experiments')
