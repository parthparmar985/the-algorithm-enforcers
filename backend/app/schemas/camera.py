from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class CameraBase(BaseModel):
    camera_name: str
    camera_code: str
    location: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    stream_url: Optional[str] = None
    status: Optional[str] = "OFFLINE"

class CameraCreate(CameraBase):
    pass

class CameraUpdate(BaseModel):
    camera_name: Optional[str] = None
    camera_code: Optional[str] = None
    location: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    stream_url: Optional[str] = None
    status: Optional[str] = None

class CameraResponse(CameraBase):
    id: int
    created_at: datetime
    
    class Config:
        from_attributes = True
