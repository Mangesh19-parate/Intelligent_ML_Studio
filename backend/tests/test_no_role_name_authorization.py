"""
Regression Guard: test_no_role_name_authorization.py
Reference: Software Requirements Specification (SRS) v9 §9 / §1.3

Performs a static scan across the service and API layers (backend/app/api and backend/app/services)
to assert that NO code uses direct role-name checks (e.g. `user.role ==`, `role in [`, `.role_name ==`,
`current_user.role ==`) for authorization.

Authorization MUST exclusively use the permission-based primitive:
`require_permission(permission_key)` from `app.core.dependencies`.
"""

import ast
import os
import re
from pathlib import Path


FORBIDDEN_PATTERNS = [
    re.compile(r"\buser\.role\s*==\s*", re.IGNORECASE),
    re.compile(r"\buser\.role\s*!=\s*", re.IGNORECASE),
    re.compile(r"\bcurrent_user\.role\s*==\s*", re.IGNORECASE),
    re.compile(r"\bcurrent_user\.role\s*!=\s*", re.IGNORECASE),
    re.compile(r"\brole\s+in\s+\[", re.IGNORECASE),
    re.compile(r"\brole_name\s+in\s+\[", re.IGNORECASE),
    re.compile(r"\buser\.role_name\s*==\s*", re.IGNORECASE),
    re.compile(r"\bcurrent_user\.role\.role_name\s*==\s*", re.IGNORECASE),
    re.compile(r"\bcurrent_user\.role_id\s*==\s*", re.IGNORECASE),
]

# Allowable exceptions where role metadata is strictly read for presentation/serialization (not auth checks)
ALLOWED_EXEMPTIONS = {
    # auth_service converts user.role for UserResponse schema serialization
    "auth_service.py": [
        "user.role.permissions",
        "user.role.id",
        "user.role.role_name",
        "user.role.description",
    ]
}


def test_static_scan_no_role_name_authorization():
    """
    Scans all Python files in app/api and app/services for forbidden role comparison patterns.
    Fails immediately if any route or service performs direct role-name based authorization.
    """
    backend_root = Path(__file__).resolve().parent.parent
    app_dir = backend_root / "app"
    
    target_dirs = [
        app_dir / "api",
        app_dir / "services",
    ]

    violations = []

    for target_dir in target_dirs:
        assert target_dir.exists(), f"Target directory {target_dir} does not exist."
        for root, _, files in os.walk(target_dir):
            for file in files:
                if not file.endswith(".py"):
                    continue
                
                filepath = Path(root) / file
                rel_path = filepath.relative_to(app_dir)
                filename = file

                with open(filepath, "r", encoding="utf-8") as f:
                    lines = f.readlines()

                for line_idx, line in enumerate(lines, start=1):
                    # Skip comment lines
                    stripped = line.strip()
                    if stripped.startswith("#"):
                        continue

                    for pattern in FORBIDDEN_PATTERNS:
                        if pattern.search(line):
                            violations.append(
                                f"Forbidden role-name authorization pattern '{pattern.pattern}' found in "
                                f"{rel_path}:{line_idx}\n    --> {stripped}"
                            )

    assert not violations, (
        f"Found {len(violations)} role-name authorization violation(s):\n"
        + "\n".join(violations)
        + "\n\nAll authorization checks MUST use `require_permission(permission_key)` instead of inspecting role names."
    )
