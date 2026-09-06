"""Database-derived investigation context and restricted evidence file access."""
import hashlib
import os
from pathlib import Path
from datetime import timedelta
from fastapi import HTTPException
from sqlalchemy import and_, or_
from ..models.vehicle import Vehicle
from ..models.detection import Detection
from ..models.alert import Alert
from ..models.camera import Camera
from ..api.routes.search import trace_data


def metadata(row):
    return {c.name: (getattr(row, c.name).isoformat() if hasattr(getattr(row, c.name), "isoformat") else getattr(row, c.name))
            for c in row.__table__.columns if c.name not in {"snapshot_path", "stream_url", "file_path", "source_key"}}


def snapshot_bytes(path):
    if not path:
        return None
    root = (Path(os.getenv("UPLOAD_DIR", "uploads")) / "snapshots").resolve()
    candidate = Path(path)
    if ".." in candidate.parts or candidate.is_symlink():
        raise HTTPException(400, "Unsafe evidence file reference")
    resolved = candidate.resolve()
    if not resolved.is_relative_to(root) or resolved.suffix.lower() not in {".jpg", ".jpeg", ".png"}:
        raise HTTPException(400, "Unsafe evidence file reference")
    try:
        if resolved.stat().st_size > 20 * 1024 * 1024:
            raise HTTPException(413, "Evidence image exceeds 20 MB")
        return resolved.read_bytes()
    except OSError:
        raise HTTPException(409, "Evidence snapshot is missing or unreadable")


def verified_bytes(item):
    data = snapshot_bytes(item.file_path)
    if data is not None and hashlib.sha256(data).hexdigest() != item.sha256:
        raise HTTPException(409, f"Evidence {item.id}: SHA-256 mismatch")
    return data


def evidence_metadata(item):
    result = metadata(item)
    result["file_name"] = f"evidence_{item.id:03d}{Path(item.file_path).suffix.lower()}" if item.file_path else None
    try:
        verified_bytes(item)
        result["file_status"] = "AVAILABLE" if item.file_path else "NO_SNAPSHOT"
    except HTTPException as exc:
        result["file_status"] = exc.detail
    return result


def context(db, investigation):
    vehicles = db.query(Vehicle).filter(Vehicle.number_plate == investigation.vehicle_plate).order_by(Vehicle.first_seen).all()
    # Tracking IDs restart on videos. Bound association by camera AND sighting interval.
    clauses = [and_(Detection.camera_id == v.camera_id, Detection.tracking_id == v.tracking_id,
                    Detection.timestamp >= v.first_seen - timedelta(seconds=1), Detection.timestamp <= v.last_seen + timedelta(seconds=1))
               for v in vehicles if v.tracking_id is not None]
    detections = db.query(Detection).filter(or_(*clauses)).order_by(Detection.timestamp).all() if clauses else []
    snapshots = {v.snapshot_path for v in vehicles if v.snapshot_path} | {d.snapshot_path for d in detections if d.snapshot_path}
    # Alerts have no plate FK. Only shared snapshot provenance establishes a relation.
    alerts = db.query(Alert).filter(Alert.snapshot_path.in_(snapshots)).order_by(Alert.timestamp).all() if snapshots else []
    cameras = db.query(Camera).filter(Camera.id.in_({v.camera_id for v in vehicles})).all()
    route = trace_data(investigation.vehicle_plate, db)
    route = [{k: v for k, v in row.items() if k != "snapshot_path"} for row in route]
    return {"investigation_id": investigation.id, "vehicle_plate": investigation.vehicle_plate,
            "vehicles": [metadata(v) for v in vehicles], "detections": [metadata(d) for d in detections],
            "alerts": [metadata(a) for a in alerts], "cameras": [metadata(c) for c in cameras], "route": route,
            "summary": {"first_seen": min((v.first_seen for v in vehicles), default=None),
                        "last_seen": max((v.last_seen for v in vehicles), default=None),
                        "detection_count": len(detections), "camera_count": len(cameras), "alert_count": len(alerts),
                        "speed_anomalies": sum(r["transition_status"] == "ANOMALOUS TRANSITION" for r in route),
                        "total_route_distance_km": round(sum(r["distance_km"] for r in route), 2)},
            "association_note": "Detections associated by camera, track and sighting interval; alerts by shared snapshot. Human verification required."}
