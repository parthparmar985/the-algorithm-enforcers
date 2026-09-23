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
            
        # 1. Image Enhancement for highly blurred CCTV video
        # Upscale the cropped image to make characters larger for OCR
        crop_en = cv2.resize(crop, None, fx=2.5, fy=2.5, interpolation=cv2.INTER_CUBIC)
        gray = cv2.cvtColor(crop_en, cv2.COLOR_BGR2GRAY)
        
        # Apply Unsharp Masking to heavily sharpen the blurred edges
        gaussian_blur = cv2.GaussianBlur(gray, (0, 0), 3.0)
        sharpened = cv2.addWeighted(gray, 2.0, gaussian_blur, -1.0, 0)
        
        # Denoise and equalize
        sharpened = cv2.bilateralFilter(sharpened, 11, 17, 17)
        sharpened = cv2.equalizeHist(sharpened)
        
        results = self.reader.readtext(sharpened)
        
        plate_text = ""
        best_conf = 0.0
        
        for (points, text, prob) in results:
            # Spatial filter: If the text is located in the top 25% of the vehicle's bounding box, 
            # it's almost certainly a background shop sign (like ELEGANCE) or billboard. Ignore it!
            points_y = [p[1] for p in points]
            text_center_y = sum(points_y) / 4.0
            image_h = sharpened.shape[0]
            
            if text_center_y < (image_h * 0.25):
                continue
                
            # Clean and normalize
            cleaned = re.sub(r'[^A-Z0-9]', '', text.upper())
            
            # Post-Processing Guess / AI correction for common errors in blurry videos
            if "GJ" in cleaned or "G1" in cleaned or "CJ" in cleaned or "6J" in cleaned or "GJ0" in cleaned:
                cleaned = cleaned.replace("G1", "GJ").replace("CJ", "GJ").replace("6J", "GJ")
            
            # Fix common OCR failures where digits are misread as letters before we enforce digit rules
            if len(cleaned) >= 5:
                # If a string has no digits, let's forcefully convert known letter-digit confusions if they are in typical digit positions
                # But to be safe, we just allow purely alphabetic strings if they are in the bottom 75% of the car
                # and are between 4 and 10 chars, as they're highly likely to be misread plates.
                pass
                
            if len(cleaned) >= 4 and prob > best_conf: 
                plate_text = cleaned
                best_conf = prob
                
        if plate_text:
            return plate_text, best_conf
            
        return None, 0.0
