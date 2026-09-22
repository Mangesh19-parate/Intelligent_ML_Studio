"""
CI Documentation Path Integrity Validator.
Scans documentation markdown files for referenced source code and infrastructure paths
to prevent broken links or stale documentation references.
"""

import sys
import re
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent

# Regex to match paths like apps/backend/..., infra/..., etc.
PATH_PATTERN = re.compile(r'[`\[(](apps/[a-zA-Z0-9_\-\./]+|infra/[a-zA-Z0-9_\-\./]+|docs/[a-zA-Z0-9_\-\./]+|scripts/[a-zA-Z0-9_\-\./]+|contracts/[a-zA-Z0-9_\-\./]+|research/[a-zA-Z0-9_\-\./]+)[`)\]]')


def validate_doc_file(doc_path: Path) -> list[str]:
    errors = []
    content = doc_path.read_text(encoding="utf-8")
    matches = PATH_PATTERN.findall(content)

    for m in matches:
        clean_path = m.split("#")[0].split("<br>")[0].strip().rstrip(".,;:)")
        if not clean_path:
            continue
        target = ROOT_DIR / clean_path
        if not target.exists():
            errors.append(f"[{doc_path.name}] Broken path reference: '{clean_path}' does not exist on disk.")

    return errors


def main():
    print("=" * 60)
    print("  ML Studio: Documentation Path Validation CI")
    print("=" * 60)

    doc_files = [
        ROOT_DIR / "DEPLOYMENT.md",
        ROOT_DIR / "docs" / "claims-matrix.md",
        ROOT_DIR / "README.md",
    ]

    total_errors = []
    for doc in doc_files:
        if doc.exists():
            print(f"Scanning {doc.relative_to(ROOT_DIR)}...")
            errs = validate_doc_file(doc)
            total_errors.extend(errs)

    if total_errors:
        print("\n[FAIL] Documentation path validation FAILED with the following errors:")
        for err in total_errors:
            print(f"  - {err}")
        sys.exit(1)
    else:
        print("\n[OK] All documentation path references are valid and verified!")
        sys.exit(0)


if __name__ == "__main__":
    main()
