"""
Clean Source Release Archive Packager.
Packages a production-grade source distribution while strictly excluding:
- .git, node_modules, .env, *.db, .pytest_cache, dist, __pycache__, evidence, artifacts, and developer cache files.
"""

import sys
import os
import zipfile
import argparse
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent

# Directory names that should be excluded wherever they appear in the project tree
EXCLUDE_DIR_NAMES = {
    ".git",
    ".agents",
    "node_modules",
    ".pytest_cache",
    "dist",
    "dist_export",
    "releases",
    "__pycache__",
    ".venv",
    "venv",
    ".idea",
    ".vscode",
    ".system_generated",
    "scratch",
    "coverage",
    ".turbo",
    ".next",
    ".vite",
}

# Specific project-relative paths (or prefixes) that must be excluded
EXCLUDE_PATH_PREFIXES = {
    "evidence",
    "artifacts",
    "models",
    "benchmarks/results",
    "research/results",
    "data",
    "apps/backend/data",
    "apps/frontend/dist",
}

EXCLUDE_FILES = {
    ".env",
    "ml_studio.db",
    "test_ci.db",
    "results.db",
    ".DS_Store",
    "runs.parquet",
}

EXCLUDE_EXTENSIONS = {
    ".pyc",
    ".pyo",
    ".pyd",
    ".db",
    ".sqlite",
    ".sqlite3",
    ".parquet",
    ".joblib",
    ".pkl",
    ".tmp",
}


def is_excluded_dir_rel(rel_posix: str) -> bool:
    parts = rel_posix.split("/")
    for part in parts:
        if part in EXCLUDE_DIR_NAMES:
            return True
    for prefix in EXCLUDE_PATH_PREFIXES:
        if rel_posix == prefix or rel_posix.startswith(f"{prefix}/"):
            return True
    return False


def should_exclude(file_path: Path) -> bool:
    try:
        rel_posix = file_path.relative_to(ROOT_DIR).as_posix()
    except ValueError:
        return True

    if is_excluded_dir_rel(rel_posix):
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
            root_path = Path(root)
            # Filter dirs in-place to avoid descending into excluded directory trees
            dirs_to_keep = []
            for d in dirs:
                if d in EXCLUDE_DIR_NAMES:
                    continue
                sub_rel = (root_path / d).relative_to(ROOT_DIR).as_posix()
                if not is_excluded_dir_rel(sub_rel):
                    dirs_to_keep.append(d)
            dirs[:] = dirs_to_keep

            for file in files:
                full_path = root_path / file
                if not should_exclude(full_path) and full_path != output_zip:
                    rel_path = full_path.relative_to(ROOT_DIR)
                    zf.write(full_path, arcname=rel_path.as_posix())
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
            p_posix = p.as_posix()
            parts = p_posix.split("/")

            for part in parts[:-1]:
                if part in EXCLUDE_DIR_NAMES:
                    violations.append(f"Contains excluded directory name '{part}': {m}")
            for prefix in EXCLUDE_PATH_PREFIXES:
                if p_posix == prefix or p_posix.startswith(f"{prefix}/"):
                    violations.append(f"Contains excluded directory tree '{prefix}': {m}")
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
    parser.add_argument("--require-clean-git", action="store_true", help="Fail if git worktree is dirty")
    parser.add_argument("--verify-clean", action="store_true", help="Verify archive contains no prohibited files/directories")
    args = parser.parse_args()

    if args.require_clean_git:
        import subprocess
        status = subprocess.run(["git", "status", "--porcelain"], cwd=ROOT_DIR, capture_output=True, text=True)
        if status.returncode == 0 and status.stdout.strip():
            print("[FAIL] Git worktree is dirty. Commit or stash changes before packaging clean release.")
            sys.exit(1)

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
