"""
CI Documentation Path Integrity Validator.
Scans all documentation markdown files across the repository for referenced
source code and infrastructure paths to prevent broken links or stale documentation references.
"""

import sys
import os
import re
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent

# Regex to match paths like apps/backend/..., infra/..., etc.
PATH_PATTERN = re.compile(
    r'[`\[(](apps/[a-zA-Z0-9_\-\./]+|infra/[a-zA-Z0-9_\-\./]+|docs/[a-zA-Z0-9_\-\./]+|scripts/[a-zA-Z0-9_\-\./]+|contracts/[a-zA-Z0-9_\-\./]+|research/[a-zA-Z0-9_\-\./]+)[`)\]]'
)

STALE_PREFIX_PATTERN = re.compile(
    r'[`\[(](?:python\s+)?(backend/(?:app|tests|scripts)/[a-zA-Z0-9_\-\./]+|frontend/(?:src|public|package-lock\.json))[`)\]]'
)


def validate_doc_file(doc_path: Path) -> list[str]:
    errors = []
    content = doc_path.read_text(encoding="utf-8")
    
    # Check for stale un-namespaced paths (e.g. backend/tests instead of apps/backend/tests)
    stale_matches = STALE_PREFIX_PATTERN.findall(content)
    for sm in stale_matches:
        errors.append(f"[{doc_path.name}] Stale monorepo path '{sm}'. Should start with 'apps/'.")

    # Check path existence
    matches = PATH_PATTERN.findall(content)
    for m in matches:
        clean_path = m.split("#")[0].split("<br>")[0].strip().rstrip(".,;:)")
        if not clean_path:
            continue
        target = ROOT_DIR / clean_path
        if not target.exists():
            errors.append(f"[{doc_path.name}] Broken path reference: '{clean_path}' does not exist on disk.")

    return errors


def collect_all_markdown_files() -> list[Path]:
    md_files = list(ROOT_DIR.glob("*.md"))
    docs_dir = ROOT_DIR / "docs"
    if docs_dir.exists():
        md_files.extend(docs_dir.rglob("*.md"))
    return sorted(set(md_files))


def main():
    print("=" * 60)
    print("  ML Studio: Documentation Path Validation CI")
    print("=" * 60)

    doc_files = collect_all_markdown_files()
    total_errors = []

    for doc in doc_files:
        rel = doc.relative_to(ROOT_DIR)
        errs = validate_doc_file(doc)
        if errs:
            print(f"Scanning {rel}... [FAIL] ({len(errs)} errors)")
            total_errors.extend(errs)
        else:
            print(f"Scanning {rel}... [OK]")

    if total_errors:
        print(f"\n[FAIL] Documentation path validation FAILED with {len(total_errors)} errors:")
        for err in total_errors:
            print(f"  - {err}")
        sys.exit(1)
    else:
        print(f"\n[OK] All {len(doc_files)} markdown files have valid, verified path references!")
        sys.exit(0)


if __name__ == "__main__":
    main()
