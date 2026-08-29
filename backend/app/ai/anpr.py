import easyocr
import cv2
import numpy as np
import re

class ANPREngine:
    def __init__(self):
        # Using CPU by default for MVP to avoid CUDA setup dependencies for the hackathon
        self.reader = easyocr.Reader(['en'], gpu=False) 
        
    def extract_number_plate(self, frame, bbox):
        """
        bbox is [x1, y1, x2, y2]
        """
        x1, y1, x2, y2 = map(int, bbox)
        
        # Ensure bbox is within frame boundaries
        h, w = frame.shape[:2]
        x1, y1 = max(0, x1), max(0, y1)
        x2, y2 = min(w, x2), min(h, y2)
        
        crop = frame[y1:y2, x1:x2]
        
        if crop.size == 0:
            return None, 0.0
            
        # Optional: preprocessing (grayscale)
        gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
        
        # Enhanced processing for better OCR read quality
        gray = cv2.bilateralFilter(gray, 11, 17, 17) # Noise reduction
        gray = cv2.equalizeHist(gray) # Contrast enhancement
        
        results = self.reader.readtext(gray)
        
        plate_text = ""
        best_conf = 0.0
        
        for (points, text, prob) in results:
            # Clean text (remove special characters)
            cleaned = re.sub(r'[^A-Z0-9]', '', text.upper())
            # Simple heuristic for plate length
            if len(cleaned) >= 4 and prob > best_conf: 
                plate_text = cleaned
                best_conf = prob
                
        if plate_text:
            return plate_text, best_conf
            
        return None, 0.0
