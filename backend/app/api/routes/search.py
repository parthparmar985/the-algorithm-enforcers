import math
from datetime import datetime, timedelta, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import or_
from sqlalchemy.orm import Session
from ...database.database import get_db
from ...models.vehicle import Vehicle
from ...models.detection import Detection
from ...models.alert import Alert
from ...models.camera import Camera
from ...auth.jwt import get_current_user
from ...ai.plate_utils import normalize_plate
from ...services.natural_investigation import parse_natural_query

router = APIRouter()


class NaturalSearchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    query: str = Field(min_length=1, max_length=500)

    @field_validator("query")
    @classmethod
    def query_must_contain_text(cls, value):
        if not value.strip():
            raise ValueError("Query must contain text")
        return value


def utc_naive(value):
    return value.astimezone(timezone.utc).replace(tzinfo=None) if value and value.tzinfo else value


def haversine(lat1, lon1, lat2, lon2):
    radius_km = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    value = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    return radius_km * 2 * math.atan2(math.sqrt(value), math.sqrt(1 - value))


def transition(previous, current):
    if previous is None:
        return {"distance_km": 0.0, "time_diff_mins": 0.0, "calculated_speed_kmh": None, "transition_status": "STARTPOINT"}
    previous_vehicle, previous_camera = previous
    vehicle, camera = current
    seconds = (vehicle.first_seen - previous_vehicle.first_seen).total_seconds()
    distance = 0.0
    coordinates = (camera.latitude, camera.longitude, previous_camera.latitude, previous_camera.longitude)
    if all(value is not None for value in coordinates):
        distance = haversine(previous_camera.latitude, previous_camera.longitude, camera.latitude, camera.longitude)
    speed = distance / (seconds / 3600) if seconds > 0 else None
    anomalous = (speed is not None and speed > 150) or (seconds <= 0 and distance > 0.5)
    return {"distance_km": round(distance, 2), "time_diff_mins": round(seconds / 60, 1),
            "calculated_speed_kmh": round(speed, 1) if speed is not None else None,
            "transition_status": "ANOMALOUS TRANSITION" if anomalous else "PLAUSIBLE TRANSITION"}


def build_timeline(db: Session, rows):
    if not rows:
        return []
    vehicles = [vehicle for vehicle, _camera in rows]
    camera_ids = {vehicle.camera_id for vehicle in vehicles}
    first = min(vehicle.first_seen for vehicle in vehicles) - timedelta(seconds=1)
    last = max(vehicle.last_seen for vehicle in vehicles) + timedelta(seconds=1)
    detections = db.query(Detection).filter(Detection.camera_id.in_(camera_ids), Detection.timestamp.between(first, last)).all()
    snapshot_paths = {vehicle.snapshot_path for vehicle in vehicles if vehicle.snapshot_path}
    alerts = db.query(Alert).filter(Alert.snapshot_path.in_(snapshot_paths)).all() if snapshot_paths else []
    alerts_by_snapshot = {}
    for alert in alerts:
        alerts_by_snapshot.setdefault(alert.snapshot_path, []).append({
            "id": alert.id, "type": alert.alert_type, "severity": alert.severity,
            "message": alert.message, "timestamp": alert.timestamp.isoformat()
        })
    timeline = []
    previous = None
    for vehicle, camera in rows:
        related = [d for d in detections if d.camera_id == vehicle.camera_id and d.tracking_id == vehicle.tracking_id
                   and vehicle.first_seen - timedelta(seconds=1) <= d.timestamp <= vehicle.last_seen + timedelta(seconds=1)]
        event = {
            "id": vehicle.id, "vehicle_id": vehicle.id, "camera_id": camera.id,
            "camera_code": camera.camera_code, "camera_name": camera.camera_name,
            "location": camera.location, "latitude": camera.latitude, "longitude": camera.longitude,
            "timestamp": vehicle.first_seen.isoformat(), "last_seen": vehicle.last_seen.isoformat(),
            "registration_number": vehicle.number_plate, "plate_raw_text": vehicle.plate_raw_text,
            "plate_confidence": vehicle.plate_confidence, "detection_confidence": max((d.confidence for d in related), default=None),
            "vehicle_type": vehicle.vehicle_type, "snapshot_path": vehicle.snapshot_path,
            "alerts": alerts_by_snapshot.get(vehicle.snapshot_path, []) if vehicle.snapshot_path else [],
            **transition(previous, (vehicle, camera)),
        }
        timeline.append(event)
        previous = (vehicle, camera)
    return timeline


def trace_data(registration_number: str, db: Session):
    normalized = normalize_plate(registration_number)
    rows = (db.query(Vehicle, Camera).join(Camera, Vehicle.camera_id == Camera.id)
            .filter(Vehicle.number_plate == normalized).order_by(Vehicle.first_seen, Vehicle.id).all())
    return build_timeline(db, rows)


def run_structured_search(
    db: Session, registration_number=None, vehicle_type=None, camera_id=None,
    location=None, start_time=None, end_time=None,
):
    start_time, end_time = utc_naive(start_time), utc_naive(end_time)
    if start_time and end_time and start_time > end_time:
        raise HTTPException(400, "Start time must be before end time")
    query = db.query(Vehicle, Camera).join(Camera, Vehicle.camera_id == Camera.id).filter(Vehicle.number_plate.is_not(None))
    if registration_number:
        query = query.filter(Vehicle.number_plate == normalize_plate(registration_number))
    if vehicle_type:
        query = query.filter(Vehicle.vehicle_type == vehicle_type.lower())
    if camera_id:
        query = query.filter(Vehicle.camera_id == camera_id)
    if location:
        query = query.filter(Camera.location.ilike(f"%{location.strip()}%"))
    if start_time:
        query = query.filter(Vehicle.first_seen >= start_time)
    if end_time:
        query = query.filter(Vehicle.first_seen <= end_time)
    rows = query.order_by(Vehicle.first_seen, Vehicle.id).limit(200).all()
    return build_timeline(db, rows)


@router.get("/investigations")
def structured_investigation_search(
    registration_number: Optional[str] = Query(default=None, max_length=50),
    vehicle_type: Optional[str] = Query(default=None, max_length=100),
    camera_id: Optional[int] = Query(default=None, gt=0),
    location: Optional[str] = Query(default=None, max_length=255),
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    db: Session = Depends(get_db), current_user=Depends(get_current_user),
):
    return run_structured_search(
        db, registration_number, vehicle_type, camera_id, location, start_time, end_time
    )


@router.post("/natural")
def natural_investigation_search(
    request: NaturalSearchRequest,
    db: Session = Depends(get_db), current_user=Depends(get_current_user),
):
    cameras = db.query(Camera).order_by(Camera.id).all()
    try:
        parsed = parse_natural_query(request.query, cameras)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc

    filters = parsed.filters.copy()
    filters.pop("camera_name", None)
    results = []
    if parsed.status == "PARSED":
        results = run_structured_search(db, **filters)
    return {
        "status": parsed.status,
        "original_query": request.query,
        "parsed_filters": jsonable_encoder(parsed.filters),
        "confidence": parsed.confidence,
        "interpretation": parsed.interpretation,
        "unparsed_terms": parsed.unparsed_terms,
        "warnings": parsed.warnings,
        "matches": parsed.matches,
        "results": results,
        "result_count": len(results),
        "timezone": {
            "input": "Asia/Kolkata",
            "storage_and_api": "UTC",
        },
    }


@router.get("/vehicles")
def search_vehicles(
    query_str: Optional[str] = None, camera_id: Optional[int] = None,
    vehicle_type: Optional[str] = None, location: Optional[str] = None,
    start_time: Optional[datetime] = None, end_time: Optional[datetime] = None,
    db: Session = Depends(get_db), current_user=Depends(get_current_user),
):
    start_time, end_time = utc_naive(start_time), utc_naive(end_time)
    if start_time and end_time and start_time > end_time:
        raise HTTPException(400, "Start time must be before end time")
    query = db.query(Vehicle).join(Camera, Vehicle.camera_id == Camera.id)
    if query_str:
        normalized = normalize_plate(query_str)
        query = query.filter(or_(Vehicle.number_plate == normalized, Vehicle.vehicle_type.ilike(f"%{query_str}%")))
    if camera_id:
        query = query.filter(Vehicle.camera_id == camera_id)
    if vehicle_type:
        query = query.filter(Vehicle.vehicle_type == vehicle_type.lower())
    if location:
        query = query.filter(Camera.location.ilike(f"%{location.strip()}%"))
    if start_time:
        query = query.filter(Vehicle.first_seen >= start_time)
    if end_time:
        query = query.filter(Vehicle.first_seen <= end_time)
    return query.order_by(Vehicle.first_seen.desc()).limit(100).all()


@router.get("/detections")
def search_detections(obj_class: Optional[str] = None, camera_id: Optional[int] = None,
                      db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    query = db.query(Detection)
    if obj_class:
        query = query.filter(Detection.object_class == obj_class)
    if camera_id:
        query = query.filter(Detection.camera_id == camera_id)
    return query.order_by(Detection.timestamp.desc()).limit(100).all()


@router.get("/trace/{registration_number}")
def trace_vehicle(registration_number: str, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    return trace_data(registration_number, db)
