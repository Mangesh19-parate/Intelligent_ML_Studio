"""
Unit & Regression Tests for Clean Source Release Packaging & Verification Gates.
"""

import sys
import zipfile
from pathlib import Path
import pytest

from scripts.package_release import (
    ROOT_DIR,
    EXCLUDE_DIR_NAMES,
    EXCLUDE_PATH_PREFIXES,
    EXCLUDE_FILES,
    EXCLUDE_EXTENSIONS,
    should_exclude,
    is_excluded_dir_rel,
    build_release_archive,
    verify_archive,
)


def test_is_excluded_dir_rel():
    assert is_excluded_dir_rel("research/results") is True
    assert is_excluded_dir_rel("research/results/subfolder") is True
    assert is_excluded_dir_rel("evidence") is True
    assert is_excluded_dir_rel("evidence/ml") is True
    assert is_excluded_dir_rel("benchmarks/results") is True
    assert is_excluded_dir_rel("apps/frontend/node_modules") is True
    assert is_excluded_dir_rel("apps/backend/__pycache__") is True
    assert is_excluded_dir_rel("apps/backend/app") is False
    assert is_excluded_dir_rel("research/protocol") is False


def test_should_exclude_compound_paths():
    # Compound directories that previously slipped through
    assert should_exclude(ROOT_DIR / "research" / "results" / "statistical_summary.json") is True
    assert should_exclude(ROOT_DIR / "research" / "results" / "alpha_ablation.csv") is True
    assert should_exclude(ROOT_DIR / "evidence" / "qa" / "test-summary.json") is True
    assert should_exclude(ROOT_DIR / "evidence" / "release_certificate.json") is True
    assert should_exclude(ROOT_DIR / "benchmarks" / "results" / "benchmark.json") is True
    assert should_exclude(ROOT_DIR / ".git" / "config") is True
    assert should_exclude(ROOT_DIR / "apps" / "backend" / "data" / "data.db") is True

    # Valid source files must NOT be excluded
    assert should_exclude(ROOT_DIR / "apps" / "backend" / "app" / "main.py") is False
    assert should_exclude(ROOT_DIR / "apps" / "frontend" / "src" / "App.tsx") is False
    assert should_exclude(ROOT_DIR / "pyproject.toml") is False
    assert should_exclude(ROOT_DIR / "README.md") is False


def test_package_and_verify_archive_in_memory(tmp_path):
    out_zip = tmp_path / "test_release.zip"
    count, bytes_count = build_release_archive(out_zip)

    assert count > 0
    assert bytes_count > 0
    assert out_zip.exists()

    # Verify that the generated archive satisfies 100% clean release invariants
    assert verify_archive(out_zip) is True

    # Check contents do not contain any excluded items
    with zipfile.ZipFile(out_zip, "r") as zf:
        names = zf.namelist()
        for name in names:
            assert not name.startswith("research/results/"), f"Archive contained forbidden: {name}"
            assert not name.startswith("evidence/"), f"Archive contained forbidden: {name}"
            assert not name.startswith(".git/"), f"Archive contained forbidden: {name}"
            assert "node_modules" not in name, f"Archive contained node_modules: {name}"
            assert not name.endswith(".pyc"), f"Archive contained forbidden: {name}"
            assert not name.endswith(".db"), f"Archive contained forbidden: {name}"
