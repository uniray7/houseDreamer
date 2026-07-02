"""
信義房屋 crawler - https://www.sinyi.com.tw
Uses Playwright for JavaScript-rendered pages.
"""

import logging
import re
from typing import AsyncIterator

from app.crawlers.base import BaseCrawler, playwright_page

logger = logging.getLogger(__name__)

# sinyi uses Title-Case city slugs
CITIES = [
    ("Taipei-city", "台北市"),
    ("New-Taipei-city", "新北市"),
    ("Taoyuan-city", "桃園市"),
    ("Taichung-city", "台中市"),
    ("Tainan-city", "台南市"),
    ("Kaohsiung-city", "高雄市"),
    ("Hsinchu-city", "新竹市"),
]


class SinyiCrawler(BaseCrawler):
    name = "sinyi"

    def __init__(self, max_pages: int = 5):
        super().__init__()
        self.max_pages = max_pages

    def _parse_price(self, text: str) -> float | None:
        text = text.replace(",", "")
        m = re.search(r"([\d.]+)", text)
        if not m:
            return None
        val = float(m.group(1))
        if "億" in text:
            val *= 10000
        return val

    def _parse_area(self, text: str) -> float | None:
        m = re.search(r"([\d.]+)", text)
        return float(m.group(1)) if m else None

    def _extract_district(self, city_name: str, text: str) -> str:
        m = re.search(rf"{city_name}(.{{2,4}}[區鄉鎮市])", text)
        return m.group(1) if m else ""

    async def _fetch_page(self, city_slug: str, city_name: str, page: int) -> list[dict]:
        url = f"https://www.sinyi.com.tw/buy/list/{city_slug}/0-price/desc/{page}/"
        try:
            async with playwright_page() as pw_page:
                await pw_page.goto(url, wait_until="networkidle", timeout=30000)
                content = await pw_page.content()

            from bs4 import BeautifulSoup
            soup = BeautifulSoup(content, "lxml")
            return self._parse_list(soup, city_name)
        except Exception as e:
            logger.warning(f"信義 {city_name} page {page} failed: {e}")
            return []

    def _parse_list(self, soup, city_name: str) -> list[dict]:
        results = []
        # sinyi uses li elements inside a buy-list container
        cards = soup.select("li.buy-list-item, div.buy-list-item, li[class*='item']")
        if not cards:
            # fallback: any card-like container with a price element
            cards = soup.select("div[class*='house'], article[class*='house']")
        for card in cards:
            try:
                record = self._parse_card(card, city_name)
                if record:
                    results.append(record)
            except Exception as e:
                logger.debug(f"信義 card parse error: {e}")
        return results

    def _parse_card(self, card, city_name: str) -> dict | None:
        title_el = card.select_one("h3, h2, .house-title, [class*='title']")
        price_el = card.select_one(".price, .house-price, [class*='price']")
        area_el = card.select_one("[class*='area'], [class*='ping'], [class*='size']")
        link_el = card.select_one("a[href]")
        addr_el = card.select_one("[class*='addr'], [class*='address'], [class*='location']")

        title = title_el.get_text(strip=True) if title_el else ""
        if not title:
            return None

        price = self._parse_price(price_el.get_text(strip=True) if price_el else "")
        area_ping = self._parse_area(area_el.get_text(strip=True) if area_el else "")
        address = addr_el.get_text(strip=True) if addr_el else ""
        url = link_el["href"] if link_el else ""
        if url and not url.startswith("http"):
            url = "https://www.sinyi.com.tw" + url

        district = self._extract_district(city_name, address or title)
        unit_price = round(price * 10000 / area_ping, 0) if price and area_ping else None

        return {
            "source": "sinyi",
            "source_id": url.split("/")[-2] if url else "",
            "title": title,
            "property_type": "apartment",
            "county": city_name,
            "district": district,
            "address": address,
            "price": price,
            "unit_price": unit_price,
            "area_ping": area_ping,
            "floor": "",
            "total_floors": None,
            "rooms": None,
            "age": None,
            "url": url,
            "description": "",
        }

    async def crawl(self) -> AsyncIterator[dict]:
        for city_slug, city_name in CITIES:
            logger.info(f"Crawling 信義房屋 {city_name}...")
            for page in range(1, self.max_pages + 1):
                records = await self._fetch_page(city_slug, city_name, page)
                if not records:
                    break
                for r in records:
                    yield r
