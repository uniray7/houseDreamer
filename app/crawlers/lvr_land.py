"""
實價登錄 (LVR Land) crawler
Government open data: https://plvr.land.moi.gov.tw/DownloadOpenData
"""

import csv
import io
import logging
import zipfile
from typing import AsyncIterator

from app.crawlers.base import BaseCrawler

logger = logging.getLogger(__name__)

OPEN_DATA_BASE = "https://plvr.land.moi.gov.tw/DownloadSeason"

CITY_CODES = {
    "A": "台北市",
    "B": "台中市",
    "C": "基隆市",
    "D": "台南市",
    "E": "高雄市",
    "F": "新北市",
    "G": "宜蘭縣",
    "H": "桃園市",
    "I": "嘉義市",
    "J": "新竹縣",
    "K": "苗栗縣",
    "M": "南投縣",
    "N": "彰化縣",
    "O": "新竹市",
    "P": "雲林縣",
    "Q": "嘉義縣",
    "T": "屏東縣",
    "U": "花蓮縣",
    "V": "台東縣",
    "W": "金門縣",
    "X": "澎湖縣",
    "Z": "連江縣",
}


class LvrLandCrawler(BaseCrawler):
    name = "lvr_land"

    def __init__(self, year: int = 113, season: int = 1):
        super().__init__()
        self.year = year
        self.season = season

    def _build_url(self, city_code: str) -> str:
        return (
            f"{OPEN_DATA_BASE}?season={self.year}S{self.season}"
            f"&type=ZIP&token=&fileName={city_code}_lvr_land_A.zip"
        )

    async def _fetch_city(self, city_code: str, city_name: str) -> AsyncIterator[dict]:
        url = self._build_url(city_code)
        try:
            resp = await self.get(url)
        except Exception as e:
            logger.warning(f"Failed to fetch {city_name}: {e}")
            return

        try:
            with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
                for name in zf.namelist():
                    if not name.endswith(".csv"):
                        continue
                    with zf.open(name) as f:
                        content = f.read().decode("utf-8-sig", errors="replace")
                        reader = csv.DictReader(io.StringIO(content))
                        rows = list(reader)
                        for row in rows[1:]:
                            yield self._parse_row(row, city_name)
        except zipfile.BadZipFile:
            logger.warning(f"Bad zip for {city_name}")

    def _parse_row(self, row: dict, city_name: str) -> dict:
        def _float(v: str) -> float | None:
            try:
                return float(v.replace(",", "").strip())
            except (ValueError, AttributeError):
                return None

        def _int(v: str) -> int | None:
            try:
                return int(v.replace(",", "").strip())
            except (ValueError, AttributeError):
                return None

        area_sqm = _float(row.get("建物移轉總面積平方公尺", ""))
        area_ping = round(area_sqm / 3.30579, 2) if area_sqm else None

        total_price = _float(row.get("總價元", ""))
        price_wan = round(total_price / 10000, 2) if total_price else None

        unit_price_sqm = _float(row.get("單價元平方公尺", ""))
        unit_price_ping = round(unit_price_sqm * 3.30579, 0) if unit_price_sqm else None

        trade_date_str = row.get("交易年月日", "")
        trade_date = None
        if trade_date_str and len(trade_date_str) == 7:
            try:
                from datetime import datetime
                roc_year = int(trade_date_str[:3])
                month = int(trade_date_str[3:5])
                day = int(trade_date_str[5:7])
                trade_date = datetime(roc_year + 1911, month, day)
            except Exception:
                pass

        return {
            "source": "lvr_land",
            "source_id": row.get("編號", ""),
            "title": f"{city_name}{row.get('鄉鎮市區', '')} {row.get('建物型態', '')}",
            "property_type": self._map_type(row.get("建物型態", "")),
            "county": city_name,
            "district": row.get("鄉鎮市區", ""),
            "address": row.get("土地位置建物門牌", ""),
            "price": price_wan,
            "unit_price": unit_price_ping,
            "area_ping": area_ping,
            "floor": row.get("移轉層次", ""),
            "total_floors": _int(row.get("總樓層數", "")),
            "rooms": _int(row.get("建物現況格局-房", "")),
            "age": None,
            "url": None,
            "description": row.get("備註", ""),
            "trade_date": trade_date,
        }

    def _map_type(self, raw: str) -> str:
        if "公寓" in raw or "大樓" in raw or "華廈" in raw:
            return "apartment"
        if "透天" in raw or "別墅" in raw:
            return "house"
        if "土地" in raw:
            return "land"
        if "辦公" in raw or "商業" in raw:
            return "office"
        return "other"

    async def crawl(self) -> AsyncIterator[dict]:
        for code, name in CITY_CODES.items():
            logger.info(f"Crawling 實價登錄 {name}...")
            async for record in self._fetch_city(code, name):
                yield record
