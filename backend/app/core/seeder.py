import logging
from sqlalchemy.orm import Session
from app.models.role import Role
from app.models.permission import Permission
from app.models.role_permission import role_permissions

logger = logging.getLogger(__name__)

CANONICAL_ROLES = [
    ("ADMIN", "System administrator with full permissions"),
    ("ML_ENGINEER", "Machine learning engineer with training and data edit permissions"),
    ("DATA_STEWARD", "Data steward with dataset management and editing permissions"),
    ("DEPLOYMENT_MANAGER", "Deployment manager with model deployment and export permissions"),
    ("VIEWER", "Read-only viewer with inspection permissions"),
]

CANONICAL_PERMISSIONS = [
    "READ",
    "EDIT_DATA",
    "TRAIN",
    "DEPLOY",
    "MANAGE_USERS",
    "EXPORT",
]

DEFAULT_ROLE_PERMISSIONS: dict[str, list[str]] = {
    "ADMIN": ["READ", "EDIT_DATA", "TRAIN", "DEPLOY", "MANAGE_USERS", "EXPORT"],
    "ML_ENGINEER": ["READ", "EDIT_DATA", "TRAIN", "EXPORT"],
    "DATA_STEWARD": ["READ", "EDIT_DATA"],
    "DEPLOYMENT_MANAGER": ["READ", "DEPLOY", "EXPORT"],
    "VIEWER": ["READ"],
}

def seed_rbac_data(db: Session) -> None:
    """
    Seeds canonical roles, permissions, and role-permission mappings.
    Idempotent: will not duplicate existing entities.
    """
    # 1. Seed Permissions
    permission_map: dict[str, Permission] = {}
    for perm_key in CANONICAL_PERMISSIONS:
        perm = db.query(Permission).filter(Permission.permission_key == perm_key).first()
        if not perm:
            perm = Permission(permission_key=perm_key)
            db.add(perm)
            db.flush()
        permission_map[perm_key] = perm

    # 2. Seed Roles
    role_map: dict[str, Role] = {}
    for role_name, description in CANONICAL_ROLES:
        role = db.query(Role).filter(Role.role_name == role_name).first()
        if not role:
            role = Role(role_name=role_name, description=description)
            db.add(role)
            db.flush()
        role_map[role_name] = role

    # 3. Seed Role-Permission Associations
    for role_name, allowed_perms in DEFAULT_ROLE_PERMISSIONS.items():
        role = role_map.get(role_name)
        if not role:
            continue
        
        current_perm_ids = {p.id for p in role.permissions}
        for perm_key in allowed_perms:
            perm = permission_map.get(perm_key)
            if perm and perm.id not in current_perm_ids:
                role.permissions.append(perm)

    db.commit()
    logger.info("RBAC roles, permissions, and mappings successfully seeded.")
