import asyncio
import logging
from abc import ABC, abstractmethod
from typing import AsyncIterator

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "zh-TW,zh;q=0.9,en;q=0.8",
}


class BaseCrawler(ABC):
    name: str = "base"

    def __init__(self):
        self.client = httpx.AsyncClient(
            headers=HEADERS,
            timeout=30.0,
            follow_redirects=True,
        )

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        await self.client.aclose()

    async def get(self, url: str, **kwargs) -> httpx.Response:
        await asyncio.sleep(settings.crawler_delay)
        r = await self.client.get(url, **kwargs)
        r.raise_for_status()
        return r

    async def post(self, url: str, **kwargs) -> httpx.Response:
        await asyncio.sleep(settings.crawler_delay)
        r = await self.client.post(url, **kwargs)
        r.raise_for_status()
        return r

    @abstractmethod
    async def crawl(self) -> AsyncIterator[dict]:
        ...
