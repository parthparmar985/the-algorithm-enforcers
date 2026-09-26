"""Process-local processing ownership and measured capture health (not a broker)."""
import math
import threading
import time
from datetime import datetime, timezone

import cv2

from .camera_url import normalized_capture_url, validate_stream_url

_guard = threading.RLock()
_active = set()
_metrics = {}


def reserve(camera_id):
    with _guard:
        if camera_id in _active:
            return False
        _active.add(camera_id)
        _metrics[camera_id] = dict(camera_id=camera_id, status="OFFLINE", active=True,
            processing_fps=0.0, source_fps=None, last_frame_at=None,
            frames_received=0, frames_processed=0, failed_reads=0, skipped_frames=0,
            consecutive_failures=0, last_error=None, queue_depth=0,
            average_processing_latency_ms=0.0, started=time.monotonic(), last_tick=None,
            processing_seconds=0.0)
        return True


def update(camera_id, **values):
    with _guard:
        if camera_id in _metrics:
            _metrics[camera_id].update(values)


def finish(camera_id):
    with _guard:
        _active.discard(camera_id)
        update(camera_id, active=False, status="OFFLINE")


def snapshot(camera_id):
    with _guard:
        row = dict(_metrics.get(camera_id, {}))
    if not row:
        return None
    tick = row.pop("last_tick")
    row.pop("started")
    row.pop("processing_seconds")
    # A blocked read/inference cannot leave the API claiming ONLINE indefinitely.
    age = time.monotonic() - tick if tick is not None else None
    if row["active"] and age is not None:
        if age > 15:
            row["status"] = "OFFLINE"
        elif age > 5:
            row["status"] = "DEGRADED"
    return row


def processed(camera_id, seconds):
    with _guard:
        row = _metrics[camera_id]
        row["frames_processed"] += 1
        row["processing_seconds"] += seconds
        elapsed = max(time.monotonic() - row["started"], .001)
        row["processing_fps"] = row["frames_processed"] / elapsed
        row["average_processing_latency_ms"] = 1000 * row["processing_seconds"] / row["frames_processed"]


def skipped(camera_id):
    with _guard:
        _metrics[camera_id]["skipped_frames"] += 1


class ResilientCapture:
    """Finite files; network streams retry with capped exponential backoff.

    FFmpeg timeout support depends on the installed OpenCV backend. Never fall
    back to an unbounded network open. No application frame queue is retained.
    """
    def __init__(self, camera_id, source, factory=None, sleep=time.sleep):
        self.camera_id = camera_id
        self.source = source
        self.network = source.lower().startswith(("rtsp://", "http://", "https://"))
        if self.network:
            self.source = normalized_capture_url(validate_stream_url(source))
        self.factory = factory or cv2.VideoCapture
        self.sleep = sleep
        self.cap = None
        self.closed = False

    def isOpened(self):
        return not self.closed

    def _open(self):
        self.cap = self.factory()
        if self.network:
            opened = self.cap.open(self.source, cv2.CAP_FFMPEG,
                [cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, 3000, cv2.CAP_PROP_READ_TIMEOUT_MSEC, 3000])
        else:
            opened = self.cap.open(self.source)
        if not opened:
            return False
        fps = self.cap.get(cv2.CAP_PROP_FPS)
        update(self.camera_id, source_fps=fps if math.isfinite(fps) and fps > 0 else None)
        return True

    def get(self, prop):
        return self.cap.get(prop) if self.cap is not None else 0

    def read(self):
        for attempt in range(6):
            if self.closed:
                return False, None
            started = time.monotonic()
            opened = False
            try:
                opened = self.cap is not None or self._open()
                ok, frame = self.cap.read() if opened else (False, None)
                if ok and frame is not None and frame.size:
                    with _guard:
                        row = _metrics[self.camera_id]
                        tick = time.monotonic()
                        gap = tick - row["last_tick"] if row["last_tick"] else tick - started
                        row.update(status="DEGRADED" if gap > 1.5 else "ONLINE",
                            last_tick=tick, last_frame_at=datetime.now(timezone.utc).isoformat(),
                            frames_received=row["frames_received"] + 1,
                            consecutive_failures=0, last_error=None)
                    return True, frame
                error = "No valid frame received"
            except Exception as exc:
                error = "Capture failed: " + type(exc).__name__
            if not self.network and self.cap is not None and opened:
                self.release()  # EOF is not a failed network read.
                return False, None
            with _guard:
                row = _metrics[self.camera_id]
                row.update(failed_reads=row["failed_reads"] + 1,
                    consecutive_failures=row["consecutive_failures"] + 1,
                    status="OFFLINE", last_error=error)
            if self.cap is not None:
                self.cap.release()
                self.cap = None
            if not self.network or attempt == 5:
                self.release()
                return False, None
            self.sleep(min(2 ** attempt, 8))
        return False, None

    def release(self):
        self.closed = True
        if self.cap is not None:
            self.cap.release()
            self.cap = None
