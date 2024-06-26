from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base

class Price(Base):
    __tablename__ = "prices"

    id = Column(Integer, primary_key=True, index=True)
    station_id = Column(String, ForeignKey("stations.id"))
    tag = Column(String)
    price = Column(Float)
    updated = Column(String)
    delta = Column(Float)
    reporter = Column(String)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    station = relationship("Station", back_populates="prices")
