import time

class RuleEngine:
    def __init__(self):
        self.stationary_track_counts = {}
        self.person_alert_cooldowns = {}
    
    def evaluate(self, camera_id, detections):
        alerts = []
        now = time.time()
        
        for det in detections:
            cls_name = det.get("class")
            track_id = det.get("track_id")
            
            # Stationary vehicle rule (tracks seen > 30 frames)
            if cls_name in ["car", "truck", "motorcycle", "bus"] and track_id:
                if track_id not in self.stationary_track_counts:
                    self.stationary_track_counts[track_id] = 1
                else:
                    self.stationary_track_counts[track_id] += 1
                    
                if self.stationary_track_counts[track_id] == 30:
                    alerts.append({
                        "camera_id": camera_id,
                        "alert_type": "STATIONARY_VEHICLE",
                        "severity": "HIGH",
                        "message": f"{cls_name.title()} remained stationary for excessive duration.",
                    })
                    
            # Person in restricted zone rule (deduplicated by track_id or 10s cooldown per camera)
            if cls_name == "person":
                key = f"person_{camera_id}_{track_id}" if track_id else f"person_{camera_id}_general"
                last_alert_time = self.person_alert_cooldowns.get(key, 0)
                
                # Cooldown: alert at most once every 10 seconds for the same person/camera
                if now - last_alert_time > 10.0:
                    self.person_alert_cooldowns[key] = now
                    alerts.append({
                        "camera_id": camera_id,
                        "alert_type": "UNAUTHORIZED_ACCESS",
                        "severity": "CRITICAL",
                        "message": "Person detected in a restricted or active monitoring zone.",
                    })
        
        return alerts

