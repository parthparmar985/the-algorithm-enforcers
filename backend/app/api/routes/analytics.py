from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ...database.database import get_db
from ...models.vehicle import Vehicle
from ...models.detection import Detection
from ...models.alert import Alert
from ...models.camera import Camera
from ...auth.jwt import get_current_user
from sqlalchemy import func

router = APIRouter()

@router.get("/summary")
def get_analytics_summary(db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    total_cameras = db.query(Camera).count()
    online_cameras = db.query(Camera).filter(Camera.status == "ONLINE").count()
    
    total_detections_today = db.query(Detection).count() # Simplified for MVP
    total_vehicles_today = db.query(Vehicle).count()
    active_alerts = db.query(Alert).filter(Alert.status == "NEW").count()
    critical_alerts = db.query(Alert).filter(Alert.severity == "CRITICAL", Alert.status == "NEW").count()
    plates_detected = db.query(Vehicle).filter(Vehicle.number_plate.isnot(None)).count()
    
    # Simple aggregations
    vehicle_types = db.query(Vehicle.vehicle_type, func.count(Vehicle.id)).group_by(Vehicle.vehicle_type).all()
    vehicle_types_dict = {k: v for k, v in vehicle_types}
    
    return {
        "summary": {
            "total_cameras": total_cameras,
            "online_cameras": online_cameras,
            "today_detections": total_detections_today,
            "today_vehicles": total_vehicles_today,
            "active_alerts": active_alerts,
            "critical_alerts": critical_alerts,
            "plates_detected": plates_detected
        },
        "charts": {
            "vehicle_types": vehicle_types_dict
        }
    }
