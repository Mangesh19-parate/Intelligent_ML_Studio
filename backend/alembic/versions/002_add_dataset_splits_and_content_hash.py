"""add dataset_splits and content_hash

Revision ID: 002_add_dataset_splits_and_content_hash
Revises: 001_initial_schema
Create Date: 2026-09-04 10:00:00.000000

"""
from typing import Sequence, Union
import uuid
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '002_add_dataset_splits_and_content_hash'
down_revision: Union[str, None] = '001_initial_schema'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    # 1. Add content_hash to datasets
    op.add_column(
        'datasets',
        sa.Column('content_hash', sa.String(length=64), nullable=True)
    )

    # 2. Create dataset_splits table
    op.create_table(
        'dataset_splits',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('dataset_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('datasets.id', ondelete='CASCADE'), nullable=False),
        sa.Column('split_type', sa.String(length=20), nullable=False),
        sa.Column('split_seed', sa.Integer(), nullable=False),
        sa.Column('row_indices', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("split_type IN ('DEVELOPMENT', 'LOCKED_TEST')", name='chk_dataset_split_type'),
        sa.UniqueConstraint('dataset_id', 'split_type', name='uq_dataset_split_type'),
    )
    op.create_index(op.f('ix_dataset_splits_dataset_id'), 'dataset_splits', ['dataset_id'], unique=False)

def downgrade() -> None:
    op.drop_index(op.f('ix_dataset_splits_dataset_id'), table_name='dataset_splits')
    op.drop_table('dataset_splits')
    op.drop_column('datasets', 'content_hash')
