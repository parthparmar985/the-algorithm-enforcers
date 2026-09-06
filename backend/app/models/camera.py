from sqlalchemy import Boolean, Column, Integer, String, Float, DateTime
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
    # Operator-configured runtime state retained for backwards compatibility.
    # Reachability is represented independently by health_status.
    status = Column(String(50), default="OFFLINE") # ONLINE, OFFLINE, PROCESSING
    health_status = Column(String(20), nullable=False, default="UNKNOWN", index=True)
    last_health_check = Column(DateTime, nullable=True)
    last_online_at = Column(DateTime, nullable=True)
    last_frame_at = Column(DateTime, nullable=True)
    latency_ms = Column(Integer, nullable=True)
    consecutive_failures = Column(Integer, nullable=False, default=0)
    stream_available = Column(Boolean, nullable=False, default=False)
    health_message = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
