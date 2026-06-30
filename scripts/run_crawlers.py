"""
CLI entry point to trigger crawlers manually.

Usage:
  python scripts/run_crawlers.py              # run all
  python scripts/run_crawlers.py lvr_land     # run one
"""

import asyncio
import sys
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


async def main():
    from app.database import init_db
    from app.crawlers.runner import run_all_crawlers, run_crawler, ALL_CRAWLERS

    await init_db()

    if len(sys.argv) > 1:
        name = sys.argv[1]
        crawler_map = {c.name: c for c in ALL_CRAWLERS}
        if name not in crawler_map:
            print(f"Unknown crawler '{name}'. Available: {list(crawler_map)}")
            sys.exit(1)
        await run_crawler(crawler_map[name])
    else:
        await run_all_crawlers()


if __name__ == "__main__":
    asyncio.run(main())
