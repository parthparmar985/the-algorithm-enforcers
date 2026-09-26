from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session
from typing import List

from ...auth.jwt import get_current_user
from ...database.database import get_db
from ...models.camera import Camera
from ...models.detection import Detection
from ...models.user import User
from ...schemas.camera import CameraCreate, CameraResponse, CameraUpdate
from ...services.camera_health import HEALTH_STATES, HealthCheckInProgress, check_all_cameras, check_camera
from ...services.camera_url import validate_stream_url


router = APIRouter()


def require_health_access(user: User):
    if user.role not in {"ADMIN", "OPERATOR"}:
        raise HTTPException(403, "Camera health checks require operator access")


def camera_rows(db: Session, camera_id: int | None = None):
    latest = (db.query(Detection.camera_id, func.max(Detection.timestamp).label("last_detection_at"))
              .group_by(Detection.camera_id).subquery())
    query = db.query(Camera, latest.c.last_detection_at).outerjoin(latest, Camera.id == latest.c.camera_id)
    if camera_id is not None:
        query = query.filter(Camera.id == camera_id)
    rows = query.order_by(Camera.id).all()
    for camera, last_detection in rows:
        camera.last_detection_at = last_detection
        from ...services.stream_runtime import snapshot
        camera.runtime_health = snapshot(camera.id)
    return [camera for camera, _last_detection in rows]


@router.get("/", response_model=List[CameraResponse])
def get_cameras(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return camera_rows(db)


@router.post("/", response_model=CameraResponse)
def create_camera(camera: CameraCreate, db: Session = Depends(get_db),
                  current_user: User = Depends(get_current_user)):
    if current_user.role != "ADMIN":
        raise HTTPException(403, "Only admins can manage cameras")
    if db.query(Camera).filter(Camera.camera_code == camera.camera_code).first():
        raise HTTPException(400, "Camera code already exists")
    try:
        stream_url = validate_stream_url(camera.stream_url)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    values = camera.model_dump()
    values["stream_url"] = stream_url
    new_camera = Camera(**values)
    db.add(new_camera)
    db.commit()
    db.refresh(new_camera)
    new_camera.last_detection_at = None
    return new_camera


@router.get("/health-summary")
def health_summary(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    counts = {state: db.query(Camera).filter(Camera.health_status == state).count() for state in HEALTH_STATES}
    return {"total": db.query(Camera).count(), "online": counts["ONLINE"],
            "degraded": counts["DEGRADED"], "offline": counts["OFFLINE"],
            "unknown": counts["UNKNOWN"]}


@router.post("/health-check-all")
def health_check_all(current_user: User = Depends(get_current_user)):
    require_health_access(current_user)
    try:
        return check_all_cameras(force=True)
    except HealthCheckInProgress as exc:
        raise HTTPException(409, str(exc)) from exc


@router.post("/{camera_id}/health-check")
def health_check(camera_id: int, db: Session = Depends(get_db),
                 current_user: User = Depends(get_current_user)):
    require_health_access(current_user)
    if not db.query(Camera.id).filter(Camera.id == camera_id).first():
        raise HTTPException(404, "Camera not found")
    result = check_camera(camera_id)
    if result.get("error"):
        raise HTTPException(404, result["error"])
    return result


@router.get("/{id}", response_model=CameraResponse)
def get_camera(id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    cameras = camera_rows(db, id)
    if not cameras:
        raise HTTPException(404, "Camera not found")
    return cameras[0]


@router.put("/{id}", response_model=CameraResponse)
def update_camera(id: int, cam_update: CameraUpdate, db: Session = Depends(get_db),
                  current_user: User = Depends(get_current_user)):
    if current_user.role != "ADMIN":
        raise HTTPException(403, "Only admins can manage cameras")
    camera = db.query(Camera).filter(Camera.id == id).first()
    if not camera:
        raise HTTPException(404, "Camera not found")
    update_values = cam_update.model_dump(exclude_unset=True)
    if "stream_url" in update_values:
        try:
            update_values["stream_url"] = validate_stream_url(update_values["stream_url"])
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc
        if update_values["stream_url"] != camera.stream_url:
            camera.health_status = "UNKNOWN"
            camera.last_health_check = None
            camera.latency_ms = None
            camera.consecutive_failures = 0
            camera.stream_available = False
            camera.health_message = "Stream configuration changed; awaiting health check"
    for key, value in update_values.items():
        setattr(camera, key, value)
    db.commit()
    db.refresh(camera)
    camera.last_detection_at = db.query(func.max(Detection.timestamp)).filter(Detection.camera_id == camera.id).scalar()
    return camera


@router.delete("/{id}")
def delete_camera(id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.role != "ADMIN":
        raise HTTPException(403, "Only admins can manage cameras")
    camera = db.query(Camera).filter(Camera.id == id).first()
    if not camera:
        raise HTTPException(404, "Camera not found")
    db.delete(camera)
    db.commit()
    return {"message": "Camera deleted successfully"}
