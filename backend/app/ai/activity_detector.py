class RuleEngine:
    def __init__(self):
        self.stationary_track_counts = {}
    
    def evaluate(self, camera_id, detections):
        alerts = []
        for det in detections:
            cls_name = det.get("class")
            track_id = det.get("track_id")
            
            # Stationary vehicle rule (simplified for MVP: tracks seen > N frames)
            if cls_name in ["car", "truck", "motorcycle", "bus"] and track_id:
                if track_id not in self.stationary_track_counts:
                    self.stationary_track_counts[track_id] = 1
                else:
                    self.stationary_track_counts[track_id] += 1
                    
                if self.stationary_track_counts[track_id] == 30: # arbitrarily 30 frames
                    alerts.append({
                        "camera_id": camera_id,
                        "alert_type": "STATIONARY_VEHICLE",
                        "severity": "HIGH",
                        "message": f"{cls_name.title()} remained stationary for excessive duration.",
                    })
                    
            # Person in restricted zone rule (simplified for MVP: person detected)
            if cls_name == "person":
                # Assume whole view is restricted at night/after-hours (stub)
                alerts.append({
                    "camera_id": camera_id,
                    "alert_type": "UNAUTHORIZED_ACCESS",
                    "severity": "CRITICAL",
                    "message": "Person detected in a restricted or active monitoring zone.",
                })
        
        return alerts
