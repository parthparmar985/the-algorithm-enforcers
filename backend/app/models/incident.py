from sqlalchemy import Column, Integer, String, DateTime, Text
from datetime import datetime
from ..database.database import Base

class Incident(Base):
    __tablename__ = "incidents"
    
    id = Column(Integer, primary_key=True, index=True)
    incident_type = Column(String(100))
    camera_id = Column(Integer, index=True)
    description = Column(Text)
    start_time = Column(DateTime, default=datetime.utcnow)
    end_time = Column(DateTime, nullable=True)
    severity = Column(String(50))
    status = Column(String(50), default="OPEN") # OPEN, IN_PROGRESS, CLOSED
