"""
Clean Source Release Archive Packager.
Packages a production-grade source distribution while strictly excluding:
- .git, node_modules, .env, *.db, .pytest_cache, dist, __pycache__, and developer cache files.
"""

import sys
import os
import zipfile
import argparse
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent

EXCLUDE_DIRS = {
    ".git",
    ".agents",
    "node_modules",
    ".pytest_cache",
    "dist",
    "__pycache__",
    ".venv",
    "venv",
    ".idea",
    ".vscode",
    "evidence",
    "benchmarks/results",
    "research/results",
    ".system_generated",
    "scratch",
}

EXCLUDE_FILES = {
    ".env",
    "ml_studio.db",
    ".DS_Store",
}

EXCLUDE_EXTENSIONS = {
    ".pyc",
    ".pyo",
    ".pyd",
    ".db",
    ".sqlite",
    ".sqlite3",
}


def should_exclude(file_path: Path) -> bool:
    rel_parts = file_path.relative_to(ROOT_DIR).parts
    for part in rel_parts:
        if part in EXCLUDE_DIRS:
            return True
    if file_path.name in EXCLUDE_FILES:
        return True
    if file_path.suffix.lower() in EXCLUDE_EXTENSIONS:
        return True
    return False


def build_release_archive(output_zip: Path) -> tuple[int, int]:
    output_zip.parent.mkdir(parents=True, exist_ok=True)
    file_count = 0
    total_bytes = 0

    with zipfile.ZipFile(output_zip, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(ROOT_DIR):
            # Modify dirs in-place to avoid recursing into excluded directories
            dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
            
            for file in files:
                full_path = Path(root) / file
                if not should_exclude(full_path) and full_path != output_zip:
                    rel_path = full_path.relative_to(ROOT_DIR)
                    zf.write(full_path, arcname=str(rel_path).replace("\\", "/"))
                    file_count += 1
                    total_bytes += full_path.stat().st_size

    return file_count, total_bytes


def verify_archive(zip_path: Path) -> bool:
    print(f"Verifying archive integrity for {zip_path.name}...")
    with zipfile.ZipFile(zip_path, "r") as zf:
        members = zf.namelist()
        violations = []
        for m in members:
            p = Path(m)
            parts = p.parts
            for d in EXCLUDE_DIRS:
                if d in parts:
                    violations.append(f"Contains excluded directory '{d}': {m}")
            if p.name in EXCLUDE_FILES:
                violations.append(f"Contains excluded file '{p.name}': {m}")
            if p.suffix.lower() in EXCLUDE_EXTENSIONS:
                violations.append(f"Contains excluded extension '{p.suffix}': {m}")

        if violations:
            print("[FAIL] Release hygiene verification failed:")
            for v in violations[:10]:
                print(f"  - {v}")
            return False
        else:
            print(f"[OK] Archive is 100% clean! Verified {len(members)} release members.")
            return True


def main():
    parser = argparse.ArgumentParser(description="Package clean source distribution.")
    parser.add_argument("--output", default=str(ROOT_DIR / "dist" / "intelligent-ml-studio-source.zip"))
    parser.add_argument("--verify-clean", action="store_true", help="Verify archive cleanliness")
    args = parser.parse_args()

    out_path = Path(args.output).resolve()
    print("=" * 60)
    print("  ML Studio: Source Release Packaging")
    print("=" * 60)
    print(f"Target: {out_path}")

    files, size = build_release_archive(out_path)
    print(f"Packaged {files} files ({size / (1024 * 1024):.2f} MB raw)")

    if args.verify_clean:
        if not verify_archive(out_path):
            sys.exit(1)


if __name__ == "__main__":
    main()
