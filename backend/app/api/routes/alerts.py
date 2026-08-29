from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from ...database.database import get_db
from ...models.alert import Alert
from ...schemas.alert import AlertResponse, AlertUpdate
from ...auth.jwt import get_current_user

router = APIRouter()

@router.get("/", response_model=List[AlertResponse])
def get_alerts(limit: int = 100, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    return db.query(Alert).order_by(Alert.timestamp.desc()).limit(limit).all()

@router.put("/{id}/resolve", response_model=AlertResponse)
def resolve_alert(
    id: int, 
    update: AlertUpdate, 
    db: Session = Depends(get_db), 
    current_user = Depends(get_current_user)
):
    alert = db.query(Alert).filter(Alert.id == id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
        
    alert.status = update.status
    db.commit()
    db.refresh(alert)
    return alert
