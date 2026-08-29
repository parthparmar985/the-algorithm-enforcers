import os
import sys
from datetime import datetime, timedelta
import random

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database.database import SessionLocal
from app.models.vehicle import Vehicle
from app.models.detection import Detection
from app.models.camera import Camera

db = SessionLocal()

# Ensure we have a camera at least
cam = db.query(Camera).first()
if not cam:
    cam = Camera(camera_name="Main Gate Demo", camera_code="CAM-DEMO", location="Gate 1", status="ONLINE")
    db.add(cam)
    db.commit()
    db.refresh(cam)

print("Injecting valid dummy vehicles and detections for demo...")
plates = ["GJ01GH1234", "MH12AB5678", "DL01CZ9012", "RJ14XYZ123", "TN02AB4567", "UP16XY8888"]
types = ["car", "truck", "motorcycle", "car", "car", "bus"]

for i in range(6):
    last_time = datetime.utcnow() - timedelta(minutes=random.randint(1, 120))
    v = Vehicle(
        camera_id=cam.id,
        tracking_id=700 + i,
        vehicle_type=types[i],
        number_plate=plates[i],
        plate_confidence=random.uniform(0.70, 0.99),
        first_seen=last_time - timedelta(seconds=30),
        last_seen=last_time,
        snapshot_path=None
    )
    db.add(v)
    
    # Add multiple detections per vehicle to populate the Activity chart
    for j in range(random.randint(2,5)):
        d = Detection(
            camera_id=cam.id,
            detection_type="OBJECT",
            object_class=types[i],
            confidence=random.uniform(0.70, 0.95),
            tracking_id=700 + i,
            timestamp=last_time - timedelta(seconds=j*5),
            frame_number=5000 + i*10 + j,
            bounding_box="[10, 20, 100, 200]",
            snapshot_path=None
        )
        db.add(d)

db.commit()
print("Dummy Database populated successfully! Check the React Frontend.")
