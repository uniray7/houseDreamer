# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Start Postgres container + API server in one command (requires Docker)
./scripts/dev.sh

# Start API server only (if Postgres is already running)
uvicorn app.main:app --reload

# Run all crawlers
python scripts/run_crawlers.py

# Run a single crawler (lvr_land | house591 | yungching | sinyi | chunghua)
python scripts/run_crawlers.py lvr_land

# Trigger crawl via API (after server is running)
curl -X POST "http://localhost:8000/api/v1/crawl?source=lvr_land"
```

## Environment

Copy `.env.example` to `.env` and set `DATABASE_URL`. Defaults to a local SQLite file (`housedreamer.db`) if not set, so the app works out of the box without Postgres for local dev.

Railway production uses `DATABASE_URL` pointing to its managed PostgreSQL. The `database.py` helper auto-rewrites `postgresql://` → `postgresql+asyncpg://` for async compatibility.

## Architecture

**FastAPI + async SQLAlchemy** — all DB operations are `async`/`await`. The engine and session factory live in `app/database.py` and are shared across the app. `init_db()` runs at startup (via lifespan) to create tables.

**Single model** (`app/models.py`) — `Listing` stores normalised property data from all sources. Fields like `price` (萬元), `unit_price` (元/坪), `area_ping` (坪) are stored in consistent units regardless of what each source provides.

**Crawler pattern** — every crawler extends `BaseCrawler` (`app/crawlers/base.py`), which wraps `httpx.AsyncClient` with a configurable delay (`CRAWLER_DELAY` env var, default 2s). Each crawler implements `async def crawl(self) -> AsyncIterator[dict]` and yields normalised dicts matching the `Listing` fields.

Data sources and their approach:
- `lvr_land` — downloads ZIP files from the government open-data API, parses CSV. Converts ROC dates (民國) to Gregorian, sqm to 坪.
- `house591` — fetches a CSRF token from the homepage first, then calls the JSON search API with it.
- `yungching`, `sinyi`, `chunghua` — HTML scraping with BeautifulSoup; selectors may need updating if sites change their markup.

**Runner** (`app/crawlers/runner.py`) — `run_crawler(crawler_class)` streams records from a crawler and upserts each one by `(source, source_id)`. `run_all_crawlers()` runs every crawler sequentially.

**API** (`app/api/routes.py`) — `POST /api/v1/crawl` launches crawlers as FastAPI background tasks. `GET /api/v1/listings` supports filtering by source, county, district, property_type, price range, area range, with pagination. `GET /api/v1/stats` returns aggregated averages by county.

## Git Workflow

All changes go through PRs — never push directly to `main`.
