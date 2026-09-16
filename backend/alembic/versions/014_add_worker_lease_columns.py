"""add worker lease and heartbeat columns to durable_tasks

Revision ID: 014_worker_leases
Revises: 013_durable_tasks
Create Date: 2026-09-15 12:45:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '014_worker_leases'
down_revision: Union[str, None] = '013_durable_tasks'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = inspector.get_table_names()

    if 'durable_tasks' in tables:
        cols = [c['name'] for c in inspector.get_columns('durable_tasks')]
        if 'lease_expires_at' not in cols:
            op.add_column('durable_tasks', sa.Column('lease_expires_at', sa.DateTime(timezone=True), nullable=True))
            op.create_index(op.f('ix_durable_tasks_lease_expires_at'), 'durable_tasks', ['lease_expires_at'], unique=False)
        if 'heartbeat_at' not in cols:
            op.add_column('durable_tasks', sa.Column('heartbeat_at', sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = inspector.get_table_names()

    if 'durable_tasks' in tables:
        cols = [c['name'] for c in inspector.get_columns('durable_tasks')]
        if 'lease_expires_at' in cols:
            op.drop_index(op.f('ix_durable_tasks_lease_expires_at'), table_name='durable_tasks')
            op.drop_column('durable_tasks', 'lease_expires_at')
        if 'heartbeat_at' in cols:
            op.drop_column('durable_tasks', 'heartbeat_at')
