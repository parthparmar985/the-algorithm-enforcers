from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class DetectionBase(BaseModel):
    camera_id: int
    detection_type: str
    object_class: str
    confidence: float
    tracking_id: Optional[int]
    timestamp: datetime
    frame_number: int
    bounding_box: str 
    snapshot_path: Optional[str]

class DetectionResponse(DetectionBase):
    id: int
    
    class Config:
        from_attributes = True
