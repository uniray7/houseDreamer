#!/usr/bin/env bash
# Start a local Postgres container + a web DB viewer (Adminer), then launch the API server.
set -euo pipefail

CONTAINER_NAME="housedreamer-postgres"
ADMINER_NAME="housedreamer-adminer"
NETWORK_NAME="housedreamer-net"
DB_USER="housedreamer"
DB_PASS="housedreamer"
DB_NAME="housedreamer"
DB_PORT="${DB_PORT:-5432}"
ADMINER_PORT="${ADMINER_PORT:-8080}"
DATABASE_URL="postgresql+asyncpg://${DB_USER}:${DB_PASS}@localhost:${DB_PORT}/${DB_NAME}"

# ── Docker check ─────────────────────────────────────────────────────────────
if ! command -v docker &>/dev/null; then
  echo "ERROR: docker is not installed or not in PATH." >&2
  exit 1
fi

# ── Ensure shared network exists (lets Adminer reach Postgres by name) ────────
if ! docker network inspect "${NETWORK_NAME}" &>/dev/null; then
  echo "[dev] Creating Docker network '${NETWORK_NAME}'..."
  docker network create "${NETWORK_NAME}" >/dev/null
fi

# ── Start Postgres container if needed ────────────────────────────────────────
if docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
  echo "[dev] Postgres container '${CONTAINER_NAME}' already running."
elif docker ps -a --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
  echo "[dev] Starting existing container '${CONTAINER_NAME}'..."
  docker start "${CONTAINER_NAME}"
else
  echo "[dev] Creating Postgres container '${CONTAINER_NAME}'..."
  docker run -d \
    --name "${CONTAINER_NAME}" \
    --network "${NETWORK_NAME}" \
    -e POSTGRES_USER="${DB_USER}" \
    -e POSTGRES_PASSWORD="${DB_PASS}" \
    -e POSTGRES_DB="${DB_NAME}" \
    -p "${DB_PORT}:5432" \
    postgres:16-alpine
fi

# Ensure Postgres is attached to the shared network (no-op if already attached).
docker network connect "${NETWORK_NAME}" "${CONTAINER_NAME}" 2>/dev/null || true

# ── Start Adminer (web DB viewer) if needed ───────────────────────────────────
if docker ps --format '{{.Names}}' | grep -q "^${ADMINER_NAME}$"; then
  echo "[dev] Adminer container '${ADMINER_NAME}' already running."
elif docker ps -a --format '{{.Names}}' | grep -q "^${ADMINER_NAME}$"; then
  echo "[dev] Starting existing container '${ADMINER_NAME}'..."
  docker start "${ADMINER_NAME}"
else
  echo "[dev] Creating Adminer container '${ADMINER_NAME}'..."
  docker run -d \
    --name "${ADMINER_NAME}" \
    --network "${NETWORK_NAME}" \
    -e ADMINER_DEFAULT_SERVER="${CONTAINER_NAME}" \
    -p "${ADMINER_PORT}:8080" \
    adminer:latest
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
echo "[dev] Adminer (DB viewer) at http://localhost:${ADMINER_PORT}"
echo "[dev]   → System: PostgreSQL | Server: ${CONTAINER_NAME} | User: ${DB_USER} | Password: ${DB_PASS} | Database: ${DB_NAME}"
echo "[dev] Starting API server at http://localhost:8000 ..."

# Prefer a project virtualenv if present, else fall back to uvicorn on PATH.
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
if [ -x "${REPO_ROOT}/.venv/bin/uvicorn" ]; then
  exec "${REPO_ROOT}/.venv/bin/uvicorn" app.main:app --reload --host 0.0.0.0 --port 8000
elif command -v uvicorn &>/dev/null; then
  exec uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
else
  echo "ERROR: uvicorn not found. Install deps (pip install -r requirements.txt) or create a .venv." >&2
  exit 1
fi
