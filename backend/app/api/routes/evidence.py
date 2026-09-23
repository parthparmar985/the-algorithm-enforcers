import hashlib
import json
import logging
from datetime import datetime, timezone
from io import BytesIO
from zipfile import ZipFile, ZIP_DEFLATED
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException
from fastapi.encoders import jsonable_encoder
from fastapi.responses import Response
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from ...auth.jwt import get_current_user
from ...database.database import get_db
from ...models.evidence import Investigation, Evidence
from ...models.vehicle import Vehicle
from ...models.detection import Detection
from ...models.alert import Alert
from ...services.evidence_service import context, metadata, snapshot_bytes, verified_bytes, evidence_metadata
from ...ai.plate_utils import normalize_plate

router = APIRouter()


def investigator(user=Depends(get_current_user)):
    if user.role not in {"ADMIN", "OPERATOR"}:
        raise HTTPException(403, "Investigator access required")
    return user


def access(db, user, reference):
    item = db.get(Investigation, reference)
    if not item or (item.created_by != user.id and user.role != "ADMIN"):
        raise HTTPException(404, "Investigation not found")
    return item


class ReferenceCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    vehicle_plate: str = Field(pattern=r"^[A-Z0-9 -]{2,50}$")


class EvidenceCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    investigation_id: str = Field(max_length=36)
    evidence_type: Literal["SNAPSHOT", "DETECTION", "ALERT", "PLATE_DETECTION", "ROUTE_TRACE"]
    detection_id: int | None = Field(default=None, gt=0)
    vehicle_id: int | None = Field(default=None, gt=0)
    alert_id: int | None = Field(default=None, gt=0)
    description: str = Field(default="", max_length=2000)


class ExportRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    investigation_id: str = Field(max_length=36)
    evidence_ids: list[int] = Field(min_length=1, max_length=100)
    format: Literal["pdf", "zip"] = "pdf"


@router.post("/investigations")
def create_reference(body: ReferenceCreate, db: Session = Depends(get_db), user=Depends(investigator)):
    normalized_plate = normalize_plate(body.vehicle_plate)
    if not db.query(Vehicle).filter(Vehicle.number_plate == normalized_plate).first():
        raise HTTPException(404, "No sightings for this plate")
    item = db.query(Investigation).filter_by(vehicle_plate=normalized_plate, created_by=user.id).first()
    if not item:
        item = Investigation(vehicle_plate=normalized_plate, created_by=user.id)
        db.add(item)
        db.commit()
        db.refresh(item)
    return metadata(item)


@router.get("/investigations/{reference}")
def investigation_summary(reference: str, db: Session = Depends(get_db), user=Depends(investigator)):
    result = context(db, access(db, user, reference))
    result["summary"]["evidence_count"] = db.query(Evidence).filter_by(investigation_id=reference).count()
    return result


@router.post("")
def create_evidence(body: EvidenceCreate, db: Session = Depends(get_db), user=Depends(investigator)):
    investigation = access(db, user, body.investigation_id)
    data = context(db, investigation)
    supplied = [(kind, ident) for kind, ident in [("detection", body.detection_id), ("vehicle", body.vehicle_id), ("alert", body.alert_id)] if ident is not None]
    if body.evidence_type == "ROUTE_TRACE":
        if supplied or not data["route"]:
            raise HTTPException(400, "Route evidence requires an existing route and no source ID")
        source, source_key, details, timestamp, camera_id, path = None, "route", {"route": data["route"]}, datetime.utcnow(), None, None
    else:
        if len(supplied) != 1:
            raise HTTPException(400, "Select exactly one source record")
        kind, ident = supplied[0]
        allowed = {"DETECTION": "detection", "ALERT": "alert", "PLATE_DETECTION": "vehicle"}
        if body.evidence_type in allowed and kind != allowed[body.evidence_type]:
            raise HTTPException(400, "Evidence type does not match source")
        if ident not in {r["id"] for r in data[{"detection": "detections", "vehicle": "vehicles", "alert": "alerts"}[kind]]}:
            raise HTTPException(404, "Source is not part of this investigation")
        source = db.get({"detection": Detection, "vehicle": Vehicle, "alert": Alert}[kind], ident)
        source_key, details = f"{kind}:{ident}", metadata(source)
        timestamp = source.first_seen if kind == "vehicle" else source.timestamp
        camera_id, path = source.camera_id, source.snapshot_path
        if body.evidence_type == "SNAPSHOT" and not path:
            raise HTTPException(409, "Source has no snapshot")
    existing = db.query(Evidence).filter_by(investigation_id=investigation.id, source_key=source_key).first()
    if existing:
        return evidence_metadata(existing)
    content = snapshot_bytes(path)
    item = Evidence(**body.model_dump(), source_key=source_key, camera_id=camera_id, timestamp=timestamp,
                    vehicle_plate=investigation.vehicle_plate, file_path=path, details=details,
                    sha256=hashlib.sha256(content).hexdigest() if content else None, created_by=user.id)
    db.add(item)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        item = db.query(Evidence).filter_by(investigation_id=investigation.id, source_key=source_key).one()
    db.refresh(item)
    return evidence_metadata(item)


@router.get("")
def list_evidence(investigation_id: str | None = None, plate: str | None = None, camera_id: int | None = None,
                  start_time: datetime | None = None, end_time: datetime | None = None, evidence_type: str | None = None,
                  db: Session = Depends(get_db), user=Depends(investigator)):
    query = db.query(Evidence).join(Investigation)
    if user.role != "ADMIN":
        query = query.filter(Investigation.created_by == user.id)
    if investigation_id:
        access(db, user, investigation_id)
        query = query.filter(Evidence.investigation_id == investigation_id)
    for value, column in [(plate, Evidence.vehicle_plate), (camera_id, Evidence.camera_id), (evidence_type, Evidence.evidence_type)]:
        if value is not None:
            query = query.filter(column == value)
    if start_time:
        query = query.filter(Evidence.timestamp >= start_time)
    if end_time:
        query = query.filter(Evidence.timestamp <= end_time)
    return [evidence_metadata(e) for e in query.order_by(Evidence.timestamp, Evidence.id).all()]


@router.post("/export")
def export_evidence(body: ExportRequest, db: Session = Depends(get_db), user=Depends(investigator)):
    investigation = access(db, user, body.investigation_id)
    ids = set(body.evidence_ids)
    items = db.query(Evidence).filter(Evidence.investigation_id == investigation.id, Evidence.id.in_(ids)).order_by(Evidence.timestamp, Evidence.id).all()
    if len(items) != len(ids):
        raise HTTPException(404, "Selected evidence not found in investigation")
    files = {e.id: verified_bytes(e) for e in items}
    data = context(db, investigation)
    data.update(generated_at=datetime.now(timezone.utc).isoformat(), generated_by={"id": user.id, "name": user.name}, evidence=[evidence_metadata(e) for e in items])
    data["summary"]["evidence_count"] = len(items)
    data = jsonable_encoder(data)
    try:
        from ...services.investigation_report import generate_pdf
        pdf = generate_pdf(data, files)
        if body.format == "pdf":
            content, media = pdf, "application/pdf"
        else:
            output = BytesIO()
            with ZipFile(output, "w", ZIP_DEFLATED) as archive:
                archive.writestr("investigation/report.pdf", pdf)
                for name, payload in [("metadata", data), ("timeline", data["detections"]), ("route", data["route"])]:
                    archive.writestr(f"investigation/{name}.json", json.dumps(payload, indent=2))
                for item in data["evidence"]:
                    if files[item["id"]] is not None:
                        archive.writestr(f"investigation/evidence/{item['file_name']}", files[item["id"]])
            content, media = output.getvalue(), "application/zip"
    except Exception:
        logging.exception("Investigation export failed")
        raise HTTPException(500, "Report generation failed; please retry or contact an administrator")
    plate = "".join(c for c in investigation.vehicle_plate if c.isascii() and c.isalnum())
    filename = f"investigation_{plate}_{datetime.now(timezone.utc):%Y-%m-%d}.{body.format}"
    return Response(content, media_type=media, headers={"Content-Disposition": f'attachment; filename="{filename}"', "Cache-Control": "no-store"})


def get_item(db, user, evidence_id):
    item = db.get(Evidence, evidence_id)
    if not item:
        raise HTTPException(404, "Evidence not found")
    access(db, user, item.investigation_id)
    return item


@router.get("/{evidence_id}")
def get_evidence(evidence_id: int, db: Session = Depends(get_db), user=Depends(investigator)):
    return evidence_metadata(get_item(db, user, evidence_id))


@router.get("/{evidence_id}/file")
def preview_evidence(evidence_id: int, db: Session = Depends(get_db), user=Depends(investigator)):
    item = get_item(db, user, evidence_id)
    content = verified_bytes(item)
    if content is None:
        raise HTTPException(404, "Evidence has no snapshot")
    return Response(content, media_type="image/png" if item.file_path.lower().endswith(".png") else "image/jpeg", headers={"Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"})


@router.delete("/{evidence_id}")
def delete_evidence(evidence_id: int, db: Session = Depends(get_db), user=Depends(investigator)):
    item = get_item(db, user, evidence_id)
    db.delete(item)
    db.commit()
    return {"message": "Removed from evidence; original source retained"}
