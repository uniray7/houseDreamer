from typing import Optional
from fastapi import APIRouter, Depends, Query, HTTPException, BackgroundTasks
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from datetime import datetime

from app.database import get_db
from app.models import Listing

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
    trade_date: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True


class PaginatedListings(BaseModel):
    total: int
    page: int
    page_size: int
    items: list[ListingOut]


class Stats(BaseModel):
    total_listings: int
    by_source: dict[str, int]
    avg_price_by_county: dict[str, float]
    avg_unit_price_by_county: dict[str, float]


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
    if county:
        q = q.where(Listing.county == county)
    if district:
        q = q.where(Listing.district == district)
    if property_type:
        q = q.where(Listing.property_type == property_type)
    if min_price is not None:
        q = q.where(Listing.price >= min_price)
    if max_price is not None:
        q = q.where(Listing.price <= max_price)
    if min_area is not None:
        q = q.where(Listing.area_ping >= min_area)
    if max_area is not None:
        q = q.where(Listing.area_ping <= max_area)

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


@router.get("/stats", response_model=Stats)
async def get_stats(db: AsyncSession = Depends(get_db)):
    total_result = await db.execute(select(func.count(Listing.id)))
    total = total_result.scalar_one()

    by_source_result = await db.execute(
        select(Listing.source, func.count(Listing.id)).group_by(Listing.source)
    )
    by_source = {row[0]: row[1] for row in by_source_result.all()}

    avg_price_result = await db.execute(
        select(Listing.county, func.avg(Listing.price))
        .where(Listing.price.isnot(None), Listing.county.isnot(None))
        .group_by(Listing.county)
    )
    avg_price_by_county = {
        row[0]: round(row[1], 2) for row in avg_price_result.all() if row[0]
    }

    avg_unit_result = await db.execute(
        select(Listing.county, func.avg(Listing.unit_price))
        .where(Listing.unit_price.isnot(None), Listing.county.isnot(None))
        .group_by(Listing.county)
    )
    avg_unit_price_by_county = {
        row[0]: round(row[1], 2) for row in avg_unit_result.all() if row[0]
    }

    return Stats(
        total_listings=total,
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
