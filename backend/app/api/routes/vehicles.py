from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from ...database.database import get_db
from ...models.vehicle import Vehicle
from ...schemas.vehicle import VehicleResponse
from ...auth.jwt import get_current_user

router = APIRouter()

@router.get("/", response_model=List[VehicleResponse])
def get_vehicles(limit: int = 100, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    return db.query(Vehicle).order_by(Vehicle.last_seen.desc()).limit(limit).all()

@router.get("/{id}", response_model=VehicleResponse)
def get_vehicle(id: int, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    veh = db.query(Vehicle).filter(Vehicle.id == id).first()
    if not veh:
        raise HTTPException(status_code=404, detail="Vehicle not found")
    return veh
