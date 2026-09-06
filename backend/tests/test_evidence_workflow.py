"""Executable API/export integration checks; fixture data is explicitly synthetic."""
import os
import tempfile
import unittest
import hashlib
import json
import threading
import time
from pathlib import Path
from io import BytesIO
from datetime import datetime, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from zipfile import ZipFile
from unittest.mock import patch

scratch = tempfile.TemporaryDirectory()
os.environ["DATABASE_URL"] = "sqlite:///" + str(Path(scratch.name) / "test.db")
os.environ["UPLOAD_DIR"] = str(Path(scratch.name) / "uploads")
from fastapi.testclient import TestClient
from PIL import Image
from pypdf import PdfReader
from app.main import app
from app.database.database import SessionLocal, engine
from app.models.camera import Camera
from app.models.vehicle import Vehicle
from app.models.detection import Detection
from app.models.alert import Alert
from app.models.user import User
from app.models.evidence import Evidence
from app.services.evidence_service import snapshot_bytes
from app.ai.plate_utils import normalize_plate, normalize_ocr_plate, is_valid_indian_plate, plates_match
from app.services.natural_investigation import INDIA_TZ, parse_natural_query
from app.services.camera_health import ProbeResult, probe_stream
from fastapi import HTTPException


class EvidenceWorkflow(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        cls.client.__enter__()
        cls.headers = {}
        for name in ['owner', 'other']:
            response = cls.client.post('/api/auth/register', json={'name': name, 'email': f'{name}@example.com', 'password': 'evidence-test-pass', 'role': 'ADMIN'})
            assert response.status_code == 200, response.text
            assert response.json()['role'] == 'OPERATOR'
            token = cls.client.post('/api/auth/login', data={'username': f'{name}@example.com', 'password': 'evidence-test-pass'}).json()['access_token']
            cls.headers[name] = {'Authorization': f'Bearer {token}'}
        token = cls.client.post('/api/auth/login', data={'username': 'admin@ai.local', 'password': 'admin123'}).json()['access_token']
        cls.headers['admin'] = {'Authorization': f'Bearer {token}'}
        cls.path = Path(os.environ['UPLOAD_DIR']) / 'snapshots' / 'test.jpg'
        cls.path.parent.mkdir(parents=True)
        Image.new('RGB', (600, 240), '#314c70').save(cls.path)
        cls.original = cls.path.read_bytes()
        now = datetime(2026, 9, 4, 10, 32, 14)
        with SessionLocal() as db:
            for n in range(2):
                c = Camera(camera_name=f'Test Camera {n+1}', camera_code=f'TEST-{n+1}', location=f'Ahmedabad checkpoint {n+1}', latitude=23.02+n*.01, longitude=72.57+n*.01)
                db.add(c); db.flush()
                t = now + timedelta(minutes=n*10)
                db.add(Vehicle(camera_id=c.id, tracking_id=42, vehicle_type='car', number_plate='GJ01AB1234', plate_confidence=.92, first_seen=t, last_seen=t+timedelta(seconds=10), snapshot_path=str(cls.path)))
                db.add(Detection(camera_id=c.id, tracking_id=42, detection_type='OBJECT', object_class='car', confidence=.91, timestamp=t, snapshot_path=str(cls.path)))
            db.add(Alert(camera_id=1, alert_type='WATCHLIST_MATCH', severity='HIGH', message='Synthetic test alert', timestamp=now, snapshot_path=str(cls.path)))
            db.add(Alert(camera_id=1, alert_type='UNRELATED', severity='LOW', message='Must not be associated', timestamp=now))
            db.commit()
        cls.reference = cls.client.post('/api/evidence/investigations', headers=cls.headers['owner'], json={'vehicle_plate':'GJ01AB1234'}).json()['id']

    @classmethod
    def tearDownClass(cls):
        cls.client.__exit__(None,None,None)
        engine.dispose()

    def request(self, method, url, **kwargs):
        return self.client.request(method, '/api/evidence'+url, headers=self.headers['owner'], **kwargs)

    def add(self, **kwargs):
        response = self.request('POST','',json={'investigation_id':self.reference, **kwargs})
        self.assertEqual(response.status_code,200,response.text)
        return response.json()

    def test_complete_evidence_export(self):
        entries = [self.add(evidence_type='PLATE_DETECTION',vehicle_id=1,description='Synthetic validation snapshot'),
                   self.add(evidence_type='DETECTION',detection_id=2),self.add(evidence_type='ALERT',alert_id=1),self.add(evidence_type='ROUTE_TRACE')]
        self.assertEqual(self.add(evidence_type='PLATE_DETECTION',vehicle_id=1)['id'],entries[0]['id'])
        summary = self.request('GET',f'/investigations/{self.reference}').json()
        self.assertEqual(summary['summary']['detection_count'],2)
        self.assertEqual(summary['summary']['alert_count'],1)
        self.assertEqual(summary['summary']['camera_count'],2)
        self.assertGreater(summary['summary']['total_route_distance_km'], 0)
        self.assertEqual(len(summary['route']),2)
        self.assertEqual(len(self.request('GET','',params={'investigation_id':self.reference,'plate':'GJ01AB1234','camera_id':1,'evidence_type':'ALERT','start_time':'2026-09-04T00:00:00','end_time':'2026-09-05T00:00:00'}).json()),1)
        self.assertEqual(self.request('GET','',params={'plate':'NO_MATCH'}).json(),[])
        preview=self.request('GET',f"/{entries[0]['id']}/file")
        self.assertEqual(preview.content,self.original)
        self.assertNotIn(str(self.path),self.request('GET',f"/{entries[0]['id']}").text)
        payload={'investigation_id':self.reference,'evidence_ids':[e['id'] for e in entries]+[entries[0]['id']]}
        output=Path('output/evidence-validation'); output.mkdir(parents=True,exist_ok=True)
        pdf=self.request('POST','/export',json={**payload,'format':'pdf'})
        self.assertEqual(pdf.status_code,200,pdf.text[:100] if pdf.status_code!=200 else '')
        (output/'report.pdf').write_bytes(pdf.content)
        reader=PdfReader(BytesIO(pdf.content))
        text='\n'.join(p.extract_text() for p in reader.pages)
        for value in ['GJ01AB1234',self.reference,'Synthetic validation snapshot','Test Camera 1','Human verification required',entries[0]['sha256']]:
            self.assertIn(value,text)
        # ReportLab reuses identical image XObjects; count actual image placements.
        self.assertEqual(sum(sum(op == b'Do' for _,op in p.get_contents().operations) for p in reader.pages),3)
        package=self.request('POST','/export',json={**payload,'format':'zip'})
        self.assertEqual(package.status_code,200)
        (output/'package.zip').write_bytes(package.content)
        with ZipFile(BytesIO(package.content)) as archive:
            expected={'investigation/report.pdf','investigation/metadata.json','investigation/timeline.json','investigation/route.json'} | {f"investigation/evidence/{e['file_name']}" for e in entries if e['file_name']}
            self.assertEqual(set(archive.namelist()),expected)
            self.assertTrue(all(not n.startswith('/') and '..' not in Path(n).parts and ':' not in n for n in archive.namelist()))
            archive.extractall(output/'extracted')
            meta=json.loads(archive.read('investigation/metadata.json'))
            self.assertEqual(len(meta['evidence']),4)
            for e in meta['evidence']:
                if e['file_name']:
                    content=(output/'extracted'/'investigation'/'evidence'/e['file_name']).read_bytes()
                    self.assertEqual(hashlib.sha256(content).hexdigest(),e['sha256'])
        print('Validated PDF text, 3 embedded snapshots, ZIP extraction, exact manifest and SHA-256.')

    def test_camera_health_transitions_and_real_probe(self):
        self.assertIsNotNone(getattr(app.state, 'camera_health_task', None))
        with SessionLocal() as db:
            camera = db.query(Camera).filter(Camera.id == 1).one()
            camera.health_status = 'UNKNOWN'; camera.consecutive_failures = 0
            camera.stream_available = False; camera.last_health_check = None
            db.query(Alert).filter(Alert.camera_id == 1, Alert.alert_type.in_(['CAMERA_OFFLINE', 'CAMERA_RECOVERED'])).delete(synchronize_session=False)
            db.commit()
        listed = self.client.get('/api/cameras/', headers=self.headers['owner'])
        self.assertEqual(listed.status_code, 200, listed.text)
        self.assertIsNotNone(listed.json()[0]['last_detection_at'])

        failure = ProbeResult(False, 42, 'SIMULATION: controlled connection failure')
        with patch('app.services.camera_health.probe_stream', return_value=failure):
            first = self.client.post('/api/cameras/1/health-check', headers=self.headers['owner'])
            self.assertEqual(first.status_code, 200, first.text)
            self.assertEqual(first.json()['health_status'], 'DEGRADED')
            with self.client.websocket_connect('/ws/alerts') as websocket:
                second = self.client.post('/api/cameras/1/health-check', headers=self.headers['owner'])
                self.assertEqual(second.json()['health_status'], 'OFFLINE')
                notice = websocket.receive_json()
                self.assertEqual(notice['alert_type'], 'CAMERA_OFFLINE')
            self.assertEqual(self.client.post('/api/cameras/1/health-check', headers=self.headers['owner']).json()['health_status'], 'OFFLINE')

        with SessionLocal() as db:
            self.assertEqual(db.query(Alert).filter_by(camera_id=1, alert_type='CAMERA_OFFLINE').count(), 1)

        success = ProbeResult(True, 80, 'SIMULATION: controlled valid frame')
        with patch('app.services.camera_health.probe_stream', return_value=success):
            with self.client.websocket_connect('/ws/alerts') as websocket:
                recovered = self.client.post('/api/cameras/1/health-check', headers=self.headers['owner'])
                self.assertEqual(recovered.json()['health_status'], 'ONLINE')
                self.assertIsNotNone(recovered.json()['last_frame_at'])
                self.assertEqual(websocket.receive_json()['alert_type'], 'CAMERA_RECOVERED')
            self.client.post('/api/cameras/1/health-check', headers=self.headers['owner'])
            bulk = self.client.post('/api/cameras/health-check-all', headers=self.headers['owner'])
            self.assertEqual(bulk.status_code, 200, bulk.text)
            self.assertEqual(bulk.json()['total'], 2)
            self.assertEqual(bulk.json()['checked'], 2)
            summary = self.client.get('/api/cameras/health-summary', headers=self.headers['owner'])
            self.assertEqual(summary.json()['total'], 2)
            self.assertEqual(sum(summary.json()[key] for key in ['online', 'degraded', 'offline', 'unknown']), 2)
        with SessionLocal() as db:
            self.assertEqual(db.query(Alert).filter_by(camera_id=1, alert_type='CAMERA_RECOVERED').count(), 1)

        slow = ProbeResult(True, 2000, 'SIMULATION: slow valid frame')
        with patch('app.services.camera_health.probe_stream', return_value=slow):
            self.assertEqual(self.client.post('/api/cameras/1/health-check', headers=self.headers['owner']).json()['health_status'], 'DEGRADED')

        self.assertEqual(self.client.post('/api/cameras/1/health-check').status_code, 401)
        self.assertEqual(self.client.post('/api/cameras/999999/health-check', headers=self.headers['owner']).status_code, 404)
        with SessionLocal() as db:
            other = db.query(User).filter_by(email='other@example.com').one(); other.role = 'VIEWER'; db.commit()
        self.assertEqual(self.client.post('/api/cameras/1/health-check', headers=self.headers['other']).status_code, 403)
        with SessionLocal() as db:
            other = db.query(User).filter_by(email='other@example.com').one(); other.role = 'OPERATOR'; db.commit()
        unsupported = self.client.post('/api/cameras/', headers=self.headers['admin'], json={
            'camera_name': 'Unsafe', 'camera_code': 'UNSAFE', 'location': 'Test', 'stream_url': 'file:///etc/passwd', 'status': 'ONLINE'})
        self.assertEqual(unsupported.status_code, 400)
        for unsafe_url in ['http://localhost:8000/private', 'http://169.254.169.254/latest/meta-data']:
            rejected = self.client.post('/api/cameras/', headers=self.headers['admin'], json={
                'camera_name': 'Unsafe', 'camera_code': 'UNSAFE', 'location': 'Test', 'stream_url': unsafe_url, 'status': 'ONLINE'})
            self.assertEqual(rejected.status_code, 400, unsafe_url)

        class FakeCapture:
            released = False
            def open(self, *_args): return True
            def isOpened(self): return True
            def read(self): return False, None
            def release(self): self.released = True
        fake = FakeCapture()
        with patch('app.services.camera_health.cv2.VideoCapture', return_value=fake):
            self.assertFalse(probe_stream('http://example.com/feed', 300).success)
        self.assertTrue(fake.released)

        frame = Image.new('RGB', (320, 180), '#31517a')
        buffer = BytesIO(); frame.save(buffer, format='JPEG'); jpeg = buffer.getvalue()
        class MjpegHandler(BaseHTTPRequestHandler):
            def do_GET(self):
                self.send_response(200); self.send_header('Content-Type', 'multipart/x-mixed-replace; boundary=frame'); self.end_headers()
                try:
                    for _ in range(10):
                        self.wfile.write(b'--frame\r\nContent-Type: image/jpeg\r\nContent-Length: ' + str(len(jpeg)).encode() + b'\r\n\r\n' + jpeg + b'\r\n')
                        self.wfile.flush(); time.sleep(.02)
                except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
                    pass
            def log_message(self, *_args): pass
        server = ThreadingHTTPServer(('127.0.0.1', 0), MjpegHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
        previous_loopback = os.environ.get('CAMERA_HEALTH_ALLOW_LOOPBACK')
        os.environ['CAMERA_HEALTH_ALLOW_LOOPBACK'] = 'true'
        try:
            local_stream = f'http://127.0.0.1:{server.server_port}/video'
            reachable = probe_stream(local_stream, 1000)
            self.assertTrue(reachable.success, reachable)
            with SessionLocal() as db:
                camera = db.query(Camera).filter(Camera.id == 1).one(); camera.stream_url = local_stream; db.commit()
            streamed = self.client.get('/api/video/1/stream')
            self.assertEqual(streamed.status_code, 200)
            self.assertIn(b'Content-Type: image/jpeg', streamed.content)
        finally:
            with SessionLocal() as db:
                camera = db.query(Camera).filter(Camera.id == 1).one(); camera.stream_url = None; db.commit()
            server.shutdown(); server.server_close(); thread.join(timeout=2)
            if previous_loopback is None: os.environ.pop('CAMERA_HEALTH_ALLOW_LOOPBACK', None)
            else: os.environ['CAMERA_HEALTH_ALLOW_LOOPBACK'] = previous_loopback

        started = time.perf_counter()
        timed = probe_stream('rtsp://192.0.2.1:8554/missing', 300)
        self.assertFalse(timed.success)
        self.assertLess(time.perf_counter() - started, 2.0)

    def test_failure_cases_and_access(self):
        e=self.add(evidence_type='PLATE_DETECTION',vehicle_id=1)
        payload={'investigation_id':self.reference,'evidence_ids':[e['id']]}
        self.assertEqual(self.request('POST','/export',json={**payload,'evidence_ids':[]}).status_code,422)
        self.assertEqual(self.request('POST','/export',json={**payload,'evidence_ids':[999999]}).status_code,404)
        self.assertEqual(self.request('POST','/export',json={**payload,'investigation_id':'invalid'}).status_code,404)
        self.assertEqual(self.request('POST','',json={'investigation_id':self.reference,'evidence_type':'SNAPSHOT','vehicle_id':1,'file_path':'../../secret'}).status_code,422)
        self.assertEqual(self.request('POST','',json={'investigation_id':self.reference,'evidence_type':'ALERT','alert_id':2}).status_code,404)
        for method,url,body in [('GET','',None),('GET',f'/{e["id"]}',None),('GET',f'/{e["id"]}/file',None),('GET',f'/investigations/{self.reference}',None),('POST','/export',payload),('POST','',{}),('DELETE',f'/{e["id"]}',None),('POST','/investigations',{'vehicle_plate':'GJ01AB1234'})]:
            self.assertEqual(self.client.request(method,'/api/evidence'+url,json=body).status_code,401)
        for method,url in [('GET',f'/{e["id"]}'),('GET',f'/{e["id"]}/file'),('DELETE',f'/{e["id"]}'),('GET',f'/investigations/{self.reference}')]:
            self.assertEqual(self.client.request(method,'/api/evidence'+url,headers=self.headers['other']).status_code,404)
        self.assertEqual(self.client.post('/api/evidence/export',json=payload,headers=self.headers['other']).status_code,404)
        self.assertEqual(self.client.get('/api/evidence',headers=self.headers['other']).json(),[])
        self.assertEqual(self.client.get(f'/api/evidence/{e["id"]}',headers=self.headers['admin']).status_code,200)
        with SessionLocal() as db:
            other=db.query(User).filter_by(email='other@example.com').one(); other.role='VIEWER'; db.commit()
        self.assertEqual(self.client.get('/api/evidence',headers=self.headers['other']).status_code,403)
        try:
            self.path.unlink()
            self.assertEqual(self.request('GET',f'/{e["id"]}/file').status_code,409)
            self.assertIn('missing',self.request('GET',f'/{e["id"]}').json()['file_status'])
            self.assertEqual(self.request('POST','/export',json=payload).status_code,409)
            self.assertEqual(self.request('POST','',json={'investigation_id':self.reference,'evidence_type':'PLATE_DETECTION','vehicle_id':2}).status_code,409)
            self.path.write_bytes(b'changed')
            self.assertEqual(self.request('POST','/export',json=payload).status_code,409)
        finally:
            self.path.write_bytes(self.original)
        for bad in ['../secret.jpg',str(self.path.parent/'..'/'secret.jpg'),str(self.path.parent.parent/'snapshots-other'/'secret.jpg')]:
            with self.assertRaises(HTTPException): snapshot_bytes(bad)
        with patch('app.services.investigation_report.generate_pdf',side_effect=RuntimeError('test renderer failure')):
            for fmt in ['pdf','zip']:
                self.assertEqual(self.request('POST','/export',json={**payload,'format':fmt}).status_code,500)
        route=self.add(evidence_type='ROUTE_TRACE')
        self.assertEqual(self.request('GET',f'/{route["id"]}/file').status_code,404)
        self.assertEqual(self.request('DELETE',f'/{route["id"]}').status_code,200)
        self.assertEqual(self.request('GET',f'/{route["id"]}').status_code,404)

    def test_existing_endpoints(self):
        for path in ['/api/analytics/summary','/api/cameras/','/api/search/vehicles?query_str=GJ01AB1234','/api/search/detections','/api/search/trace/GJ01AB1234','/api/alerts/']:
            response=self.client.get(path,headers=self.headers['owner'])
            self.assertEqual(response.status_code,200,(path,response.text))
        camera={'camera_name':'CRUD test','camera_code':'CRUD','latitude':23.0,'longitude':72.0,'location':'Test','stream_url':''}
        self.assertEqual(self.client.post('/api/cameras/',headers=self.headers['owner'],json=camera).status_code,403)
        created=self.client.post('/api/cameras/',headers=self.headers['admin'],json=camera)
        self.assertEqual(created.status_code,200,created.text)
        ident=created.json()['id']
        self.assertEqual(self.client.put(f'/api/cameras/{ident}',headers=self.headers['admin'],json={'camera_name':'Updated'}).status_code,200)
        self.assertEqual(self.client.delete(f'/api/cameras/{ident}',headers=self.headers['admin']).status_code,200)
        with self.client.websocket_connect('/ws/alerts') as ws:
            ws.send_text('validation heartbeat')
            from app.websocket.manager import manager
            manager.broadcast_alert_sync({'alert_id': 1, 'message': 'WebSocket validation'})
            self.assertEqual(ws.receive_json()['alert_id'], 1)

    def test_plate_normalization_and_structured_timeline(self):
        for value in ['GJ 01 AB 1234', 'GJ-01-AB-1234', 'gj01ab1234']:
            self.assertEqual(normalize_plate(value), 'GJ01AB1234')
            self.assertTrue(is_valid_indian_plate(value))
            self.assertTrue(plates_match(value, 'GJ01AB1234'))
        self.assertFalse(is_valid_indian_plate('FL21E50'))
        self.assertEqual(normalize_ocr_plate('GJO1AB1234', .99), 'GJ01AB1234')
        self.assertEqual(normalize_ocr_plate('GJO1AB1234', .60), 'GJO1AB1234')
        params = {'registration_number': 'GJ-01-AB-1234', 'vehicle_type': 'car',
                  'camera_id': 1, 'location': 'Ahmedabad',
                  'start_time': '2026-09-04T10:00:00', 'end_time': '2026-09-04T10:40:00'}
        response = self.client.get('/api/search/investigations', headers=self.headers['owner'], params=params)
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(len(response.json()), 1)
        self.assertEqual(response.json()[0]['registration_number'], 'GJ01AB1234')
        timeline = self.client.get('/api/search/trace/GJ%2001%20AB%201234', headers=self.headers['owner'])
        self.assertEqual(timeline.status_code, 200, timeline.text)
        self.assertEqual([row['camera_name'] for row in timeline.json()], ['Test Camera 1', 'Test Camera 2'])
        self.assertGreater(timeline.json()[1]['distance_km'], 0)
        self.assertIsNotNone(timeline.json()[1]['calculated_speed_kmh'])
        self.assertEqual(len(timeline.json()[0]['alerts']), 1)
        self.assertEqual(self.client.get('/api/search/trace/GJ01AB1234').status_code, 401)
        invalid = self.client.get('/api/search/investigations', headers=self.headers['owner'], params={'start_time': '2026-09-05T00:00:00', 'end_time': '2026-09-04T00:00:00'})
        self.assertEqual(invalid.status_code, 400)

    def test_natural_language_investigation_search(self):
        natural = lambda query: self.client.post('/api/search/natural', headers=self.headers['owner'], json={'query': query})

        plate = natural('Find GJ01AB1234')
        self.assertEqual(plate.status_code, 200, plate.text)
        self.assertEqual(plate.json()['parsed_filters']['registration_number'], 'GJ01AB1234')
        self.assertEqual(plate.json()['result_count'], 2)
        structured = self.client.get('/api/search/investigations', headers=self.headers['owner'], params={'registration_number': 'GJ01AB1234'}).json()
        self.assertEqual([row['id'] for row in plate.json()['results']], [row['id'] for row in structured])

        camera = natural('Find GJ01AB1234 on Camera 2')
        self.assertEqual(camera.json()['parsed_filters']['camera_id'], 2)
        self.assertEqual(camera.json()['result_count'], 1)

        location_time = natural('Show vehicles at Ahmedabad checkpoint 1 in the last hour')
        self.assertEqual(location_time.json()['parsed_filters']['location'], 'Ahmedabad checkpoint 1')
        self.assertIsNotNone(location_time.json()['parsed_filters']['start_time'])
        self.assertEqual(location_time.json()['timezone']['input'], 'Asia/Kolkata')

        vehicle_type = natural('Show cars detected September 4 2026')
        self.assertEqual(vehicle_type.json()['parsed_filters']['vehicle_type'], 'car')
        self.assertEqual(vehicle_type.json()['result_count'], 2)

        explicit_range = natural('Find vehicles between 8 PM and 10 PM September 4 2026')
        self.assertEqual(explicit_range.status_code, 200, explicit_range.text)
        self.assertIn('14:30', explicit_range.json()['parsed_filters']['start_time'])

        combined = natural('Find GJ01AB1234 at Ahmedabad checkpoint 2 between 8 PM and 10 PM September 4 2026')
        self.assertEqual(combined.json()['parsed_filters']['camera_id'], 2)
        self.assertEqual(combined.json()['parsed_filters']['registration_number'], 'GJ01AB1234')
        self.assertEqual(combined.json()['result_count'], 0)

        unsupported = natural('Find the suspicious white BMW driven by John')
        self.assertEqual(unsupported.json()['status'], 'UNSUPPORTED')
        self.assertTrue({'suspicious', 'white', 'BMW', 'driven', 'John'} <= set(unsupported.json()['unparsed_terms']))
        self.assertEqual(natural('asdfghjkl').json()['status'], 'UNSUPPORTED')

        injection = natural("Find vehicles'; DROP TABLE vehicles; --")
        self.assertEqual(injection.status_code, 200, injection.text)
        with SessionLocal() as db:
            self.assertEqual(db.query(Vehicle).count(), 2)

        self.assertEqual(self.client.post('/api/search/natural', json={'query': 'Find GJ01AB1234'}).status_code, 401)
        self.assertEqual(natural('x' * 501).status_code, 422)
        self.assertEqual(natural('Find vehicles between 25 PM and 10 PM').status_code, 400)
        self.assertEqual(natural('Find vehicles September 31 2026').status_code, 400)
        contradiction = natural('Find vehicles from 2026-09-04T22:00 to 2026-09-04T20:00')
        self.assertEqual(contradiction.status_code, 400)

        with SessionLocal() as db:
            one = db.query(Camera).filter(Camera.id == 1).one()
            two = db.query(Camera).filter(Camera.id == 2).one()
            old_one, old_two = one.location, two.location
            one.location = two.location = 'Shared Gate'
            db.commit()
        try:
            ambiguous = natural('Show vehicles at Shared Gate')
            self.assertEqual(ambiguous.json()['status'], 'AMBIGUOUS')
            self.assertEqual(len(ambiguous.json()['matches']), 2)
            self.assertEqual(ambiguous.json()['results'], [])
        finally:
            with SessionLocal() as db:
                db.query(Camera).filter(Camera.id == 1).update({'location': old_one})
                db.query(Camera).filter(Camera.id == 2).update({'location': old_two})
                db.commit()

    def test_natural_time_parser_deterministically(self):
        fixed = datetime(2026, 9, 6, 21, 30, tzinfo=INDIA_TZ)
        with SessionLocal() as db:
            cameras = db.query(Camera).all()
        cases = {
            'today': ('2026-09-05T18:30:00', '2026-09-06T16:00:00'),
            'yesterday': ('2026-09-04T18:30:00', '2026-09-05T18:29:59.999999'),
            'last 30 minutes': ('2026-09-06T15:30:00', '2026-09-06T16:00:00'),
            'this morning': ('2026-09-06T00:30:00', '2026-09-06T06:30:00'),
            'this afternoon': ('2026-09-06T06:30:00', '2026-09-06T11:30:00'),
            'this evening': ('2026-09-06T11:30:00', '2026-09-06T18:29:59'),
            'between 8 PM and 10 PM': ('2026-09-06T14:30:00', '2026-09-06T16:30:00'),
            'after 9 PM': ('2026-09-06T15:30:00', '2026-09-06T16:00:00'),
            'before 11 PM': ('2026-09-05T18:30:00', '2026-09-06T17:30:00'),
            'September 6': ('2026-09-05T18:30:00', '2026-09-06T16:00:00'),
            '6 September': ('2026-09-05T18:30:00', '2026-09-06T16:00:00'),
        }
        for phrase, expected in cases.items():
            parsed = parse_natural_query(f'Show cars {phrase}', cameras, fixed)
            self.assertEqual(parsed.filters['start_time'].isoformat(), expected[0], phrase)
            self.assertEqual(parsed.filters['end_time'].isoformat(), expected[1], phrase)


if __name__=='__main__':
    unittest.main(verbosity=2)
