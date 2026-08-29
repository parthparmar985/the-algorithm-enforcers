from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from ...database.database import get_db
from ...models.camera import Camera
from ...schemas.camera import CameraCreate, CameraUpdate, CameraResponse
from ...auth.jwt import get_current_user
from ...models.user import User

router = APIRouter()

@router.get("/", response_model=List[CameraResponse])
def get_cameras(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return db.query(Camera).all()

@router.post("/", response_model=CameraResponse)
def create_camera(
    camera: CameraCreate, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role != "ADMIN":
        raise HTTPException(status_code=403, detail="Only admins can manage cameras")
        
    db_cam = db.query(Camera).filter(Camera.camera_code == camera.camera_code).first()
    if db_cam:
        raise HTTPException(status_code=400, detail="Camera code already exists")
        
    new_cam = Camera(**camera.model_dump())
    db.add(new_cam)
    db.commit()
    db.refresh(new_cam)
    return new_cam

@router.get("/{id}", response_model=CameraResponse)
def get_camera(id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    camera = db.query(Camera).filter(Camera.id == id).first()
    if not camera:
        raise HTTPException(status_code=404, detail="Camera not found")
    return camera

@router.put("/{id}", response_model=CameraResponse)
def update_camera(
    id: int, 
    cam_update: CameraUpdate, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role != "ADMIN":
        raise HTTPException(status_code=403, detail="Only admins can manage cameras")
        
    camera = db.query(Camera).filter(Camera.id == id).first()
    if not camera:
        raise HTTPException(status_code=404, detail="Camera not found")
        
    for key, value in cam_update.model_dump(exclude_unset=True).items():
        setattr(camera, key, value)
        
    db.commit()
    db.refresh(camera)
    return camera

@router.delete("/{id}")
def delete_camera(
    id: int, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role != "ADMIN":
        raise HTTPException(status_code=403, detail="Only admins can manage cameras")
        
    camera = db.query(Camera).filter(Camera.id == id).first()
    if not camera:
        raise HTTPException(status_code=404, detail="Camera not found")
        
    db.delete(camera)
    db.commit()
    return {"message": "Camera deleted successfully"}
