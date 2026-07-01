#!/usr/bin/env bash
# Start a local Postgres container (if not already running) then launch the API server.
set -euo pipefail

CONTAINER_NAME="housedreamer-postgres"
DB_USER="housedreamer"
DB_PASS="housedreamer"
DB_NAME="housedreamer"
DB_PORT="5432"
DATABASE_URL="postgresql+asyncpg://${DB_USER}:${DB_PASS}@localhost:${DB_PORT}/${DB_NAME}"

# ── Docker check ─────────────────────────────────────────────────────────────
if ! command -v docker &>/dev/null; then
  echo "ERROR: docker is not installed or not in PATH." >&2
  exit 1
fi

# ── Start container if needed ─────────────────────────────────────────────────
if docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
  echo "[dev] Postgres container '${CONTAINER_NAME}' already running."
elif docker ps -a --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
  echo "[dev] Starting existing container '${CONTAINER_NAME}'..."
  docker start "${CONTAINER_NAME}"
else
  echo "[dev] Creating Postgres container '${CONTAINER_NAME}'..."
  docker run -d \
    --name "${CONTAINER_NAME}" \
    -e POSTGRES_USER="${DB_USER}" \
    -e POSTGRES_PASSWORD="${DB_PASS}" \
    -e POSTGRES_DB="${DB_NAME}" \
    -p "${DB_PORT}:5432" \
    postgres:16-alpine
fi

# ── Wait for Postgres to be ready ────────────────────────────────────────────
echo "[dev] Waiting for Postgres to be ready..."
for i in $(seq 1 20); do
  if docker exec "${CONTAINER_NAME}" pg_isready -U "${DB_USER}" -d "${DB_NAME}" &>/dev/null; then
    echo "[dev] Postgres is ready."
    break
  fi
  if [ "$i" -eq 20 ]; then
    echo "ERROR: Postgres did not become ready in time." >&2
    exit 1
  fi
  sleep 1
done

# ── Launch API ────────────────────────────────────────────────────────────────
export DATABASE_URL="${DATABASE_URL}"
echo "[dev] DATABASE_URL=${DATABASE_URL}"
echo "[dev] Starting API server at http://localhost:8000 ..."
exec uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
