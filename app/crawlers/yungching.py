"""
永慶房屋 crawler - https://www.yungching.com.tw
"""

import logging
from typing import AsyncIterator

from bs4 import BeautifulSoup

from app.crawlers.base import BaseCrawler

logger = logging.getLogger(__name__)

SEARCH_URL = "https://www.yungching.com.tw/buy/list/"


class YungchingCrawler(BaseCrawler):
    name = "yungching"

    def __init__(self, max_pages: int = 5):
        super().__init__()
        self.max_pages = max_pages

    async def _fetch_page(self, page: int) -> list[dict]:
        params = {"pg": page, "orderby": "new"}
        try:
            resp = await self.get(SEARCH_URL, params=params)
            soup = BeautifulSoup(resp.text, "lxml")
            return self._parse_list_page(soup)
        except Exception as e:
            logger.warning(f"永慶 page {page} failed: {e}")
            return []

    def _parse_list_page(self, soup: BeautifulSoup) -> list[dict]:
        results = []
        cards = soup.select("li.item, div.house-item, article.list-item, div[class*='house']")
        if not cards:
            cards = soup.select("li[class*='item']")
        for card in cards:
            try:
                record = self._parse_card(card)
                if record:
                    results.append(record)
            except Exception as e:
                logger.debug(f"Card parse error: {e}")
        return results

    def _parse_card(self, card) -> dict | None:
        title_el = card.select_one("h3, .title, [class*='title']")
        price_el = card.select_one(".price, [class*='price']")
        area_el = card.select_one(".area, [class*='area'], [class*='ping']")
        addr_el = card.select_one(".address, [class*='addr']")
        link_el = card.select_one("a[href]")

        title = title_el.get_text(strip=True) if title_el else ""
        if not title:
            return None

        price = self._parse_price(price_el.get_text(strip=True) if price_el else "")
        area_ping = self._parse_area(area_el.get_text(strip=True) if area_el else "")
        address = addr_el.get_text(strip=True) if addr_el else ""
        url = link_el["href"] if link_el else ""
        if url and not url.startswith("http"):
            url = "https://www.yungching.com.tw" + url

        county, district = self._extract_location(address or title)
        unit_price = round(price * 10000 / area_ping, 0) if price and area_ping else None

        return {
            "source": "yungching",
            "source_id": url.split("/")[-1] if url else "",
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
        elif "千萬" in text:
            val *= 1000
        return val

    def _parse_area(self, text: str) -> float | None:
        import re
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
            import re
            m = re.search(rf"{county}(.{{2,4}}[區鄉鎮市])", text)
            if m:
                district = m.group(1)
        return county, district

    async def crawl(self) -> AsyncIterator[dict]:
        logger.info("Crawling 永慶房屋...")
        for page in range(1, self.max_pages + 1):
            records = await self._fetch_page(page)
            if not records:
                break
            for r in records:
                yield r
