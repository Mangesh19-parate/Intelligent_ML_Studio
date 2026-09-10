# ML Studio - Roles

## Identity Roles

```
ADMIN
USER
```

No other role names anywhere in code or UI. Authorization is always via `require_permission(key)`, never a role-name comparison.

## Permissions

| Permission | ADMIN default | USER default | Override-able for USER? |
|---|---|---|---|
| READ | yes | yes | n/a |
| EDIT_DATA | yes | yes | n/a |
| TRAIN | yes | yes | n/a |
| EXPORT | yes | yes | n/a |
| DEPLOY | yes | no | yes, per-user grant |
| MANAGE_USERS | yes | no | no - admin-only, always |

`user_permission_overrides: user_id, permission_key, granted (bool), granted_by, granted_at`. Effective permission = role default bundle, overridden by any explicit grant/revoke row.

## Separation of Duties

`deployment_gates.approved_by` must not equal `trained_models.created_by` for the same deployment, enforced server-side, no exceptions - including for ADMIN accounts. This is why the platform needs per-user permission overrides rather than relying on ADMIN to demonstrate the mechanism: an ADMIN training and approving their own model would trivially satisfy a naive "is admin" check while violating the actual intent.

## Signup & Bootstrap

```
POST /api/v1/auth/signup { email, password, name }
  -> role hardcoded to USER; request rejected if it contains a `role` field at all

CLI, run once at deploy: bootstrap_admin --email --password
  -> refuses to run if any ADMIN account already exists
```

## Demo Accounts

```
trainer@demo.com  - USER, default bundle, no DEPLOY
approver@demo.com - USER, default bundle + explicit DEPLOY override
```

Both are USER. This demonstrates the permission-override mechanism itself, which an ADMIN account would bypass by default.

## Promotion & Overrides (Admin-only)

The User Management page lets an ADMIN promote/demote USER<->ADMIN, deactivate accounts, and grant/revoke the DEPLOY override for a specific USER. There is no per-role page variant for a `VIEWER`/`DATA_STEWARD`/`DEPLOYMENT_MANAGER` - a USER without DEPLOY simply doesn't see the deploy action on a shared page, gated by permission, not by a separate role-specific page.

## Authorization Guarantee, Stated Precisely

The real guarantee is `require_permission(key)` plus integration tests against it. `test_no_role_name_authorization.py` (a static scan for `user.role ==` / `role in [...]` patterns) is a regression heuristic that catches an accidental reintroduction of role-name logic - it is not itself a security proof, and should never be described as one.
