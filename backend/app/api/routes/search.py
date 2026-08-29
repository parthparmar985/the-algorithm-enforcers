from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
from ...database.database import get_db
from ...models.vehicle import Vehicle
from ...models.detection import Detection
from ...auth.jwt import get_current_user

router = APIRouter()

@router.get("/vehicles")
def search_vehicles(
    query_str: Optional[str] = None,
    camera_id: Optional[int] = None,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    from sqlalchemy import or_
    query = db.query(Vehicle)
    
    if query_str:
        query = query.filter(
            or_(
                Vehicle.number_plate.ilike(f"%{query_str}%"),
                Vehicle.vehicle_type.ilike(f"%{query_str}%")
            )
        )
    if camera_id:
        query = query.filter(Vehicle.camera_id == camera_id)
    if start_time:
        query = query.filter(Vehicle.last_seen >= start_time)
    if end_time:
        query = query.filter(Vehicle.last_seen <= end_time)
        
    results = query.order_by(Vehicle.last_seen.desc()).limit(100).all()
    return results

@router.get("/detections")
def search_detections(
    obj_class: Optional[str] = None,
    camera_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    query = db.query(Detection)
    
    if obj_class:
        query = query.filter(Detection.object_class == obj_class)
    if camera_id:
        query = query.filter(Detection.camera_id == camera_id)
        
    return query.order_by(Detection.timestamp.desc()).limit(100).all()

import math

def haversine(lat1, lon1, lat2, lon2):
    R = 6371.0 # Earth radius in km
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

@router.get("/trace/{registration_number}")
def trace_vehicle(registration_number: str, db: Session = Depends(get_db)):
    from ...models.camera import Camera
    
    # Chronological route trace
    sightings = db.query(Vehicle, Camera).join(Camera, Vehicle.camera_id == Camera.id)\
                   .filter(Vehicle.number_plate == registration_number)\
                   .order_by(Vehicle.first_seen.asc()).all()
    
    trace_results = []
    prev_sighting = None
    
    for v, c in sightings:
        item = {
            "id": v.id,
            "camera_id": c.id,
            "camera_code": c.camera_code,
            "camera_name": c.camera_name,
            "location": c.location,
            "latitude": c.latitude,
            "longitude": c.longitude,
            "timestamp": v.first_seen.isoformat(),
            "confidence": v.plate_confidence,
            "vehicle_type": v.vehicle_type,
            "snapshot_path": v.snapshot_path,
            "transition_status": "STARTPOINT",
            "distance_km": 0.0,
            "time_diff_mins": 0.0
        }
        
        if prev_sighting:
            p_v, p_c = prev_sighting
            time_diff = (v.first_seen - p_v.first_seen).total_seconds() / 60.0
            
            dist = 0.0
            if c.latitude and c.longitude and p_c.latitude and p_c.longitude:
                dist = haversine(p_c.latitude, p_c.longitude, c.latitude, c.longitude)
                
            item["distance_km"] = round(dist, 2)
            item["time_diff_mins"] = round(time_diff, 1)
            
            # Geographic anomaly evaluation
            if time_diff > 0:
                speed_kmh = (dist / (time_diff / 60.0))
                if speed_kmh > 150: 
                    item["transition_status"] = "ANOMALOUS TRANSITION"
                else:
                    item["transition_status"] = "PLAUSIBLE TRANSITION"
            else:
                 if dist > 0.5:
                     item["transition_status"] = "ANOMALOUS TRANSITION"
                 else:
                     item["transition_status"] = "PLAUSIBLE TRANSITION"
                     
        trace_results.append(item)
        prev_sighting = (v, c)
        
    return trace_results
