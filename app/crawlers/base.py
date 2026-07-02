import asyncio
import logging
from abc import ABC, abstractmethod
from contextlib import asynccontextmanager
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


@asynccontextmanager
async def playwright_page():
    """Async context manager that yields a Playwright page with a real Chromium browser."""
    from playwright.async_api import async_playwright
    import os

    chromium_path = os.environ.get("PLAYWRIGHT_CHROMIUM_PATH", "/opt/pw-browsers/chromium")

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            executable_path=chromium_path if os.path.exists(chromium_path) else None,
            args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage"],
        )
        context = await browser.new_context(
            user_agent=HEADERS["User-Agent"],
            locale="zh-TW",
            extra_http_headers={"Accept-Language": "zh-TW,zh;q=0.9,en;q=0.8"},
        )
        page = await context.new_page()
        try:
            yield page
        finally:
            await browser.close()


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
