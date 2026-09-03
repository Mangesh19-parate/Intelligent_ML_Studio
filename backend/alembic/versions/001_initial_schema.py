"""initial schema and rbac seed

Revision ID: 001_initial_schema
Revises: 
Create Date: 2026-09-03 16:00:00.000000

"""
from typing import Sequence, Union
import uuid
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001_initial_schema'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    # 1. Permissions Table
    permissions_table = op.create_table(
        'permissions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('permission_key', sa.String(length=30), nullable=False, unique=True),
    )
    op.create_index(op.f('ix_permissions_permission_key'), 'permissions', ['permission_key'], unique=True)

    # 2. Roles Table
    roles_table = op.create_table(
        'roles',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('role_name', sa.String(length=50), nullable=False, unique=True),
        sa.Column('description', sa.Text(), nullable=True),
    )
    op.create_index(op.f('ix_roles_role_name'), 'roles', ['role_name'], unique=True)

    # 3. Role Permissions Association Table
    role_permissions_table = op.create_table(
        'role_permissions',
        sa.Column('role_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('roles.id', ondelete='CASCADE'), primary_key=True),
        sa.Column('permission_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('permissions.id', ondelete='CASCADE'), primary_key=True),
    )

    # 4. Users Table
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('full_name', sa.String(length=150), nullable=False),
        sa.Column('email', sa.String(length=150), nullable=False, unique=True),
        sa.Column('password_hash', sa.String(), nullable=False),
        sa.Column('role_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('roles.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)

    # 5. Projects Table
    op.create_table(
        'projects',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('owner_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('project_name', sa.String(length=200), nullable=False),
        sa.Column('task_type', sa.String(length=30), nullable=False, server_default='UNDETERMINED'),
        sa.Column('target_column', sa.String(length=150), nullable=True),
        sa.Column('pipeline_stage', sa.String(length=40), nullable=False, server_default='DATA'),
        sa.Column('data_quality_index', sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("task_type IN ('REGRESSION', 'CLASSIFICATION', 'UNDETERMINED')", name='chk_project_task_type'),
    )

    # 6. Datasets Table
    op.create_table(
        'datasets',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('project_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('projects.id', ondelete='CASCADE'), nullable=False),
        sa.Column('file_path', sa.Text(), nullable=False),
        sa.Column('version_number', sa.Integer(), nullable=False),
        sa.Column('row_count', sa.Integer(), nullable=False),
        sa.Column('column_count', sa.Integer(), nullable=False),
        sa.Column('stage', sa.String(length=30), nullable=False, server_default='RAW'),
        sa.Column('uploaded_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint('project_id', 'version_number', name='uq_project_version_number'),
    )
    op.create_index(op.f('ix_datasets_project_id'), 'datasets', ['project_id'], unique=False)

    # 7. Dataset Columns Table
    op.create_table(
        'dataset_columns',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('dataset_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('datasets.id', ondelete='CASCADE'), nullable=False),
        sa.Column('column_name', sa.String(length=150), nullable=False),
        sa.Column('data_type', sa.String(length=30), nullable=False),
        sa.Column('unique_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('missing_percentage', sa.Numeric(precision=5, scale=2), nullable=False, server_default='0.00'),
        sa.Column('is_target', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.CheckConstraint("data_type IN ('NUMERIC', 'CATEGORICAL', 'DATETIME', 'MIXED')", name='chk_column_data_type'),
    )
    op.create_index(op.f('ix_dataset_columns_dataset_id'), 'dataset_columns', ['dataset_id'], unique=False)

    # Seed Canonical Data
    perms_data = [
        {"id": uuid.uuid4(), "permission_key": "READ"},
        {"id": uuid.uuid4(), "permission_key": "EDIT_DATA"},
        {"id": uuid.uuid4(), "permission_key": "TRAIN"},
        {"id": uuid.uuid4(), "permission_key": "DEPLOY"},
        {"id": uuid.uuid4(), "permission_key": "MANAGE_USERS"},
        {"id": uuid.uuid4(), "permission_key": "EXPORT"},
    ]
    op.bulk_insert(permissions_table, perms_data)
    perm_id_by_key = {p["permission_key"]: p["id"] for p in perms_data}

    roles_data = [
        {"id": uuid.uuid4(), "role_name": "ADMIN", "description": "System administrator with full permissions"},
        {"id": uuid.uuid4(), "role_name": "ML_ENGINEER", "description": "Machine learning engineer with training and data edit permissions"},
        {"id": uuid.uuid4(), "role_name": "DATA_STEWARD", "description": "Data steward with dataset management and editing permissions"},
        {"id": uuid.uuid4(), "role_name": "DEPLOYMENT_MANAGER", "description": "Deployment manager with model deployment and export permissions"},
        {"id": uuid.uuid4(), "role_name": "VIEWER", "description": "Read-only viewer with inspection permissions"},
    ]
    op.bulk_insert(roles_table, roles_data)
    role_id_by_name = {r["role_name"]: r["id"] for r in roles_data}

    role_perms_mapping = {
        "ADMIN": ["READ", "EDIT_DATA", "TRAIN", "DEPLOY", "MANAGE_USERS", "EXPORT"],
        "ML_ENGINEER": ["READ", "EDIT_DATA", "TRAIN", "EXPORT"],
        "DATA_STEWARD": ["READ", "EDIT_DATA"],
        "DEPLOYMENT_MANAGER": ["READ", "DEPLOY", "EXPORT"],
        "VIEWER": ["READ"],
    }

    role_perms_rows = []
    for role_name, perm_keys in role_perms_mapping.items():
        role_id = role_id_by_name[role_name]
        for key in perm_keys:
            role_perms_rows.append({
                "role_id": role_id,
                "permission_id": perm_id_by_key[key]
            })

    op.bulk_insert(role_permissions_table, role_perms_rows)

def downgrade() -> None:
    op.drop_table('dataset_columns')
    op.drop_table('datasets')
    op.drop_table('projects')
    op.drop_table('users')
    op.drop_table('role_permissions')
    op.drop_table('roles')
    op.drop_table('permissions')
