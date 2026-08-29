from sqlalchemy.orm import Session
from ..models.detection import Detection
from ..models.vehicle import Vehicle
from ..ai.detector import VideoAnalyzer
from ..ai.anpr import ANPREngine
from datetime import datetime
import cv2
import json
import os
from uuid import uuid4
import asyncio
from ..models.alert import Alert
from ..models.watchlist import Watchlist
from ..ai.activity_detector import RuleEngine
from ..websocket.manager import manager
from ..database.database import SessionLocal

class DetectionService:
    def __init__(self):
        self.detector = VideoAnalyzer()
        self.rule_engine = RuleEngine()
        self.anpr = ANPREngine()
        
        self.snapshot_dir = os.path.join(os.getenv("UPLOAD_DIR", "uploads"), "snapshots")
        if not os.path.exists(self.snapshot_dir):
            os.makedirs(self.snapshot_dir)
            
    def process_video_file(self, camera_id: int, video_path: str):
        # We need a new session since this runs in a background thread
        db = SessionLocal()
        try:
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                print(f"Error opening video {video_path}")
                return
                
            fps = cap.get(cv2.CAP_PROP_FPS)
            process_fps = int(os.getenv("PROCESS_FPS", 15))
            if process_fps <= 0 or process_fps > fps:
                process_fps = fps
                
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            frame_skip = max(1, int(fps / process_fps))
            
            frame_idx = 0
            
            active_vehicles = {}
            
            while cap.isOpened():
                ret, frame = cap.read()
                if not ret:
                    break
                    
                frame_idx += 1
                if frame_idx % frame_skip != 0:
                    continue
                
                # Enhance frame quality for robust AI detection under varying conditions
                frame = cv2.convertScaleAbs(frame, alpha=1.1, beta=5)
                
                detections = self.detector.process_frame(frame, persist=True)
                
                for det in detections:
                    cls_name = det["class"]
                    conf = det["confidence"]
                    track_id = det["track_id"]
                    bbox = det["bbox"]
                    
                    plate_text = None
                    plate_conf = 0.0
                    
                    if cls_name in ["car", "truck", "bus", "motorcycle"]:
                        run_anpr = False
                        
                        # Only run heavy OCR if this is a new object, or if we haven't found a high-confidence plate yet.
                        # Throttle OCR attempts by only checking every 5th processed frame to save massive CPU time.
                        # Improve multi-frame validation by heavily re-trying if confidence is less than 0.85
                        if track_id not in active_vehicles:
                            run_anpr = True
                        else:
                            v = active_vehicles[track_id]
                            if (not v.plate_confidence or v.plate_confidence < 0.85) and (frame_idx % int(frame_skip * 3) == 0):
                                run_anpr = True
                                
                        if run_anpr:
                            plate_text, plate_conf = self.anpr.extract_number_plate(frame, bbox)
                        
                    snapshot_path = None
                    if plate_text or (track_id and track_id not in active_vehicles):
                        snapshot_filename = f"snap_{camera_id}_{track_id}_{uuid4()}.jpg"
                        snapshot_path = os.path.join(self.snapshot_dir, snapshot_filename)
                        
                        # Just crop bounding box for snapshot
                        x1, y1, x2, y2 = map(int, bbox)
                        h, w = frame.shape[:2]
                        x1, y1 = max(0, x1), max(0, y1)
                        x2, y2 = min(w, x2), min(h, y2)
                        
                        crop = frame[y1:y2, x1:x2]
                        if crop.size > 0:
                            cv2.imwrite(snapshot_path, crop)
                        else:
                            snapshot_path = None
                        
                    db_detection = Detection(
                        camera_id=camera_id,
                        detection_type="OBJECT",
                        object_class=cls_name,
                        confidence=conf,
                        tracking_id=track_id,
                        timestamp=datetime.utcnow(),
                        frame_number=frame_idx,
                        bounding_box=json.dumps(bbox),
                        snapshot_path=snapshot_path
                    )
                    db.add(db_detection)
                    
                    if cls_name in ["car", "truck", "bus", "motorcycle"] and track_id:
                        if track_id in active_vehicles:
                            v = active_vehicles[track_id]
                            v.last_seen = datetime.utcnow()
                            if plate_text and (not v.number_plate or plate_conf > (v.plate_confidence or 0)):
                                v.number_plate = plate_text
                                v.plate_confidence = plate_conf
                                v.snapshot_path = snapshot_path or v.snapshot_path
                        else:
                            v = Vehicle(
                                camera_id=camera_id,
                                tracking_id=track_id,
                                vehicle_type=cls_name,
                                number_plate=plate_text,
                                plate_confidence=plate_conf,
                                first_seen=datetime.utcnow(),
                                last_seen=datetime.utcnow(),
                                snapshot_path=snapshot_path
                            )
                            db.add(v)
                            active_vehicles[track_id] = v
                            
                        # Continuous Watchlist Matching
                        if plate_text and plate_conf > 0.65:
                            match = db.query(Watchlist).filter(Watchlist.registration_number == plate_text, Watchlist.status == "ACTIVE").first()
                            if match:
                                # Fire immediate alert for Watchlist match
                                alert_msg = f"Watchlist Match! Priority: {match.priority}. Category: {match.category}"
                                db_alert = Alert(
                                    camera_id=camera_id,
                                    alert_type="WATCHLIST_MATCH",
                                    severity=match.priority,
                                    message=alert_msg,
                                    timestamp=datetime.utcnow(),
                                    snapshot_path=snapshot_path
                                )
                                db.add(db_alert)
                                db.commit()
                                db.refresh(db_alert)
                                
                                ws_payload = {
                                    "alert_id": db_alert.id,
                                    "alert_type": db_alert.alert_type,
                                    "severity": db_alert.severity,
                                    "camera_id": db_alert.camera_id,
                                    "message": db_alert.message,
                                    "timestamp": db_alert.timestamp.isoformat(),
                                    "snapshot": db_alert.snapshot_path
                                }
                                try:
                                    asyncio.run(manager.broadcast_alert(ws_payload))
                                except Exception:
                                    pass
                                    
                # Rule Engine checks
                new_alerts = self.rule_engine.evaluate(camera_id, detections)
                for alert_data in new_alerts:
                    # Save to DB
                    db_alert = Alert(
                        camera_id=alert_data["camera_id"],
                        alert_type=alert_data["alert_type"],
                        severity=alert_data["severity"],
                        message=alert_data["message"],
                        timestamp=datetime.utcnow(),
                        snapshot_path=None
                    )
                    db.add(db_alert)
                    db.commit()
                    db.refresh(db_alert)
                    
                    # Broadcast
                    ws_payload = {
                        "alert_id": db_alert.id,
                        "alert_type": db_alert.alert_type,
                        "severity": db_alert.severity,
                        "camera_id": db_alert.camera_id,
                        "message": db_alert.message,
                        "timestamp": db_alert.timestamp.isoformat(),
                        "snapshot": db_alert.snapshot_path
                    }
                    try:
                        asyncio.run(manager.broadcast_alert(ws_payload))
                    except Exception as e:
                        print("Broadcast error:", e)

                db.commit()
                
                # Progress Reporting
                if total_frames > 0 and frame_idx % 10 == 0:
                    percent = int((frame_idx / total_frames) * 100)
                    ws_payload = {
                        "type": "PROGRESS",
                        "percentage": percent,
                        "frame": frame_idx,
                        "total": total_frames
                    }
                    try:
                        asyncio.run(manager.broadcast_progress(ws_payload))
                    except Exception as e:
                        pass
                
            # Send completing progress event
            if total_frames > 0:
                try:
                    asyncio.run(manager.broadcast_progress({"type": "PROGRESS", "percentage": 100}))
                except Exception:
                    pass
                
            cap.release()
        finally:
            db.close()
