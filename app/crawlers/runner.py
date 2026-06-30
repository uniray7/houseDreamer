import logging
from typing import Type

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.crawlers.base import BaseCrawler
from app.crawlers.lvr_land import LvrLandCrawler
from app.crawlers.house591 import House591Crawler
from app.crawlers.yungching import YungchingCrawler
from app.crawlers.sinyi import SinyiCrawler
from app.crawlers.chunghua import ChunghuaCrawler
from app.database import AsyncSessionLocal
from app.models import Listing

logger = logging.getLogger(__name__)

ALL_CRAWLERS: list[Type[BaseCrawler]] = [
    LvrLandCrawler,
    House591Crawler,
    YungchingCrawler,
    SinyiCrawler,
    ChunghuaCrawler,
]


async def run_crawler(crawler_class: Type[BaseCrawler], **kwargs) -> int:
    count = 0
    async with crawler_class(**kwargs) as crawler:
        async for record in crawler.crawl():
            async with AsyncSessionLocal() as session:
                await _upsert(session, record)
                count += 1
            if count % 100 == 0:
                logger.info(f"[{crawler.name}] saved {count} records")
    logger.info(f"[{crawler_class.name}] total: {count}")
    return count


async def _upsert(session: AsyncSession, data: dict):
    source = data.get("source")
    source_id = data.get("source_id")
    existing = None
    if source_id:
        result = await session.execute(
            select(Listing).where(
                Listing.source == source,
                Listing.source_id == source_id,
            )
        )
        existing = result.scalar_one_or_none()

    if existing:
        for k, v in data.items():
            if hasattr(existing, k) and v is not None:
                setattr(existing, k, v)
    else:
        session.add(Listing(**data))
    await session.commit()


async def run_all_crawlers():
    total = 0
    for crawler_class in ALL_CRAWLERS:
        try:
            count = await run_crawler(crawler_class)
            total += count
        except Exception as e:
            logger.error(f"{crawler_class.name} failed: {e}")
    logger.info(f"All crawlers done. Total records: {total}")
    return total
