from sqlalchemy import Column, Integer, String, Float, DateTime
from datetime import datetime
from ..database.database import Base

class Camera(Base):
    __tablename__ = "cameras"
    
    id = Column(Integer, primary_key=True, index=True)
    camera_name = Column(String(255), nullable=False)
    camera_code = Column(String(50), unique=True, index=True)
    location = Column(String(255))
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    stream_url = Column(String(500))
    status = Column(String(50), default="OFFLINE") # ONLINE, OFFLINE, PROCESSING
    created_at = Column(DateTime, default=datetime.utcnow)
