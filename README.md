# HouseDreamer

台灣房市分析平台，整合多個房屋資料來源，提供統一 API 查詢。

## 資料來源

| 來源 | 說明 | 類型 |
|------|------|------|
| 實價登錄 (lvr_land) | 內政部實價登錄開放資料 | 成交紀錄 |
| 591房屋 (house591) | 591.com.tw 買賣物件 | 待售物件 |
| 永慶房屋 (yungching) | yungching.com.tw 買賣物件 | 待售物件 |
| 信義房屋 (sinyi) | sinyi.com.tw 買賣物件 | 待售物件 |
| 住商不動產 (chunghua) | chunghua.com.tw 買賣物件 | 待售物件 |

## 架構

```
houseDreamer/
├── app/
│   ├── main.py           # FastAPI app
│   ├── config.py         # 設定
│   ├── database.py       # SQLAlchemy async
│   ├── models.py         # ORM models
│   ├── api/
│   │   └── routes.py     # REST endpoints
│   └── crawlers/
│       ├── base.py       # BaseCrawler
│       ├── lvr_land.py   # 實價登錄
│       ├── house591.py   # 591房屋
│       ├── yungching.py  # 永慶房屋
│       ├── sinyi.py      # 信義房屋
│       ├── chunghua.py   # 住商不動產
│       └── runner.py     # 統一執行器
├── scripts/
│   └── run_crawlers.py   # CLI trigger
├── railway.toml          # Railway 部署設定
└── requirements.txt
```

## 本地開發

```bash
pip install -r requirements.txt
cp .env.example .env
# 編輯 .env 設定 DATABASE_URL
uvicorn app.main:app --reload

# 執行爬蟲
python scripts/run_crawlers.py
python scripts/run_crawlers.py lvr_land
```

## API 端點

| Method | Path | 說明 |
|--------|------|------|
| GET | `/api/v1/listings` | 查詢物件列表 |
| GET | `/api/v1/listings/{id}` | 查詢單一物件 |
| GET | `/api/v1/stats` | 統計資料 |
| POST | `/api/v1/crawl` | 觸發爬蟲 |

## Railway 部署

1. 在 [Railway](https://railway.com/) 建立新專案
2. 連結此 GitHub repo
3. 新增 PostgreSQL 服務
4. 設定環境變數 `DATABASE_URL`
5. 部署後呼叫 `POST /api/v1/crawl`
