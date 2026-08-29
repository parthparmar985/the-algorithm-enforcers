from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class AlertBase(BaseModel):
    camera_id: int
    alert_type: str
    severity: str
    message: str
    timestamp: datetime
    status: str
    snapshot_path: Optional[str]

class AlertResponse(AlertBase):
    id: int
    
    class Config:
        from_attributes = True

class AlertUpdate(BaseModel):
    status: str
