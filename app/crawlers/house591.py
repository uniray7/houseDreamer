"""
591房屋交易 crawler
"""

import logging
from typing import AsyncIterator

from app.crawlers.base import BaseCrawler

logger = logging.getLogger(__name__)

SEARCH_API = "https://sale.591.com.tw/home/search/getSaleList"

REGION_MAP = {
    1: "台北市",
    3: "台中市",
    4: "基隆市",
    5: "台南市",
    6: "高雄市",
    7: "新北市",
    10: "桃園市",
    11: "新竹市",
    12: "苗栗縣",
    13: "彰化縣",
    14: "南投縣",
    15: "雲林縣",
    17: "嘉義市",
    19: "屏東縣",
    21: "宜蘭縣",
    22: "花蓮縣",
    23: "台東縣",
}


class House591Crawler(BaseCrawler):
    name = "house591"

    def __init__(self, region_ids: list[int] | None = None, max_pages: int = 5):
        super().__init__()
        self.region_ids = region_ids or list(REGION_MAP.keys())
        self.max_pages = max_pages

    async def _get_token(self) -> str:
        resp = await self.get("https://sale.591.com.tw/")
        import re
        match = re.search(r'csrf-token"\s+content="([^"]+)"', resp.text)
        return match.group(1) if match else ""

    async def _fetch_page(self, region_id: int, page: int, token: str) -> dict:
        params = {
            "type": 2,
            "regionid": region_id,
            "firstRow": page * 30,
            "totalRows": 30,
        }
        headers = {"X-CSRF-TOKEN": token, "Referer": "https://sale.591.com.tw/"}
        try:
            resp = await self.get(SEARCH_API, params=params, headers=headers)
            return resp.json()
        except Exception as e:
            logger.warning(f"591 page fetch failed region={region_id} page={page}: {e}")
            return {}

    def _parse_item(self, item: dict, region_name: str) -> dict:
        def _float(v) -> float | None:
            try:
                return float(str(v).replace(",", "").strip())
            except (ValueError, TypeError):
                return None

        price = _float(item.get("price", ""))
        area_ping = _float(item.get("area", ""))
        unit_price = round(price / area_ping * 10000, 0) if price and area_ping else None
        house_id = item.get("houseid", "")
        url = f"https://sale.591.com.tw/home/house/detail/2/{house_id}.html" if house_id else None

        return {
            "source": "house591",
            "source_id": str(house_id),
            "title": item.get("fulladdress", item.get("address", "")),
            "property_type": self._map_type(item.get("kind_name", "")),
            "county": region_name,
            "district": item.get("section_str", ""),
            "address": item.get("fulladdress", ""),
            "price": price,
            "unit_price": unit_price,
            "area_ping": area_ping,
            "floor": item.get("floor_str", ""),
            "total_floors": None,
            "rooms": None,
            "age": _float(item.get("houseage", "")),
            "url": url,
            "description": item.get("desc", ""),
            "trade_date": None,
        }

    def _map_type(self, raw: str) -> str:
        if "公寓" in raw or "大樓" in raw or "華廈" in raw:
            return "apartment"
        if "透天" in raw or "別墅" in raw:
            return "house"
        if "土地" in raw:
            return "land"
        if "辦公" in raw:
            return "office"
        return "other"

    async def crawl(self) -> AsyncIterator[dict]:
        try:
            token = await self._get_token()
        except Exception as e:
            logger.warning(f"Could not get 591 token: {e}")
            token = ""

        for region_id in self.region_ids:
            region_name = REGION_MAP.get(region_id, str(region_id))
            logger.info(f"Crawling 591 {region_name}...")
            for page in range(self.max_pages):
                data = await self._fetch_page(region_id, page, token)
                items = data.get("data", {}).get("house_list", [])
                if not items:
                    break
                for item in items:
                    yield self._parse_item(item, region_name)
