.PHONY: help install test typecheck lint format format-check verify build run-dev run-prod clean

help:
	@echo "Intelligent ML Studio - Development & Build Automation"
	@echo "  make install      - Install locked Python dependencies and clean Node packages"
	@echo "  make test         - Run backend and frontend automated test suites"
	@echo "  make typecheck    - Run frontend TypeScript type checking"
	@echo "  make lint         - Run frontend ESLint checks with zero warnings tolerance"
	@echo "  make format       - Format frontend code with Prettier"
	@echo "  make format-check - Verify frontend formatting with Prettier"
	@echo "  make verify       - Run full multi-tier verification harness"
	@echo "  make run-dev      - Start local development environment with Docker Compose"
	@echo "  make run-prod     - Start production-hardened Docker Compose stack"
	@echo "  make clean        - Clean cache files and temporary test artifacts"

install:
	cd apps/backend && pip install -r requirements.lock
	cd apps/frontend && npm ci

test:
	cd apps/backend && pytest -q
	cd apps/frontend && npm run test -- --run

typecheck:
	cd apps/frontend && npm run typecheck

lint:
	cd apps/frontend && npm run lint

format:
	cd apps/frontend && npm run format

format-check:
	cd apps/frontend && npm run format:check

verify:
	python scripts/verify.py

run-dev:
	docker compose -f infra/docker/docker-compose.dev.yml up --build

run-prod:
	docker compose -f infra/docker/docker-compose.prod.yml up --build -d

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	rm -rf apps/frontend/dist
