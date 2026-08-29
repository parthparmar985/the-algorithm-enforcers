from sqlalchemy import Column, Integer, String, Float, DateTime, Text
from datetime import datetime
from ..database.database import Base

class Detection(Base):
    __tablename__ = "detections"
    
    id = Column(Integer, primary_key=True, index=True)
    camera_id = Column(Integer, index=True)
    detection_type = Column(String(100))
    object_class = Column(String(100))
    confidence = Column(Float)
    tracking_id = Column(Integer, index=True, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    frame_number = Column(Integer)
    bounding_box = Column(Text) # JSON string
    snapshot_path = Column(String(500), nullable=True)
