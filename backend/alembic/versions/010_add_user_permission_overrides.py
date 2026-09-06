"""add user_permission_overrides table

Revision ID: 010_add_user_permission_overrides
Revises: 009_add_deployments_and_gates
Create Date: 2026-09-06 14:00:00.000000

"""
from typing import Sequence, Union
import uuid
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '010_add_user_permission_overrides'
down_revision: Union[str, None] = '009_add_deployments_and_gates'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = inspector.get_table_names()

    if 'user_permission_overrides' not in tables:
        op.create_table(
            'user_permission_overrides',
            sa.Column('id', sa.Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4),
            sa.Column('user_id', sa.Uuid(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
            sa.Column('permission_key', sa.String(length=50), nullable=False),
            sa.Column('is_granted', sa.Boolean(), nullable=False, default=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.UniqueConstraint('user_id', 'permission_key', name='uq_user_permission_override'),
        )
        op.create_index('ix_user_permission_overrides_user_id', 'user_permission_overrides', ['user_id'])
        op.create_index('ix_user_permission_overrides_permission_key', 'user_permission_overrides', ['permission_key'])


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = inspector.get_table_names()

    if 'user_permission_overrides' in tables:
        op.drop_table('user_permission_overrides')
