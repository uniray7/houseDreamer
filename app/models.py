from datetime import datetime
from sqlalchemy import String, Float, Integer, DateTime, Text, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column
import enum

from app.database import Base


class DataSource(str, enum.Enum):
    lvr_land = "lvr_land"
    house591 = "house591"
    yungching = "yungching"
    sinyi = "sinyi"
    chunghua = "chunghua"


class PropertyType(str, enum.Enum):
    house = "house"
    apartment = "apartment"
    land = "land"
    office = "office"
    other = "other"


class Listing(Base):
    __tablename__ = "listings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source: Mapped[str] = mapped_column(SAEnum(DataSource), nullable=False, index=True)
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

    trade_date: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
