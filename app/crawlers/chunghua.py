"""
住商不動產 crawler - https://www.chunghua.com.tw
"""

import logging
from typing import AsyncIterator

from bs4 import BeautifulSoup

from app.crawlers.base import BaseCrawler

logger = logging.getLogger(__name__)

SEARCH_URL = "https://www.chunghua.com.tw/buy/list"

CITIES = [
    ("taipei", "台北市"),
    ("newtaipei", "新北市"),
    ("taoyuan", "桃園市"),
    ("taichung", "台中市"),
    ("tainan", "台南市"),
    ("kaohsiung", "高雄市"),
    ("hsinchu", "新竹市"),
]


class ChunghuaCrawler(BaseCrawler):
    name = "chunghua"

    def __init__(self, max_pages: int = 5):
        super().__init__()
        self.max_pages = max_pages

    async def _fetch_page(self, city: str, city_name: str, page: int) -> list[dict]:
        params = {"city": city, "page": page}
        try:
            resp = await self.get(SEARCH_URL, params=params)
            soup = BeautifulSoup(resp.text, "lxml")
            return self._parse_list(soup, city_name)
        except Exception as e:
            logger.warning(f"住商 {city_name} page {page} failed: {e}")
            return []

    def _parse_list(self, soup: BeautifulSoup, city_name: str) -> list[dict]:
        results = []
        cards = soup.select(
            "div.house-list-item, li.item, article, div[class*='house'], div[class*='item']"
        )
        for card in cards:
            try:
                record = self._parse_card(card, city_name)
                if record:
                    results.append(record)
            except Exception as e:
                logger.debug(f"住商 card parse error: {e}")
        return results

    def _parse_card(self, card, city_name: str) -> dict | None:
        title_el = card.select_one("h3, h2, .title, [class*='title']")
        price_el = card.select_one(".price, [class*='price']")
        area_el = card.select_one("[class*='area'], [class*='ping']")
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
            url = "https://www.chunghua.com.tw" + url

        district = self._extract_district(city_name, address or title)
        unit_price = round(price * 10000 / area_ping, 0) if price and area_ping else None

        return {
            "source": "chunghua",
            "source_id": url.split("/")[-1] if url else "",
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
        m = re.search(r"([\d,]+\.?\d*)", text.replace(",", ""))
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
        for city, city_name in CITIES:
            logger.info(f"Crawling 住商不動產 {city_name}...")
            for page in range(1, self.max_pages + 1):
                records = await self._fetch_page(city, city_name, page)
                if not records:
                    break
                for r in records:
                    yield r
