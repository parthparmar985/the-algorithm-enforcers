import easyocr
import cv2
import numpy as np
from .plate_utils import is_valid_indian_plate, normalize_ocr_plate, normalize_plate

_anpr_instance = None

def get_anpr():
    global _anpr_instance
    if _anpr_instance is None:
        _anpr_instance = ANPREngine()
    return _anpr_instance

class ANPREngine:
    def __init__(self):
        # Using CPU by default for MVP to avoid CUDA setup dependencies for the hackathon
        self.reader = easyocr.Reader(['en'], gpu=False) 
        
    def extract_number_plate_with_audit(self, frame, bbox):
        """Return normalized plate, confidence, and best raw OCR candidate."""
        x1, y1, x2, y2 = map(int, bbox)
        
        # Ensure bbox is within frame boundaries
        h, w = frame.shape[:2]
        x1, y1 = max(0, x1), max(0, y1)
        x2, y2 = min(w, x2), min(h, y2)
        
        crop = frame[y1:y2, x1:x2]
        
        if crop.size == 0:
            return None, 0.0
            
        crop_h, crop_w = crop.shape[:2]
        if crop_h < 180:
            scale = min(3.0, 180 / max(crop_h, 1))
            crop = cv2.resize(crop, (int(crop_w * scale), int(crop_h * scale)), interpolation=cv2.INTER_CUBIC)

        # Plates are commonly in the lower two thirds. Retain the full crop as a
        # fallback because camera angle and vehicle orientation are not known.
        lower = crop[int(crop.shape[0] * 0.30):, :]
        vehicle_gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
        _threshold, bright = cv2.threshold(vehicle_gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        contours, _hierarchy = cv2.findContours(bright, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
        plate_regions = []
        crop_area = crop.shape[0] * crop.shape[1]
        for contour in contours:
            rx, ry, rw, rh = cv2.boundingRect(contour)
            aspect = rw / max(rh, 1)
            area_ratio = (rw * rh) / max(crop_area, 1)
            if 1.8 <= aspect <= 8.0 and 0.002 <= area_ratio <= 0.25 and rw >= 60 and ry >= crop.shape[0] * 0.20:
                margin = max(2, int(rh * 0.08))
                plate_regions.append((rw * rh, crop[max(0, ry - margin):min(crop.shape[0], ry + rh + margin), max(0, rx - margin):min(crop.shape[1], rx + rw + margin)]))
        plate_regions.sort(key=lambda item: item[0], reverse=True)
        gray = cv2.cvtColor(lower, cv2.COLOR_BGR2GRAY)
        gray = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8)).apply(gray)
        sharpened = cv2.filter2D(gray, -1, np.array([[0, -1, 0], [-1, 5, -1], [0, -1, 0]]))
        variants = [region for _area, region in plate_regions[:3]]
        variants += [lower, sharpened] if variants else [crop, lower, sharpened]

        all_candidates = []
        for variant in variants:
            results = self.reader.readtext(variant, detail=1, allowlist="ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789")
            texts = []
            confidences = []
            for _points, raw_text, probability in results:
                raw_text = str(raw_text).strip()
                if raw_text:
                    texts.append(raw_text)
                    confidences.append(float(probability))
                    all_candidates.append((raw_text, float(probability)))
            if len(texts) > 1:
                all_candidates.append(("".join(texts), sum(confidences) / len(confidences)))
            confident_valid = [(normalize_ocr_plate(text, probability), probability, text) for text, probability in all_candidates
                               if probability >= 0.60 and is_valid_indian_plate(normalize_ocr_plate(text, probability))]
            if confident_valid:
                normalized, probability, raw_text = max(confident_valid, key=lambda item: item[1])
                return normalized, probability, raw_text

        best_raw = None
        best_raw_confidence = 0.0
        best_plate = None
        best_plate_confidence = 0.0
        for raw_text, probability in all_candidates:
            if probability > best_raw_confidence:
                best_raw, best_raw_confidence = raw_text, probability
            normalized = normalize_ocr_plate(raw_text, probability)
            if probability >= 0.35 and is_valid_indian_plate(normalized) and probability > best_plate_confidence:
                best_plate, best_plate_confidence = normalized, probability
        return best_plate, best_plate_confidence, best_raw

    def extract_number_plate(self, frame, bbox):
        plate, confidence, _raw = self.extract_number_plate_with_audit(frame, bbox)
        return plate, confidence
