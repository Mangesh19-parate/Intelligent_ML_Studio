"""add transformation_configs table

Revision ID: 004_add_transformation_configs
Revises: 003_add_profiling_and_recommendations
Create Date: 2026-09-04 16:00:00.000000

"""
from typing import Sequence, Union
import uuid
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '004_add_transformation_configs'
down_revision: Union[str, None] = '003_add_profiling_and_recommendations'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.create_table(
        'transformation_configs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('project_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('projects.id', ondelete='CASCADE'), nullable=False),
        sa.Column('column_name', sa.String(length=150), nullable=False),
        sa.Column('missing_value_strategy', sa.String(length=30), nullable=True),
        sa.Column('encoding_strategy', sa.String(length=30), nullable=True),
        sa.Column('scaling_strategy', sa.String(length=30), nullable=True),
        sa.Column('outlier_strategy', sa.String(length=30), nullable=True),
        sa.Column('is_active', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint('project_id', 'column_name', name='uq_transformation_project_column')
    )
    op.create_index(op.f('ix_transformation_configs_project_id'), 'transformation_configs', ['project_id'], unique=False)

def downgrade() -> None:
    op.drop_index(op.f('ix_transformation_configs_project_id'), table_name='transformation_configs')
    op.drop_table('transformation_configs')
