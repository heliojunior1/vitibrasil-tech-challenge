from sqlalchemy import Column, Integer, String, Float, Enum, DateTime, UniqueConstraint
from src.app.config.database import Base
from datetime import datetime
from src.app.domain.viticulture import ViticultureCategory
import enum



class Viticulture(Base):
    __tablename__ = "viticulture"

    id = Column(Integer, primary_key=True, index=True)
    category = Column(Enum(ViticultureCategory), nullable=False)
    subcategory = Column(String, nullable=True)
    item = Column(String, nullable=False)
    year = Column(Integer, nullable=False)
    value = Column(Float, nullable=False)
    unit = Column(String, nullable=False)
    currency = Column(String, nullable=True)
    source_url = Column(String, nullable=True)
    scraped_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("category", "subcategory", "item", "year", name="uq_viticulture_entry"),
    )