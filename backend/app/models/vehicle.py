from sqlalchemy import Column, Integer, String, Float, DateTime, Index
from datetime import datetime
from ..database.database import Base

class Vehicle(Base):
    __tablename__ = "vehicles"
    
    id = Column(Integer, primary_key=True, index=True)
    camera_id = Column(Integer, index=True)
    tracking_id = Column(Integer, index=True)
    vehicle_type = Column(String(100))
    number_plate = Column(String(50), index=True, nullable=True)
    plate_raw_text = Column(String(100), nullable=True)
    plate_confidence = Column(Float, nullable=True)
    first_seen = Column(DateTime, default=datetime.utcnow)
    last_seen = Column(DateTime, default=datetime.utcnow)
    snapshot_path = Column(String(500), nullable=True)

    __table_args__ = (
        Index("ix_vehicles_camera_first_seen", "camera_id", "first_seen"),
        Index("ix_vehicles_plate_first_seen", "number_plate", "first_seen"),
    )
