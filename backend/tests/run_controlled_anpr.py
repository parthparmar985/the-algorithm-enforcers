"""Controlled end-to-end ANPR validation using a real detected car plus a clearly rendered Indian plate."""
import json
import os
import sys
from pathlib import Path
from uuid import uuid4

import cv2

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
output = Path('output/controlled-anpr') / str(uuid4())
output.mkdir(parents=True)
os.environ['DATABASE_URL'] = 'sqlite:///' + (output / 'validation.sqlite3').resolve().as_posix()
os.environ['UPLOAD_DIR'] = str((output / 'uploads').resolve())
os.environ['PROCESS_FPS'] = '5'
os.environ['ANPR_RETRY_INTERVAL'] = '30'

from fastapi.testclient import TestClient
from app.main import app
from app.ai.anpr import ANPREngine
from app.ai.detector import VideoAnalyzer
from app.database.database import SessionLocal
from app.models.alert import Alert
from app.models.detection import Detection
from app.models.vehicle import Vehicle
from app.models.watchlist import Watchlist

plate = 'GJ01AB1234'
source = Path('uploads/088a8489-f35c-4fa9-b8fc-d77250832ad0.mp4')
cap = cv2.VideoCapture(str(source))
detector = VideoAnalyzer()
chosen = None
for frame_index in range(150):
    ok, frame = cap.read()
    if not ok:
        break
    if frame_index % 5:
        continue
    vehicles = [item for item in detector.process_frame(frame, persist=False) if item['class'] == 'car']
    vehicles.sort(key=lambda item: (item['bbox'][2] - item['bbox'][0]) * (item['bbox'][3] - item['bbox'][1]), reverse=True)
    if vehicles and vehicles[0]['bbox'][2] - vehicles[0]['bbox'][0] >= 250:
        chosen = frame.copy(), vehicles[0]['bbox']
        break
cap.release()
if not chosen:
    raise RuntimeError('No suitably large real car found in controlled source footage')

frame, bbox = chosen
x1, y1, x2, y2 = bbox
vehicle_width, vehicle_height = x2 - x1, y2 - y1
plate_width = max(260, int(vehicle_width * .48))
plate_height = max(58, int(plate_width * .20))
cx, cy = (x1 + x2) // 2, y1 + int(vehicle_height * .72)
px1, py1 = max(x1 + 4, cx - plate_width // 2), max(y1 + 4, cy - plate_height // 2)
px2, py2 = min(x2 - 4, px1 + plate_width), min(y2 - 4, py1 + plate_height)
cv2.rectangle(frame, (px1, py1), (px2, py2), (245, 245, 245), -1)
cv2.rectangle(frame, (px1, py1), (px2, py2), (15, 15, 15), 3)
font = cv2.FONT_HERSHEY_SIMPLEX
scale = 1.5
while cv2.getTextSize(plate, font, scale, 3)[0][0] > (px2 - px1 - 12):
    scale -= .05
size = cv2.getTextSize(plate, font, scale, 3)[0]
origin = (px1 + ((px2 - px1) - size[0]) // 2, py1 + ((py2 - py1) + size[1]) // 2)
cv2.putText(frame, plate, origin, font, scale, (10, 10, 10), 3, cv2.LINE_AA)
cv2.imwrite(str(output / 'controlled_frame.jpg'), frame)

anpr = ANPREngine()
read, confidence, raw = anpr.extract_number_plate_with_audit(frame, bbox)
if read != plate:
    raise RuntimeError(f'Controlled OCR did not produce {plate}: normalized={read}, raw={raw}, confidence={confidence}')

height, width = frame.shape[:2]
video = output / 'controlled_vehicle.mp4'
writer = cv2.VideoWriter(str(video), cv2.VideoWriter_fourcc(*'mp4v'), 15, (width, height))
for _ in range(18):
    writer.write(frame)
writer.release()

result = {'source': str(source), 'controlled_frame': str(output / 'controlled_frame.jpg'),
          'ocr_raw': raw, 'ocr_normalized': read, 'ocr_confidence': confidence,
          'control_disclosure': 'Plate characters were rendered onto a real YOLO-detected car at readable resolution.'}
with TestClient(app) as client:
    login = client.post('/api/auth/login', data={'username': 'admin@ai.local', 'password': 'admin123'})
    login.raise_for_status()
    headers = {'Authorization': 'Bearer ' + login.json()['access_token']}
    cameras = []
    for index, coordinates in enumerate([(23.0225, 72.5714), (23.0325, 72.5814)], 1):
        response = client.post('/api/cameras/', headers=headers, json={'camera_name': f'Controlled Camera {index}', 'camera_code': f'CTRL-{index}', 'location': f'Ahmedabad checkpoint {index}', 'latitude': coordinates[0], 'longitude': coordinates[1]})
        response.raise_for_status(); cameras.append(response.json())
    with SessionLocal() as db:
        db.add(Watchlist(registration_number=plate, category='CONTROLLED VALIDATION', priority='HIGH'))
        db.commit()
    for camera in cameras:
        with video.open('rb') as file:
            uploaded = client.post('/api/video/upload', headers=headers, files={'file': (video.name, file, 'video/mp4')})
        uploaded.raise_for_status()
        processed = client.post(f"/api/video/{camera['id']}/process", headers=headers, params={'file_path': uploaded.json()['file_path']})
        processed.raise_for_status()
    with SessionLocal() as db:
        result.update(detections=db.query(Detection).count(), tracked_detections=db.query(Detection).filter(Detection.tracking_id.is_not(None)).count(),
                      stored_plates=[v.number_plate for v in db.query(Vehicle).filter(Vehicle.number_plate.is_not(None)).all()],
                      stored_raw_text=[v.plate_raw_text for v in db.query(Vehicle).filter(Vehicle.number_plate.is_not(None)).all()], alerts=db.query(Alert).count())
    search = client.get('/api/search/investigations', headers=headers, params={'registration_number': 'GJ-01-AB-1234', 'vehicle_type': 'car', 'location': 'Ahmedabad'})
    search.raise_for_status(); result['search_results'] = len(search.json())
    timeline = client.get(f'/api/search/trace/{plate}', headers=headers)
    timeline.raise_for_status(); result['timeline_events'] = len(timeline.json())
    result['route_distance_km'] = sum(item['distance_km'] for item in timeline.json())
    reference = client.post('/api/evidence/investigations', headers=headers, json={'vehicle_plate': plate})
    reference.raise_for_status(); reference_id = reference.json()['id']
    evidence_ids = []
    for event in timeline.json():
        evidence = client.post('/api/evidence', headers=headers, json={'investigation_id': reference_id, 'evidence_type': 'PLATE_DETECTION', 'vehicle_id': event['vehicle_id'], 'description': 'Controlled ANPR validation'})
        evidence.raise_for_status(); evidence_ids.append(evidence.json()['id'])
    result['duplicate_evidence_id'] = client.post('/api/evidence', headers=headers, json={'investigation_id': reference_id, 'evidence_type': 'PLATE_DETECTION', 'vehicle_id': timeline.json()[0]['vehicle_id']}).json()['id']
    for export_format in ['pdf', 'zip']:
        exported = client.post('/api/evidence/export', headers=headers, json={'investigation_id': reference_id, 'evidence_ids': evidence_ids, 'format': export_format})
        exported.raise_for_status(); (output / f'investigation.{export_format}').write_bytes(exported.content)
    result['evidence_ids'] = evidence_ids

if plate not in result['stored_plates'] or result['search_results'] < 2 or result['timeline_events'] < 2 or not result['alerts']:
    raise RuntimeError(f'Controlled workflow incomplete: {result}')
(output / 'results.json').write_text(json.dumps(result, indent=2))
print(json.dumps(result, indent=2))
print('Artifacts:', output)
