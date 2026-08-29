from sqlalchemy import Column, Integer, String, DateTime
from datetime import datetime
from ..database.database import Base

class Watchlist(Base):
    __tablename__ = "watchlists"
    
    id = Column(Integer, primary_key=True, index=True)
    registration_number = Column(String(50), unique=True, index=True, nullable=False)
    category = Column(String(100)) # STOLEN VEHICLE, BLACKLISTED VEHICLE, WANTED VEHICLE
    priority = Column(String(50), default="HIGH") 
    status = Column(String(50), default="ACTIVE") # ACTIVE, RESOLVED
    description = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
