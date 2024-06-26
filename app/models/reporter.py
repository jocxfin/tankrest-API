from sqlalchemy import Column, Integer, String
from app.core.database import Base

class Reporter(Base):
    __tablename__ = "reporters"

    id = Column(Integer, primary_key=True, index=True)
    reporter_id = Column(String)
    name = Column(String)
    affiliation = Column(String)
