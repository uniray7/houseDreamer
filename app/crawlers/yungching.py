"""
永慶房屋 crawler - https://buy.yungching.com.tw
Uses Playwright for JavaScript-rendered pages.
"""

import logging
import re
from typing import AsyncIterator

from app.crawlers.base import BaseCrawler, playwright_page

logger = logging.getLogger(__name__)

# buy.yungching.com.tw uses Chinese city names in URL
CITIES = [
    ("台北市", "台北市"),
    ("新北市", "新北市"),
    ("桃園市", "桃園市"),
    ("台中市", "台中市"),
    ("台南市", "台南市"),
    ("高雄市", "高雄市"),
    ("新竹市", "新竹市"),
]


class YungchingCrawler(BaseCrawler):
    name = "yungching"

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
        elif "千萬" in text:
            val *= 1000
        return val

    def _parse_area(self, text: str) -> float | None:
        m = re.search(r"([\d.]+)", text)
        return float(m.group(1)) if m else None

    def _extract_location(self, text: str) -> tuple[str, str]:
        counties = ["台北市", "新北市", "桃園市", "台中市", "台南市", "高雄市",
                    "新竹市", "基隆市", "嘉義市", "新竹縣", "苗栗縣", "彰化縣",
                    "南投縣", "雲林縣", "嘉義縣", "屏東縣", "宜蘭縣", "花蓮縣",
                    "台東縣", "澎湖縣", "金門縣", "連江縣"]
        county = next((c for c in counties if c in text), "")
        district = ""
        if county:
            m = re.search(rf"{county}(.{{2,4}}[區鄉鎮市])", text)
            if m:
                district = m.group(1)
        return county, district

    async def _fetch_page(self, city: str, city_name: str, page: int) -> list[dict]:
        # URL format: /list/台北市-_c?pg=2
        url = f"https://buy.yungching.com.tw/list/{city}-_c"
        if page > 1:
            url += f"?pg={page}"
        try:
            async with playwright_page() as pw_page:
                await pw_page.goto(url, wait_until="networkidle", timeout=30000)
                content = await pw_page.content()

            from bs4 import BeautifulSoup
            soup = BeautifulSoup(content, "lxml")
            return self._parse_list_page(soup, city_name)
        except Exception as e:
            logger.warning(f"永慶 {city_name} page {page} failed: {e}")
            return []

    def _parse_list_page(self, soup, city_name: str) -> list[dict]:
        results = []
        # 永慶 uses React; look for house card elements
        cards = soup.select(
            "li.m-list-item, div.house-card, div[class*='HouseCard'], "
            "li[class*='list-item'], article[class*='house']"
        )
        if not cards:
            cards = soup.select("li[class*='item'], div[class*='item']")
        for card in cards:
            try:
                record = self._parse_card(card, city_name)
                if record:
                    results.append(record)
            except Exception as e:
                logger.debug(f"永慶 card parse error: {e}")
        return results

    def _parse_card(self, card, city_name: str) -> dict | None:
        title_el = card.select_one("h3, h2, .house-title, [class*='title'], [class*='name']")
        price_el = card.select_one(".price, [class*='price'], [class*='Price']")
        area_el = card.select_one("[class*='area'], [class*='Area'], [class*='ping'], [class*='size']")
        addr_el = card.select_one("[class*='addr'], [class*='Addr'], [class*='address'], [class*='location']")
        link_el = card.select_one("a[href]")

        title = title_el.get_text(strip=True) if title_el else ""
        if not title:
            return None

        price = self._parse_price(price_el.get_text(strip=True) if price_el else "")
        area_ping = self._parse_area(area_el.get_text(strip=True) if area_el else "")
        address = addr_el.get_text(strip=True) if addr_el else ""
        url = link_el["href"] if link_el else ""
        if url and not url.startswith("http"):
            url = "https://buy.yungching.com.tw" + url

        county, district = self._extract_location(address or title or city_name)
        if not county:
            county = city_name
        unit_price = round(price * 10000 / area_ping, 0) if price and area_ping else None

        return {
            "source": "yungching",
            "source_id": url.split("/")[-1].split("?")[0] if url else "",
            "title": title,
            "property_type": "apartment",
            "county": county,
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
        logger.info("Crawling 永慶房屋...")
        for city, city_name in CITIES:
            logger.info(f"  city: {city_name}")
            for page in range(1, self.max_pages + 1):
                records = await self._fetch_page(city, city_name, page)
                if not records:
                    break
                for r in records:
                    yield r
