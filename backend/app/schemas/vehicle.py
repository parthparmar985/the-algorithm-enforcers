from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class VehicleBase(BaseModel):
    camera_id: int
    tracking_id: int
    vehicle_type: str
    number_plate: Optional[str]
    plate_confidence: Optional[float]
    first_seen: datetime
    last_seen: datetime
    snapshot_path: Optional[str]

class VehicleResponse(VehicleBase):
    id: int
    
    class Config:
        from_attributes = True
