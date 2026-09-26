"""Deterministic failure/recovery tests; fake capture is not a WAN certification."""
import sys
import time
import unittest
from pathlib import Path
from unittest.mock import patch
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.services import stream_runtime as rt

class Capture:
    def __init__(self, opened=True, frames=None):
        self.opened = opened
        self.frames = iter(frames or [])
        self.released = False
    def open(self, *args): return self.opened
    def read(self): return next(self.frames, (False, None))
    def get(self, prop): return 30.0
    def release(self): self.released = True

class RuntimeTests(unittest.TestCase):
    def setUp(self):
        for camera in range(1, 4):
            rt.finish(camera)
            rt.reserve(camera)
    def tearDown(self):
        for camera in range(1, 4): rt.finish(camera)
    def test_startup_failure_recovery_and_cleanup(self):
        bad = Capture(False)
        good = Capture(frames=[(True, np.zeros((4,4,3),dtype=np.uint8))])
        captures = iter([bad, good]); waits=[]
        cap=rt.ResilientCapture(1,'rtsp://192.0.2.2/live',lambda:next(captures),waits.append)
        self.assertTrue(cap.read()[0]); cap.release()
        row=rt.snapshot(1)
        self.assertEqual(row['failed_reads'],1)
        self.assertEqual(row['frames_received'],1)
        self.assertEqual(row['consecutive_failures'],0)
        self.assertEqual(row['status'],'ONLINE')
        self.assertEqual(waits,[1]); self.assertTrue(bad.released and good.released)
    def test_exhaustion_isolated_from_other_camera(self):
        waits=[]; captures=[]
        def factory():
            cap=Capture(False); captures.append(cap); return cap
        bad=rt.ResilientCapture(1,'rtsp://192.0.2.2/live',factory,waits.append)
        good=rt.ResilientCapture(2,'test.avi',lambda:Capture(frames=[(True,np.ones((4,4,3)))]))
        self.assertFalse(bad.read()[0]); self.assertTrue(good.read()[0]); good.release()
        self.assertEqual(rt.snapshot(1)['status'],'OFFLINE')
        self.assertEqual(rt.snapshot(2)['status'],'ONLINE')
        self.assertEqual(rt.snapshot(1)['failed_reads'],6)
        self.assertEqual(waits,[1,2,4,8,8]); self.assertTrue(all(c.released for c in captures))
    def test_drop_then_reconnect(self):
        frame=np.ones((4,4,3))
        captures=iter([Capture(frames=[(True,frame)]),Capture(frames=[(True,frame)])])
        cap=rt.ResilientCapture(1,'https://example.com/video',lambda:next(captures),lambda _:None)
        self.assertTrue(cap.read()[0]); self.assertTrue(cap.read()[0]); cap.release()
        self.assertEqual(rt.snapshot(1)['frames_received'],2)
        self.assertEqual(rt.snapshot(1)['failed_reads'],1)
    def test_eof_not_failed_read(self):
        cap=rt.ResilientCapture(1,'file.avi',lambda:Capture())
        self.assertFalse(cap.read()[0]); self.assertEqual(rt.snapshot(1)['failed_reads'],0)
    def test_stale_frames_and_metrics(self):
        rt.update(1,last_tick=time.monotonic()-6,status='ONLINE')
        self.assertEqual(rt.snapshot(1)['status'],'DEGRADED')
        rt.update(1,last_tick=time.monotonic()-16)
        self.assertEqual(rt.snapshot(1)['status'],'OFFLINE')
        rt.processed(1,.1); rt.skipped(1)
        self.assertEqual(rt.snapshot(1)['frames_processed'],1)
        self.assertEqual(rt.snapshot(1)['skipped_frames'],1)
        self.assertAlmostEqual(rt.snapshot(1)['average_processing_latency_ms'],100)
    def test_duplicate_reservation(self):
        self.assertFalse(rt.reserve(1)); rt.finish(1); self.assertTrue(rt.reserve(1))
    def test_capture_exception_is_contained(self):
        with patch.object(Capture,'open',side_effect=RuntimeError('secret URL')):
            cap=rt.ResilientCapture(1,'rtsp://192.0.2.2/live',Capture,lambda _:None)
            self.assertFalse(cap.read()[0])
        self.assertNotIn('secret',rt.snapshot(1)['last_error'])

if __name__ == '__main__': unittest.main()
