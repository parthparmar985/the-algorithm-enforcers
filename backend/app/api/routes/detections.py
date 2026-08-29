from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from ...database.database import get_db
from ...models.detection import Detection
from ...schemas.detection import DetectionResponse
from ...auth.jwt import get_current_user

router = APIRouter()

@router.get("/", response_model=List[DetectionResponse])
def get_detections(limit: int = 100, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    return db.query(Detection).order_by(Detection.timestamp.desc()).limit(limit).all()

@router.get("/{id}", response_model=DetectionResponse)
def get_detection(id: int, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    det = db.query(Detection).filter(Detection.id == id).first()
    if not det:
        raise HTTPException(status_code=404, detail="Detection not found")
    return det
