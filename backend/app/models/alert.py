from sqlalchemy import Column, Integer, String, DateTime
from datetime import datetime
from ..database.database import Base

class Alert(Base):
    __tablename__ = "alerts"
    
    id = Column(Integer, primary_key=True, index=True)
    camera_id = Column(Integer, index=True)
    alert_type = Column(String(100))
    severity = Column(String(50)) # CRITICAL, HIGH, MEDIUM, LOW
    message = Column(String(500))
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    status = Column(String(50), default="NEW") # NEW, REVIEWED, RESOLVED
    snapshot_path = Column(String(500), nullable=True)
