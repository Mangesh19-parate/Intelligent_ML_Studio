"""add profiling_reports and recommendations tables, add task_type_confidence to projects

Revision ID: 003_add_profiling_and_recommendations
Revises: 002_add_dataset_splits_and_content_hash
Create Date: 2026-09-04 12:00:00.000000

"""
from typing import Sequence, Union
import uuid
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '003_add_profiling_and_recommendations'
down_revision: Union[str, None] = '002_add_dataset_splits_and_content_hash'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    # 1. Add task_type_confidence to projects
    op.add_column(
        'projects',
        sa.Column('task_type_confidence', sa.String(length=20), nullable=True)
    )

    # 2. Create profiling_reports table
    op.create_table(
        'profiling_reports',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('dataset_split_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('dataset_splits.id', ondelete='CASCADE'), nullable=False),
        sa.Column('report_json', sa.JSON(), nullable=False),
        sa.Column('duplicate_row_count', sa.Integer(), nullable=False, default=0),
        sa.Column('generated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index(op.f('ix_profiling_reports_dataset_split_id'), 'profiling_reports', ['dataset_split_id'], unique=True)

    # 3. Create recommendations table
    op.create_table(
        'recommendations',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('project_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('projects.id', ondelete='CASCADE'), nullable=False),
        sa.Column('finding', sa.Text(), nullable=False),
        sa.Column('evidence', sa.Text(), nullable=False),
        sa.Column('recommended_action', sa.Text(), nullable=False),
        sa.Column('risk_note', sa.Text(), nullable=False),
        sa.Column('confidence', sa.String(length=10), nullable=False),
        sa.Column('status', sa.String(length=20), server_default='SUGGESTED', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("confidence IN ('HIGH', 'MEDIUM', 'LOW')", name='chk_recommendation_confidence')
    )
    op.create_index(op.f('ix_recommendations_project_id'), 'recommendations', ['project_id'], unique=False)

def downgrade() -> None:
    op.drop_index(op.f('ix_recommendations_project_id'), table_name='recommendations')
    op.drop_table('recommendations')
    op.drop_index(op.f('ix_profiling_reports_dataset_split_id'), table_name='profiling_reports')
    op.drop_table('profiling_reports')
    op.drop_column('projects', 'task_type_confidence')
