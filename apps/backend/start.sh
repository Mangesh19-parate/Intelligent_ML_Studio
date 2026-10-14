#!/usr/bin/env bash
set -e

echo "=== Starting ML Studio Backend Production Server ==="
echo "Port: ${PORT:-8000}"
echo "Environment: ${ENV:-production}"

# Run database migrations to ensure PostgreSQL schema is completely up-to-date
echo "Running database migrations via Alembic..."
alembic upgrade head

# Start uvicorn server with production settings
echo "Starting Uvicorn..."
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}" --proxy-headers --forwarded-allow-ips='*'
