from typing import Optional
from fastapi import APIRouter, Depends, Query, HTTPException, BackgroundTasks
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from datetime import datetime

from app.database import get_db
from app.models import Listing, Transaction

router = APIRouter()


class ListingOut(BaseModel):
    id: int
    source: str
    title: str
    property_type: str
    county: Optional[str]
    district: Optional[str]
    address: Optional[str]
    price: Optional[float]
    unit_price: Optional[float]
    area_ping: Optional[float]
    floor: Optional[str]
    rooms: Optional[int]
    age: Optional[float]
    url: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class TransactionOut(BaseModel):
    id: int
    source: str
    title: str
    property_type: str
    county: Optional[str]
    district: Optional[str]
    address: Optional[str]
    price: Optional[float]
    unit_price: Optional[float]
    area_ping: Optional[float]
    floor: Optional[str]
    rooms: Optional[int]
    age: Optional[float]
    trade_date: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True


class PaginatedListings(BaseModel):
    total: int
    page: int
    page_size: int
    items: list[ListingOut]


class PaginatedTransactions(BaseModel):
    total: int
    page: int
    page_size: int
    items: list[TransactionOut]


class Stats(BaseModel):
    total_listings: int
    total_transactions: int
    by_source: dict[str, int]
    avg_price_by_county: dict[str, float]
    avg_unit_price_by_county: dict[str, float]


def _apply_common_filters(q, model, county, district, property_type, min_price, max_price, min_area, max_area):
    if county:
        q = q.where(model.county == county)
    if district:
        q = q.where(model.district == district)
    if property_type:
        q = q.where(model.property_type == property_type)
    if min_price is not None:
        q = q.where(model.price >= min_price)
    if max_price is not None:
        q = q.where(model.price <= max_price)
    if min_area is not None:
        q = q.where(model.area_ping >= min_area)
    if max_area is not None:
        q = q.where(model.area_ping <= max_area)
    return q


@router.get("/listings", response_model=PaginatedListings)
async def list_listings(
    source: Optional[str] = Query(None),
    county: Optional[str] = Query(None),
    district: Optional[str] = Query(None),
    property_type: Optional[str] = Query(None),
    min_price: Optional[float] = Query(None),
    max_price: Optional[float] = Query(None),
    min_area: Optional[float] = Query(None),
    max_area: Optional[float] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    q = select(Listing)
    if source:
        q = q.where(Listing.source == source)
    q = _apply_common_filters(q, Listing, county, district, property_type, min_price, max_price, min_area, max_area)

    count_result = await db.execute(select(func.count()).select_from(q.subquery()))
    total = count_result.scalar_one()

    q = q.offset((page - 1) * page_size).limit(page_size).order_by(Listing.created_at.desc())
    result = await db.execute(q)
    items = result.scalars().all()

    return PaginatedListings(total=total, page=page, page_size=page_size, items=items)


@router.get("/listings/{listing_id}", response_model=ListingOut)
async def get_listing(listing_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Listing).where(Listing.id == listing_id))
    listing = result.scalar_one_or_none()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    return listing


@router.get("/transactions", response_model=PaginatedTransactions)
async def list_transactions(
    county: Optional[str] = Query(None),
    district: Optional[str] = Query(None),
    property_type: Optional[str] = Query(None),
    min_price: Optional[float] = Query(None),
    max_price: Optional[float] = Query(None),
    min_area: Optional[float] = Query(None),
    max_area: Optional[float] = Query(None),
    date_from: Optional[str] = Query(None, description="YYYY-MM-DD"),
    date_to: Optional[str] = Query(None, description="YYYY-MM-DD"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    q = select(Transaction)
    q = _apply_common_filters(q, Transaction, county, district, property_type, min_price, max_price, min_area, max_area)
    if date_from:
        q = q.where(Transaction.trade_date >= date_from)
    if date_to:
        q = q.where(Transaction.trade_date <= date_to)

    count_result = await db.execute(select(func.count()).select_from(q.subquery()))
    total = count_result.scalar_one()

    q = q.offset((page - 1) * page_size).limit(page_size).order_by(Transaction.trade_date.desc())
    result = await db.execute(q)
    items = result.scalars().all()

    return PaginatedTransactions(total=total, page=page, page_size=page_size, items=items)


@router.get("/transactions/{transaction_id}", response_model=TransactionOut)
async def get_transaction(transaction_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Transaction).where(Transaction.id == transaction_id))
    txn = result.scalar_one_or_none()
    if not txn:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return txn


@router.get("/stats", response_model=Stats)
async def get_stats(db: AsyncSession = Depends(get_db)):
    total_listings_result = await db.execute(select(func.count(Listing.id)))
    total_listings = total_listings_result.scalar_one()

    total_txn_result = await db.execute(select(func.count(Transaction.id)))
    total_transactions = total_txn_result.scalar_one()

    by_source: dict[str, int] = {}
    for source_result, model in [
        (await db.execute(select(Listing.source, func.count(Listing.id)).group_by(Listing.source)), Listing),
        (await db.execute(select(Transaction.source, func.count(Transaction.id)).group_by(Transaction.source)), Transaction),
    ]:
        for row in source_result.all():
            by_source[row[0]] = row[1]

    avg_price_by_county: dict[str, float] = {}
    for model in (Listing, Transaction):
        rows = (await db.execute(
            select(model.county, func.avg(model.price))
            .where(model.price.isnot(None), model.county.isnot(None))
            .group_by(model.county)
        )).all()
        for county, avg in rows:
            if county:
                avg_price_by_county[county] = round(avg, 2)

    avg_unit_price_by_county: dict[str, float] = {}
    for model in (Listing, Transaction):
        rows = (await db.execute(
            select(model.county, func.avg(model.unit_price))
            .where(model.unit_price.isnot(None), model.county.isnot(None))
            .group_by(model.county)
        )).all()
        for county, avg in rows:
            if county:
                avg_unit_price_by_county[county] = round(avg, 2)

    return Stats(
        total_listings=total_listings,
        total_transactions=total_transactions,
        by_source=by_source,
        avg_price_by_county=avg_price_by_county,
        avg_unit_price_by_county=avg_unit_price_by_county,
    )


@router.post("/crawl")
async def trigger_crawl(
    background_tasks: BackgroundTasks,
    source: Optional[str] = Query(None, description="Specific crawler: lvr_land, house591, yungching, sinyi, chunghua"),
):
    from app.crawlers.runner import run_all_crawlers, run_crawler, ALL_CRAWLERS

    if source:
        crawler_map = {c.name: c for c in ALL_CRAWLERS}
        if source not in crawler_map:
            raise HTTPException(status_code=400, detail=f"Unknown source: {source}")
        background_tasks.add_task(run_crawler, crawler_map[source])
        return {"message": f"Crawl started for {source}"}

    background_tasks.add_task(run_all_crawlers)
    return {"message": "Full crawl started in background"}
