#!/usr/bin/env bash
# Start local Postgres via Docker Compose, then launch the API server.
set -euo pipefail

DB_USER="housedreamer"
DB_PASS="housedreamer"
DB_NAME="housedreamer"
DB_HOST="localhost"
DB_PORT="5432"
DATABASE_URL="postgresql+asyncpg://${DB_USER}:${DB_PASS}@${DB_HOST}:${DB_PORT}/${DB_NAME}"

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# ── Docker / Compose check ────────────────────────────────────────────────────
if ! command -v docker &>/dev/null; then
  echo "ERROR: docker is not installed or not in PATH." >&2
  exit 1
fi

# ── Start Postgres ────────────────────────────────────────────────────────────
echo "[dev] Starting Postgres via Docker Compose..."
docker compose -f "${REPO_ROOT}/docker-compose.yml" up -d postgres

# ── Wait for Postgres to be healthy ──────────────────────────────────────────
echo "[dev] Waiting for Postgres to be ready..."
for i in $(seq 1 30); do
  if docker compose -f "${REPO_ROOT}/docker-compose.yml" exec -T postgres \
      pg_isready -U "${DB_USER}" -d "${DB_NAME}" &>/dev/null; then
    echo "[dev] Postgres is ready."
    break
  fi
  if [ "$i" -eq 30 ]; then
    echo "ERROR: Postgres did not become ready in time." >&2
    exit 1
  fi
  sleep 1
done

# ── DBeaver connection info ───────────────────────────────────────────────────
echo ""
echo "┌─────────────────────────────────────────────────┐"
echo "│         DBeaver Connection Settings             │"
echo "├─────────────────────────────────────────────────┤"
echo "│  Type    : PostgreSQL                           │"
echo "│  Host    : ${DB_HOST}                                │"
echo "│  Port    : ${DB_PORT}                                 │"
echo "│  Database: ${DB_NAME}                        │"
echo "│  Username: ${DB_USER}                        │"
echo "│  Password: ${DB_PASS}                        │"
echo "└─────────────────────────────────────────────────┘"
echo ""

# ── Launch API ────────────────────────────────────────────────────────────────
export DATABASE_URL="${DATABASE_URL}"
echo "[dev] Starting API server at http://localhost:8000 (docs: http://localhost:8000/docs)"
exec uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
