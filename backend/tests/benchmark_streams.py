"""Short loopback HTTP MJPEG ingestion and CPU YOLO component benchmark.
Run from backend: venv/Scripts/python.exe tests/benchmark_streams.py [--ai]
No OCR, DB, browser or WAN workload is included. Stop on resource thresholds.
"""
import argparse
import concurrent.futures
import json
import os
from pathlib import Path
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import cv2
import numpy as np
import psutil
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.services import stream_runtime as rt

parser=argparse.ArgumentParser(); parser.add_argument('--ai',action='store_true'); args=parser.parse_args()
os.environ['CAMERA_HEALTH_ALLOW_LOOPBACK']='true'
os.environ['YOLO_DEVICE']='cpu'
frame=np.zeros((360,640,3),np.uint8)
cv2.putText(frame,'Synthetic ingestion benchmark',(25,180),0,1,(255,255,255),2)
if args.ai:
    from app.ai.detector import VideoAnalyzer
    import torch
    torch.set_num_threads(2)
    source=next(Path('uploads').glob('*.mp4'))
    cap=cv2.VideoCapture(str(source)); ok,actual=cap.read(); cap.release()
    if ok: frame=cv2.resize(actual,(640,360))
_,jpeg=cv2.imencode('.jpg',frame); jpeg=jpeg.tobytes()
class Handler(BaseHTTPRequestHandler):
    def log_message(self,*args): pass
    def do_GET(self):
        self.send_response(200); self.send_header('Content-Type','multipart/x-mixed-replace; boundary=frame'); self.end_headers()
        try:
            for _ in range(600):
                self.wfile.write(b'--frame\r\nContent-Type: image/jpeg\r\nContent-Length: '+str(len(jpeg)).encode()+b'\r\n\r\n'+jpeg+b'\r\n'); self.wfile.flush(); time.sleep(1/15)
        except (BrokenPipeError,ConnectionResetError,ConnectionAbortedError): pass
server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
threading.Thread(target=server.serve_forever,daemon=True).start()
process=psutil.Process(); results=[]
try:
    for count in [1,2,4,8]:
        if psutil.virtual_memory().percent > 85:
            results.append({'cameras':count,'stopped':'system RAM >85%'}); break
        models=[]
        for _ in range(count):
            if args.ai and psutil.virtual_memory().percent > 85: break
            models.append(VideoAnalyzer() if args.ai else None)
        if len(models) != count:
            results.append({'cameras':count,'stopped':'system RAM >85% during model loading'}); break
        barrier=threading.Barrier(count)
        samples=[]; done=threading.Event(); resource_stop=threading.Event()
        def monitor():
            while not done.wait(.1): samples.append((process.memory_info().rss,psutil.virtual_memory().percent))
        sampler=threading.Thread(target=monitor); sampler.start()
        cpu0=process.cpu_times(); started=time.perf_counter()
        def worker(i):
            camera=100+i; rt.reserve(camera); cap=rt.ResilientCapture(camera,f'http://127.0.0.1:{server.server_port}/video')
            latencies=[]; inference_seconds=0; barrier.wait(); begin=time.perf_counter()
            try:
                for _ in range(45 if not args.ai else 15):
                    if psutil.virtual_memory().percent>85:
                        resource_stop.set(); break
                    tick=time.perf_counter(); ok,image=cap.read()
                    if not ok: break
                    t=time.perf_counter()
                    if models[i]: models[i].process_frame(image)
                    duration=time.perf_counter()-t; inference_seconds+=duration
                    rt.processed(camera,duration); latencies.append(time.perf_counter()-tick)
                row=rt.snapshot(camera); elapsed=time.perf_counter()-begin
                row.update(elapsed_seconds=elapsed,processing_fps=len(latencies)/elapsed,
                    inference_fps=len(latencies)/inference_seconds if args.ai else None,
                    average_read_process_latency_ms=1000*sum(latencies)/max(1,len(latencies)))
                return row
            finally: cap.release(); rt.finish(camera)
        with concurrent.futures.ThreadPoolExecutor(max_workers=count) as pool:
            rows=list(pool.map(worker,range(count)))
        elapsed=time.perf_counter()-started; done.set(); sampler.join(); cpu1=process.cpu_times()
        result={'cameras':count,'mode':'CPU YOLO (no OCR/DB)' if args.ai else 'ingestion only',
            'resource_stop':resource_stop.is_set(),'elapsed_seconds':elapsed,'cpu_percent_one_core':100*((cpu1.user+cpu1.system)-(cpu0.user+cpu0.system))/elapsed,
            'peak_rss_mb':max([x[0] for x in samples]+[process.memory_info().rss])/1048576,
            'aggregate_processing_fps':sum(r['processing_fps'] for r in rows),'streams':rows}
        results.append(result); print(json.dumps(result),flush=True)
        del models
        if resource_stop.is_set() or (samples and max(x[1] for x in samples)>85): break
finally: server.shutdown(); server.server_close()
output=Path('output/challenge-audit'); output.mkdir(parents=True,exist_ok=True)
(output/('cpu-yolo.json' if args.ai else 'ingestion.json')).write_text(json.dumps({'opencv':cv2.__version__,'logical_cpus':psutil.cpu_count(),'results':results},indent=2))
