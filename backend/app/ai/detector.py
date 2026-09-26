import cv2
import os
from ultralytics import YOLO

_detector_instance = None

def get_detector():
    global _detector_instance
    if _detector_instance is None:
        _detector_instance = VideoAnalyzer()
    return _detector_instance

class VideoAnalyzer:
    def __init__(self):
        model_path = os.getenv("YOLO_MODEL", "yolo11n.pt")
        # Initialize YOLO. It will download the weights if not present.
        self.model = YOLO(model_path)
        # Increase strictness to avoid 32% false-positive vehicle hallucinations (e.g., misclassifying distant cars as buses).
        self.confidence_threshold = float(os.getenv("YOLO_CONFIDENCE", "0.45"))
        # Focus on ALL vehicles, ignoring everything else
        self.target_classes = [2, 3, 5, 7] # 2: car, 3: motorcycle, 5: bus, 7: truck

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
            device=os.getenv("YOLO_DEVICE") or None,
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
                if class_name == "motorcycle":
                    class_name = "bike"
                
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

