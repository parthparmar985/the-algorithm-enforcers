from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks
from sqlalchemy.orm import Session
from ...database.database import get_db
from ...auth.jwt import get_current_user
from ...models.user import User
import os
import shutil
from uuid import uuid4

router = APIRouter()

UPLOAD_DIR = os.getenv("UPLOAD_DIR", "uploads")
if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)

@router.post("/upload")
def upload_video(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user)
):
    if not file.filename.endswith((".mp4", ".avi", ".mkv")):
        raise HTTPException(status_code=400, detail="Invalid video format")
    
    file_extension = file.filename.split(".")[-1]
    unique_filename = f"{uuid4()}.{file_extension}"
    file_path = os.path.join(UPLOAD_DIR, unique_filename)
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    return {"message": "Video uploaded successfully", "file_path": file_path, "filename": unique_filename}

# Stub for AI processing
@router.post("/{camera_id}/process")
def process_video(
    camera_id: int,
    file_path: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Video file not found")
        
    # We instantiate DetectionService lazily because it loads heavy ML models
    from ...services.detection_service import DetectionService
    detector_service = DetectionService()
    
    background_tasks.add_task(detector_service.process_video_file, camera_id, file_path)
    return {"message": "AI processing started", "status": "processing"}
