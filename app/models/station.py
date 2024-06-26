from sqlalchemy import Column, String, Float, Boolean, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base

class Station(Base):
    __tablename__ = "stations"

    id = Column(String, primary_key=True, index=True)
    name = Column(String)
    chain = Column(String)
    brand = Column(String)
    address_street = Column(String)
    address_city = Column(String)
    address_zipcode = Column(String)
    address_country = Column(String)
    location_latitude = Column(Float)
    location_longitude = Column(Float)
    is_visible = Column(Boolean)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    prices = relationship("Price", back_populates="station")
