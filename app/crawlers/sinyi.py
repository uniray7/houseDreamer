"""
信義房屋 crawler - https://www.sinyi.com.tw
"""

import logging
from typing import AsyncIterator

from bs4 import BeautifulSoup

from app.crawlers.base import BaseCrawler

logger = logging.getLogger(__name__)

SEARCH_URL = "https://www.sinyi.com.tw/buy/list/Taipei-city/0-price/desc/1/"
API_URL = "https://www.sinyi.com.tw/api/buyhouse/list"

CITIES = [
    ("taipei", "台北市"),
    ("new-taipei", "新北市"),
    ("taoyuan", "桃園市"),
    ("taichung", "台中市"),
    ("tainan", "台南市"),
    ("kaohsiung", "高雄市"),
    ("hsinchu-city", "新竹市"),
]


class SinyiCrawler(BaseCrawler):
    name = "sinyi"

    def __init__(self, max_pages: int = 5):
        super().__init__()
        self.max_pages = max_pages

    async def _fetch_page(self, city_slug: str, city_name: str, page: int) -> list[dict]:
        url = f"https://www.sinyi.com.tw/buy/list/{city_slug}-city/0-price/desc/{page}/"
        try:
            resp = await self.get(url)
            soup = BeautifulSoup(resp.text, "lxml")
            return self._parse_list(soup, city_name)
        except Exception as e:
            logger.warning(f"信義 {city_name} page {page} failed: {e}")
            return []

    def _parse_list(self, soup: BeautifulSoup, city_name: str) -> list[dict]:
        results = []
        cards = soup.select("div.buy-list-item, li.buy-item, div[class*='house-item']")
        if not cards:
            cards = soup.select("div[class*='item']")
        for card in cards:
            try:
                record = self._parse_card(card, city_name)
                if record:
                    results.append(record)
            except Exception as e:
                logger.debug(f"Sinyi card parse error: {e}")
        return results

    def _parse_card(self, card, city_name: str) -> dict | None:
        title_el = card.select_one("h3, h2, .title, [class*='title']")
        price_el = card.select_one(".price, [class*='price']")
        area_el = card.select_one("[class*='area'], [class*='ping']")
        link_el = card.select_one("a[href]")
        addr_el = card.select_one("[class*='addr'], [class*='address']")

        title = title_el.get_text(strip=True) if title_el else ""
        if not title:
            return None

        price_text = price_el.get_text(strip=True) if price_el else ""
        price = self._parse_price(price_text)
        area_text = area_el.get_text(strip=True) if area_el else ""
        area_ping = self._parse_area(area_text)
        address = addr_el.get_text(strip=True) if addr_el else ""

        url = link_el["href"] if link_el else ""
        if url and not url.startswith("http"):
            url = "https://www.sinyi.com.tw" + url

        district = self._extract_district(city_name, address or title)

        unit_price = None
        if price and area_ping and area_ping > 0:
            unit_price = round(price * 10000 / area_ping, 0)

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
            "trade_date": None,
        }

    def _parse_price(self, text: str) -> float | None:
        import re
        clean = text.replace(",", "")
        m = re.search(r"([\d.]+)", clean)
        if not m:
            return None
        val = float(m.group(1))
        if "億" in text:
            val *= 10000
        return val

    def _parse_area(self, text: str) -> float | None:
        import re
        m = re.search(r"([\d.]+)", text)
        return float(m.group(1)) if m else None

    def _extract_district(self, city_name: str, text: str) -> str:
        import re
        m = re.search(rf"{city_name}(.{{2,4}}[區鄉鎮市])", text)
        return m.group(1) if m else ""

    async def crawl(self) -> AsyncIterator[dict]:
        for city_slug, city_name in CITIES:
            logger.info(f"Crawling 信義房屋 {city_name}...")
            for page in range(1, self.max_pages + 1):
                records = await self._fetch_page(city_slug, city_name, page)
                if not records:
                    break
                for r in records:
                    yield r
