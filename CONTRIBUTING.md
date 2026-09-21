# Contributing to Intelligent ML Studio

Thank you for your interest in contributing to Intelligent ML Studio!

## Codebase Topology

- `apps/backend/`: FastAPI Modular Monolith + Dedicated Worker execution engine.
- `apps/frontend/`: React 18 + TypeScript + Vite dashboard.
- `infra/`: Docker compose files, Render manifests, Nginx configs.
- `docs/`: System architecture, ML invariants, and Architecture Decision Records (ADRs).
- `scripts/`: Dev, CI, benchmark, and verification utilities.

## Development Workflow

1. Fork and clone the repository.
2. Setup local backend:
   ```bash
   cd apps/backend
   python -m venv venv
   source venv/bin/activate # or .\venv\Scripts\activate on Windows
   pip install -r requirements.txt
   alembic upgrade head
   ```
3. Setup local frontend:
   ```bash
   cd apps/frontend
   npm install
   npm run dev
   ```
4. Run deterministic verification before opening a pull request:
   ```bash
   python scripts/verify.py
   ```

## Coding & Architectural Standards

- **Zero-Leakage Invariants**: All preprocessing, transformations, and feature selections must strictly be fitted inside cross-validation training folds. Holdout test sets must never be fitted.
- **Bounded Contexts**: Place business logic in `application/`, ML algorithms in `ml/`, invariants in `domain/`, and persistence in `infrastructure/`.
- **Testing**: Maintain 100% test pass rate with unit, integration, and invariant regression suites.
