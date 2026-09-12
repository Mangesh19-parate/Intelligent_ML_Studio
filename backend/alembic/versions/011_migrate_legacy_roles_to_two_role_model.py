"""migrate legacy roles to two role model

Revision ID: 011_migrate_legacy_roles_to_two_role_model
Revises: 010_add_user_permission_overrides
Create Date: 2026-09-12 12:00:00.000000

"""
from typing import Sequence, Union
import uuid
from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import table, column

# revision identifiers, used by Alembic.
revision: str = '011_migrate_legacy_roles_to_two_role_model'
down_revision: Union[str, None] = '010_add_user_permission_overrides'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = inspector.get_table_names()

    if 'roles' in tables and 'users' in tables:
        roles_tbl = table('roles', column('id', sa.Uuid), column('role_name', sa.String), column('description', sa.String))
        users_tbl = table('users', column('id', sa.Uuid), column('role_id', sa.Uuid))
        overrides_tbl = table('user_permission_overrides', column('id', sa.Uuid), column('user_id', sa.Uuid), column('permission_key', sa.String), column('is_granted', sa.Boolean))

        # 1. Ensure USER role exists
        user_role_row = bind.execute(sa.select(roles_tbl.c.id).where(roles_tbl.c.role_name == 'USER')).first()
        if not user_role_row:
            user_role_id = uuid.uuid4()
            bind.execute(roles_tbl.insert().values(id=user_role_id, role_name='USER', description='Standard workbench user'))
        else:
            user_role_id = user_role_row[0]

        # 2. Find legacy roles
        legacy_roles = bind.execute(sa.select(roles_tbl.c.id, roles_tbl.c.role_name).where(roles_tbl.c.role_name.in_(['ML_ENGINEER', 'DATA_STEWARD', 'DEPLOYMENT_MANAGER', 'VIEWER']))).fetchall()
        for leg_id, leg_name in legacy_roles:
            # For DEPLOYMENT_MANAGER users, grant DEPLOY override
            if leg_name == 'DEPLOYMENT_MANAGER' and 'user_permission_overrides' in tables:
                dep_users = bind.execute(sa.select(users_tbl.c.id).where(users_tbl.c.role_id == leg_id)).fetchall()
                for (u_id,) in dep_users:
                    existing_ov = bind.execute(sa.select(overrides_tbl.c.id).where(overrides_tbl.c.user_id == u_id, overrides_tbl.c.permission_key == 'DEPLOY')).first()
                    if not existing_ov:
                        bind.execute(overrides_tbl.insert().values(id=uuid.uuid4(), user_id=u_id, permission_key='DEPLOY', is_granted=True))

            # Reassign users to USER role
            bind.execute(users_tbl.update().where(users_tbl.c.role_id == leg_id).values(role_id=user_role_id))

            # Delete legacy role
            if 'role_permissions' in tables:
                role_perm_tbl = table('role_permissions', column('role_id', sa.Uuid))
                bind.execute(role_perm_tbl.delete().where(role_perm_tbl.c.role_id == leg_id))
            bind.execute(roles_tbl.delete().where(roles_tbl.c.id == leg_id))


def downgrade() -> None:
    pass
