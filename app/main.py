import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import init_db
from app.api.routes import router

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(
    title="HouseDreamer API",
    description="台灣房市分析平台 — 整合實價登錄、591、永慶、信義、住商資料",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api/v1")


@app.get("/")
async def root():
    return {
        "service": "HouseDreamer",
        "description": "台灣房市分析平台",
        "docs": "/docs",
        "api": "/api/v1",
    }


@app.get("/health")
async def health():
    return {"status": "ok"}
