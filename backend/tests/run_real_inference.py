"""Run the actual AI upload/process API in an isolated database; never seed detections."""
import os
import sys
import json
from pathlib import Path
from uuid import uuid4
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

output = Path('output/real-inference') / str(uuid4())
output.mkdir(parents=True)
os.environ['DATABASE_URL'] = 'sqlite:///' + (output/'validation.sqlite3').resolve().as_posix()
os.environ['UPLOAD_DIR'] = str((output/'uploads').resolve())
os.environ['PROCESS_FPS'] = '5'
import cv2
from fastapi.testclient import TestClient
from app.main import app
from app.database.database import SessionLocal
from app.models.detection import Detection
from app.models.vehicle import Vehicle
from app.models.alert import Alert
from app.models.watchlist import Watchlist

results = {'note': 'Actual YOLO/ByteTrack/ANPR pipeline. No detection/plate/alert records seeded.'}
with TestClient(app) as client:
    login=client.post('/api/auth/login',data={'username':'admin@ai.local','password':'admin123'})
    login.raise_for_status()
    headers={'Authorization':'Bearer '+login.json()['access_token']}
    results['login']='PASS'
    camera=client.post('/api/cameras/',headers=headers,json={'camera_name':'AI validation camera','camera_code':'AI-VALIDATION','latitude':23.0225,'longitude':72.5714})
    camera.raise_for_status()
    camera_id=camera.json()['id']
    with SessionLocal() as db:
        db.add(Watchlist(registration_number='GJ01AB1234', category='VALIDATION', priority='HIGH'))
        db.commit()
    from app.services.stream_runtime import snapshot
    # The supplied plate-only sample and a short excerpt of existing traffic footage.
    for index, source in enumerate(['uploads/test_sample.mp4',str(next(p for p in Path('uploads').glob('*.mp4') if p.name != 'test_sample.mp4'))]):
        clip=output/f'input_{index}.mp4'
        cap=cv2.VideoCapture(source)
        fps=cap.get(cv2.CAP_PROP_FPS) or 15
        w,h=int(cap.get(3)),int(cap.get(4))
        writer=cv2.VideoWriter(str(clip),cv2.VideoWriter_fourcc(*'mp4v'),fps,(w,h))
        for _ in range(min(int(cap.get(7)),int(fps*6))):
            ok,frame=cap.read()
            if not ok: break
            writer.write(frame)
        cap.release(); writer.release()
        with clip.open('rb') as file:
            uploaded=client.post('/api/video/upload',headers=headers,files={'file':(clip.name,file,'video/mp4')})
        uploaded.raise_for_status()
        print('Running actual inference:',source,flush=True)
        processed=client.post(f'/api/video/{camera_id}/process',headers=headers,params={'file_path':uploaded.json()['file_path']})
        processed.raise_for_status()
        runtime = snapshot(camera_id)
        if runtime['last_error'] or not runtime['frames_processed']:
            raise RuntimeError(str(runtime))
        results[f'video_{index}_runtime']=runtime
        results[f'video_{index}_upload_process']='PASS'
    with SessionLocal() as db:
        results.update(detections=db.query(Detection).count(),tracked_detections=db.query(Detection).filter(Detection.tracking_id.is_not(None)).count(),vehicles=db.query(Vehicle).count(),plates=[v.number_plate for v in db.query(Vehicle).filter(Vehicle.number_plate.is_not(None)).all()],alerts=db.query(Alert).count())
    if results['plates']:
        plate=results['plates'][0]
        reference=client.post('/api/evidence/investigations',headers=headers,json={'vehicle_plate':plate})
        reference.raise_for_status()
        ref=reference.json()['id']
        summary=client.get(f'/api/evidence/investigations/{ref}',headers=headers).json()
        ids=[]
        for vehicle in summary['vehicles'][:3]:
            evidence=client.post('/api/evidence',headers=headers,json={'investigation_id':ref,'evidence_type':'PLATE_DETECTION','vehicle_id':vehicle['id']})
            evidence.raise_for_status(); ids.append(evidence.json()['id'])
        for fmt in ['pdf','zip']:
            exported=client.post('/api/evidence/export',headers=headers,json={'investigation_id':ref,'evidence_ids':ids,'format':fmt})
            exported.raise_for_status(); (output/f'report.{fmt}').write_bytes(exported.content)
        results['plate_to_exports']='PASS'
    else:
        results['plate_to_exports']='BLOCKED: actual footage produced no plate; no fabricated plate substituted'
(output/'results.json').write_text(json.dumps(results,indent=2))
print(json.dumps(results,indent=2),flush=True)
print('Artifacts:',output,flush=True)
