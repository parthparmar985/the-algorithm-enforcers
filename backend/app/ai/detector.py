import cv2
import os
from ultralytics import YOLO

class VideoAnalyzer:
    def __init__(self):
        model_path = os.getenv("YOLO_MODEL", "yolo11n.pt")
        # Initialize YOLO. It will download the weights if not present.
        self.model = YOLO(model_path)
        self.confidence_threshold = float(os.getenv("YOLO_CONFIDENCE", "0.45"))
        # Focus on people and vehicles
        self.target_classes = [0, 1, 2, 3, 5, 7] 

    def process_frame(self, frame, persist=True):
        """
        Runs YOLO object detection with built-in ByteTrack tracking.
        Returns a list of dicts with bounding boxes, classes, confidences, and track_ids.
        """
        # Using built-in ByteTrack config
        results = self.model.track(
            frame, 
            persist=persist,
            conf=self.confidence_threshold, 
            classes=self.target_classes, 
            tracker="bytetrack.yaml",
            verbose=False
        )
        
        detections = []
        if len(results) > 0:
            boxes = results[0].boxes
            
            # Not all boxes will have tracking IDs assigned immediately
            for i, box in enumerate(boxes):
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                cls = int(box.cls[0])
                conf = float(box.conf[0])
                class_name = self.model.names[cls]
                
                track_id = None
                if box.id is not None:
                    track_id = int(box.id[0])
                
                detections.append({
                    "bbox": [x1, y1, x2, y2],
                    "class": class_name,
                    "confidence": conf,
                    "track_id": track_id
                })
                
        return detections
