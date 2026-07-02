from datetime import datetime
from sqlalchemy import String, Float, Integer, DateTime, Text, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column
import enum

from app.database import Base


class PropertyType(str, enum.Enum):
    house = "house"
    apartment = "apartment"
    land = "land"
    office = "office"
    other = "other"


class Transaction(Base):
    """實價登錄成交紀錄 (lvr_land)"""
    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source: Mapped[str] = mapped_column(String(50), nullable=False, default="lvr_land", index=True)
    source_id: Mapped[str] = mapped_column(String(255), nullable=True)

    title: Mapped[str] = mapped_column(String(500), nullable=False)
    property_type: Mapped[str] = mapped_column(SAEnum(PropertyType), default=PropertyType.apartment)

    county: Mapped[str] = mapped_column(String(20), nullable=True, index=True)
    district: Mapped[str] = mapped_column(String(30), nullable=True, index=True)
    address: Mapped[str] = mapped_column(String(500), nullable=True)

    price: Mapped[float] = mapped_column(Float, nullable=True)
    unit_price: Mapped[float] = mapped_column(Float, nullable=True)
    area_ping: Mapped[float] = mapped_column(Float, nullable=True)
    floor: Mapped[str] = mapped_column(String(20), nullable=True)
    total_floors: Mapped[int] = mapped_column(Integer, nullable=True)
    rooms: Mapped[int] = mapped_column(Integer, nullable=True)
    age: Mapped[float] = mapped_column(Float, nullable=True)

    url: Mapped[str] = mapped_column(Text, nullable=True)
    description: Mapped[str] = mapped_column(Text, nullable=True)

    trade_date: Mapped[datetime] = mapped_column(DateTime, nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ListingSource(str, enum.Enum):
    house591 = "house591"
    yungching = "yungching"
    sinyi = "sinyi"
    chunghua = "chunghua"


class Listing(Base):
    """代售物件 (591/永慶/信義/住商)"""
    __tablename__ = "listings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source: Mapped[str] = mapped_column(SAEnum(ListingSource), nullable=False, index=True)
    source_id: Mapped[str] = mapped_column(String(255), nullable=True)

    title: Mapped[str] = mapped_column(String(500), nullable=False)
    property_type: Mapped[str] = mapped_column(SAEnum(PropertyType), default=PropertyType.apartment)

    county: Mapped[str] = mapped_column(String(20), nullable=True, index=True)
    district: Mapped[str] = mapped_column(String(30), nullable=True, index=True)
    address: Mapped[str] = mapped_column(String(500), nullable=True)

    price: Mapped[float] = mapped_column(Float, nullable=True)
    unit_price: Mapped[float] = mapped_column(Float, nullable=True)
    area_ping: Mapped[float] = mapped_column(Float, nullable=True)
    floor: Mapped[str] = mapped_column(String(20), nullable=True)
    total_floors: Mapped[int] = mapped_column(Integer, nullable=True)
    rooms: Mapped[int] = mapped_column(Integer, nullable=True)
    age: Mapped[float] = mapped_column(Float, nullable=True)

    url: Mapped[str] = mapped_column(Text, nullable=True)
    description: Mapped[str] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
