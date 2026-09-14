"""
Clean Repository Export Script (P4.2).

Produces a pristine, submission-ready archive of the Intelligent ML Studio repository
by pruning ephemeral build artifacts, caches, temporary databases, and environment secrets.

Usage:
    python scripts/export_clean_repo.py [--output-dir ./dist_export] [--format zip|tar.gz]
"""

import os
import sys
import shutil
import tarfile
import zipfile
import argparse
from pathlib import Path

# Directories to exclude
EXCLUDE_DIRS = {
    ".git",
    ".github",
    ".agents",
    "node_modules",
    "dist",
    "build",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "htmlcov",
    ".system_generated",
    "scratch",
    "storage",
    "venv",
    ".venv",
    "env",
}

# File patterns / extensions to exclude
EXCLUDE_EXTENSIONS = {
    ".pyc",
    ".pyo",
    ".pyd",
    ".db",
    ".sqlite",
    ".sqlite3",
    ".log",
    ".coverage",
}

EXCLUDE_FILENAMES = {
    ".DS_Store",
    "Thumbs.db",
    ".env",
    ".env.local",
    ".env.production",
}


def should_exclude(rel_path: Path) -> bool:
    """Evaluates whether a relative file or directory path should be excluded."""
    parts = rel_path.parts

    # Check parent/ancestor directory exclusion
    for part in parts[:-1]:
        if part in EXCLUDE_DIRS:
            return True

    # Check directory itself
    if parts[-1] in EXCLUDE_DIRS:
        return True

    # Check filename & extension
    if parts[-1] in EXCLUDE_FILENAMES:
        return True
    if rel_path.suffix.lower() in EXCLUDE_EXTENSIONS:
        return True

    return False


def export_clean_repository(root_dir: Path, output_dir: Path, archive_format: str = "zip") -> Path:
    """Exports clean repository tree and creates a compressed archive."""
    output_dir.mkdir(parents=True, exist_ok=True)
    archive_base_name = "intelligent-ml-studio-clean"
    export_tree_dir = output_dir / archive_base_name

    if export_tree_dir.exists():
        shutil.rmtree(export_tree_dir)
    export_tree_dir.mkdir(parents=True)

    copied_files = 0
    total_bytes = 0

    print(f"Scanning workspace at: {root_dir}")
    for root, dirs, files in os.walk(root_dir):
        rel_root = Path(root).relative_to(root_dir)

        # Prune excluded directories in-place during walk
        dirs[:] = [d for d in dirs if not should_exclude(rel_root / d)]

        for file in files:
            rel_file_path = rel_root / file
            if should_exclude(rel_file_path):
                continue

            src_path = Path(root) / file
            dest_path = export_tree_dir / rel_file_path
            dest_path.parent.mkdir(parents=True, exist_ok=True)

            shutil.copy2(src_path, dest_path)
            copied_files += 1
            total_bytes += src_path.stat().st_size

    print(f"Copied {copied_files} pristine files ({total_bytes / (1024*1024):.2f} MB) to {export_tree_dir}")

    # Build archive
    archive_path = output_dir / f"{archive_base_name}.{archive_format}"
    if archive_format == "zip":
        with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for root, _, files in os.walk(export_tree_dir):
                for file in files:
                    full_p = Path(root) / file
                    rel_p = full_p.relative_to(output_dir)
                    zf.write(full_p, rel_p)
    elif archive_format in ["tar.gz", "tgz"]:
        with tarfile.open(archive_path, "w:gz") as tf:
            tf.add(export_tree_dir, arcname=archive_base_name)

    print(f"Successfully generated clean export archive: {archive_path}")
    return archive_path


def main():
    parser = argparse.ArgumentParser(description="Export clean Intelligent ML Studio repository.")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("dist_export"),
        help="Destination directory for exported files.",
    )
    parser.add_argument(
        "--format",
        choices=["zip", "tar.gz"],
        default="zip",
        help="Export archive format.",
    )
    args = parser.parse_args()

    workspace_root = Path(__file__).resolve().parent.parent
    export_clean_repository(
        root_dir=workspace_root,
        output_dir=args.output_dir.resolve(),
        archive_format=args.format,
    )


if __name__ == "__main__":
    main()
