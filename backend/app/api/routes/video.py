from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks
from sqlalchemy.orm import Session
from ...database.database import get_db
from ...auth.jwt import get_current_user
from ...models.user import User
import os
import shutil
from uuid import uuid4
import cv2
import time
import numpy as np
from fastapi.responses import StreamingResponse
from ...models.camera import Camera
from ...services.camera_url import normalized_capture_url, validate_stream_url

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
    # Path traversal protection: resolve absolute path and check if within UPLOAD_DIR
    abs_upload_dir = os.path.abspath(UPLOAD_DIR)
    abs_file_path = os.path.abspath(file_path)
    
    if not abs_file_path.startswith(abs_upload_dir):
        raise HTTPException(status_code=400, detail="Invalid video path: path traversal forbidden")

    if not os.path.exists(abs_file_path):
        raise HTTPException(status_code=404, detail="Video file not found")
        
    # We instantiate DetectionService lazily because it loads heavy ML models
    from ...services.detection_service import DetectionService
    detector_service = DetectionService()
    
    background_tasks.add_task(detector_service.process_video_file, camera_id, abs_file_path)
    return {"message": "AI processing started", "status": "processing"}

@router.post("/{camera_id}/start-live")
def start_live_inference(
    camera_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    camera = db.query(Camera).filter(Camera.id == camera_id).first()
    if not camera:
        raise HTTPException(status_code=404, detail="Camera not found")
    try:
        stream_url = validate_stream_url(camera.stream_url)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not stream_url:
        raise HTTPException(status_code=400, detail="Camera has no valid Stream URL configured.")
    stream_url = normalized_capture_url(stream_url)
        
    from ...services.detection_service import DetectionService
    detector_service = DetectionService()
    
    background_tasks.add_task(detector_service.process_video_file, camera_id, stream_url)
    return {"message": "Live Continuous ML Inference engaged for this Node.", "status": "runtime_active"}

def generate_mock_frames(camera: Camera):
    """Generates continuous video frames simulated as real CCTV feed."""
    width, height = 640, 360
    while True:
        # Create a dark sophisticated background representing a camera feed
        frame = np.zeros((height, width, 3), dtype=np.uint8)
        
        # Draw some subtle dynamic elements (like a panning target or scanline)
        t = time.time()
        scanline_y = int((t % 2) / 2 * height)
        cv2.line(frame, (0, scanline_y), (width, scanline_y), (50, 150, 50), 1)
        
        # Add random noise for static effect
        noise = np.random.randint(0, 30, (height, width, 3), dtype=np.uint8)
        frame = cv2.add(frame, noise)

        # Overlay Camera Info
        cam_text = f"{camera.camera_code} | {camera.camera_name}"
        cv2.putText(frame, cam_text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        
        # Overlay Timestamp
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        cv2.putText(frame, timestamp, (10, height - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 1)
        
        # Record indicator
        if int(t * 2) % 2 == 0:
            cv2.circle(frame, (width - 25, 25), 8, (0, 0, 255), -1)

        ret, buffer = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
        if not ret:
            continue
            
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
        
        # Target 15 FPS
        time.sleep(1/15)

@router.get("/{camera_id}/stream")
def stream_video(
    camera_id: int, 
    db: Session = Depends(get_db)
):
    camera = db.query(Camera).filter(Camera.id == camera_id).first()
    if not camera:
        raise HTTPException(status_code=404, detail="Camera not found")
        
    def generate_real_frames(url):
        url = normalized_capture_url(url)
        cap = cv2.VideoCapture(url)
        try:
            # If the connection fails, yield a red Error Frame instead of crashing
            if not cap.isOpened():
                frame = np.zeros((360, 640, 3), dtype=np.uint8)
                frame[:] = (0, 0, 50)
                cv2.putText(frame, "CCTV CONNECTION FAILED", (80, 160), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 3)
                cv2.putText(frame, "Please verify device is active on network", (80, 230), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1)
                ret, buffer = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
                if ret:
                    yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
                return

            while cap.isOpened():
                ret, frame = cap.read()
                if not ret:
                    break
            
                # Resize for optimal dashboard streaming bandwidth
                frame = cv2.resize(frame, (640, 360))
            
            # Overlay basic node info for authenticity
                cam_text = f"LIVE | {camera.camera_code}"
                cv2.putText(frame, cam_text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            
                ret, buffer = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 60])
                if ret:
                    yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
            
            # Limit fps to save network overload in browsers
                time.sleep(1/15)
        finally:
            cap.release()

    # If the camera has a real Stream URL defined in the database, capture the real feed!
    if camera.stream_url:
        try:
            stream_url = validate_stream_url(camera.stream_url)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return StreamingResponse(generate_real_frames(stream_url), media_type="multipart/x-mixed-replace; boundary=frame")
        
    # Otherwise fallback to the simulation engine for hackathon demo
    return StreamingResponse(generate_mock_frames(camera), media_type="multipart/x-mixed-replace; boundary=frame")

