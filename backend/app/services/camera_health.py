import asyncio
import logging
import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import cv2
from sqlalchemy.orm import Session

from ..database.database import SessionLocal
from ..models.alert import Alert
from ..models.camera import Camera
from ..websocket.manager import manager
from .camera_url import normalized_capture_url, validate_stream_url


UNKNOWN = "UNKNOWN"
ONLINE = "ONLINE"
DEGRADED = "DEGRADED"
OFFLINE = "OFFLINE"
HEALTH_STATES = {UNKNOWN, ONLINE, DEGRADED, OFFLINE}

_locks_guard = threading.Lock()
_camera_locks: dict[int, threading.Lock] = {}
_bulk_lock = threading.Lock()


class HealthCheckInProgress(RuntimeError):
    pass


@dataclass(frozen=True)
class ProbeResult:
    success: bool
    latency_ms: int | None
    message: str
    connected: bool = False


def utc_now():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _setting(name: str, default: int, minimum: int, maximum: int) -> int:
    try:
        return max(minimum, min(maximum, int(os.getenv(name, str(default)))))
    except ValueError:
        return default


def camera_lock(camera_id: int):
    with _locks_guard:
        return _camera_locks.setdefault(camera_id, threading.Lock())


def probe_stream(stream_url: str | None, timeout_ms: int | None = None) -> ProbeResult:
    try:
        stream_url = validate_stream_url(stream_url)
    except ValueError as exc:
        return ProbeResult(False, None, str(exc))
    if not stream_url:
        return ProbeResult(False, None, "No stream URL configured")

    timeout_ms = timeout_ms or _setting("CAMERA_HEALTH_TIMEOUT_MS", 3000, 250, 10000)
    capture = cv2.VideoCapture()
    started = time.perf_counter()
    try:
        parameters = []
        if hasattr(cv2, "CAP_PROP_OPEN_TIMEOUT_MSEC"):
            parameters += [cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, timeout_ms]
        if hasattr(cv2, "CAP_PROP_READ_TIMEOUT_MSEC"):
            parameters += [cv2.CAP_PROP_READ_TIMEOUT_MSEC, timeout_ms]
        try:
            opened = capture.open(normalized_capture_url(stream_url), cv2.CAP_FFMPEG, parameters)
        except (TypeError, cv2.error):
            return ProbeResult(False, None, "OpenCV stream timeout controls are unavailable")
        if not opened or not capture.isOpened():
            return ProbeResult(False, round((time.perf_counter() - started) * 1000), "Stream connection failed")
        received, frame = capture.read()
        latency = round((time.perf_counter() - started) * 1000)
        if not received or frame is None or getattr(frame, "size", 0) == 0:
            return ProbeResult(False, latency, "Connected but no valid frame was received", connected=True)
        return ProbeResult(True, latency, "Stream reachable and a valid frame was received", connected=True)
    except Exception as exc:
        return ProbeResult(False, round((time.perf_counter() - started) * 1000), f"Stream probe failed: {type(exc).__name__}")
    finally:
        capture.release()


def _alert_message(camera: Camera, alert_type: str, reason: str) -> str:
    last = camera.last_frame_at.isoformat() if camera.last_frame_at else "never"
    action = "offline" if alert_type == "CAMERA_OFFLINE" else "recovered"
    return (f"Camera {camera.camera_code} ({camera.camera_name}) at {camera.location or 'unknown location'} "
            f"is {action}. {reason}. Last successful frame: {last}")[:500]


def apply_probe_result(db: Session, camera: Camera, result: ProbeResult, checked_at: datetime | None = None):
    checked_at = checked_at or utc_now()
    previous = camera.health_status if camera.health_status in HEALTH_STATES else UNKNOWN
    camera.last_health_check = checked_at
    camera.latency_ms = result.latency_ms
    offline_threshold = _setting("CAMERA_HEALTH_OFFLINE_FAILURES", 2, 2, 10)
    degraded_latency = _setting("CAMERA_HEALTH_DEGRADED_LATENCY_MS", 1500, 100, 10000)

    if result.success:
        camera.consecutive_failures = 0
        camera.stream_available = True
        camera.last_online_at = checked_at
        camera.last_frame_at = checked_at
        camera.health_status = DEGRADED if result.latency_ms is not None and result.latency_ms >= degraded_latency else ONLINE
        camera.health_message = (f"High frame latency: {result.latency_ms} ms" if camera.health_status == DEGRADED else result.message)
    else:
        if result.connected:
            camera.last_online_at = checked_at
        camera.consecutive_failures = (camera.consecutive_failures or 0) + 1
        camera.stream_available = False
        camera.health_status = OFFLINE if camera.consecutive_failures >= offline_threshold else DEGRADED
        camera.health_message = result.message[:500]

    alert_type = None
    if camera.health_status == OFFLINE and previous != OFFLINE:
        alert_type = "CAMERA_OFFLINE"
    elif previous == OFFLINE and result.success:
        alert_type = "CAMERA_RECOVERED"

    alert = None
    if alert_type:
        message = _alert_message(camera, alert_type, camera.health_message or result.message)
        alert = Alert(camera_id=camera.id, alert_type=alert_type,
                      severity="HIGH" if alert_type == "CAMERA_OFFLINE" else "LOW",
                      message=message, timestamp=checked_at, status="NEW")
        db.add(alert)
    db.commit()
    db.refresh(camera)
    if alert:
        db.refresh(alert)
        manager.broadcast_alert_sync({
            "type": "ALERT", "alert_id": alert.id, "alert_type": alert.alert_type,
            "camera_id": camera.id, "camera_code": camera.camera_code,
            "camera_name": camera.camera_name, "location": camera.location,
            "severity": alert.severity, "message": alert.message,
            "timestamp": alert.timestamp.isoformat(), "health_status": camera.health_status,
        })
    return camera


def health_payload(camera: Camera):
    return {
        "camera_id": camera.id, "camera_code": camera.camera_code, "camera_name": camera.camera_name,
        "location": camera.location, "health_status": camera.health_status,
        "last_health_check": camera.last_health_check, "last_online_at": camera.last_online_at,
        "last_frame_at": camera.last_frame_at, "latency_ms": camera.latency_ms,
        "consecutive_failures": camera.consecutive_failures, "stream_available": camera.stream_available,
        "message": camera.health_message,
    }


def check_camera(camera_id: int, probe=None):
    probe = probe or probe_stream
    with camera_lock(camera_id):
        db = SessionLocal()
        try:
            camera = db.query(Camera).filter(Camera.id == camera_id).first()
            if not camera:
                return {"camera_id": camera_id, "error": "Camera not found"}
            result = probe(camera.stream_url)
            camera = apply_probe_result(db, camera, result)
            return health_payload(camera)
        finally:
            db.close()


def check_all_cameras(force: bool = True):
    if not _bulk_lock.acquire(blocking=False):
        raise HealthCheckInProgress("A bulk camera health check is already running")
    try:
        db = SessionLocal()
        try:
            now = utc_now()
            offline_retry = _setting("CAMERA_HEALTH_OFFLINE_RETRY_SECONDS", 180, 30, 3600)
            ids = [camera.id for camera in db.query(Camera).all()
                   if force or camera.health_status != OFFLINE or not camera.last_health_check
                   or camera.last_health_check <= now - timedelta(seconds=offline_retry)]
            total = db.query(Camera).count()
        finally:
            db.close()
        workers = _setting("CAMERA_HEALTH_CONCURRENCY", 4, 1, 8)
        checked = []
        with ThreadPoolExecutor(max_workers=workers, thread_name_prefix="camera-health") as executor:
            futures = {executor.submit(check_camera, camera_id): camera_id for camera_id in ids}
            for future in as_completed(futures):
                try:
                    checked.append(future.result())
                except Exception as exc:
                    checked.append({"camera_id": futures[future], "error": f"Health check failed: {type(exc).__name__}"})
        db = SessionLocal()
        try:
            counts = {state: db.query(Camera).filter(Camera.health_status == state).count() for state in HEALTH_STATES}
        finally:
            db.close()
        return {"total": total, "checked": len(checked), "online": counts[ONLINE],
                "degraded": counts[DEGRADED], "offline": counts[OFFLINE],
                "unknown": counts[UNKNOWN], "results": checked}
    finally:
        _bulk_lock.release()


async def monitor_loop(stop_event: asyncio.Event):
    interval = _setting("CAMERA_HEALTH_INTERVAL_SECONDS", 60, 30, 3600)
    while not stop_event.is_set():
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=interval)
        except asyncio.TimeoutError:
            try:
                await asyncio.to_thread(check_all_cameras, False)
            except HealthCheckInProgress:
                continue
            except Exception:
                logging.exception("Background camera health cycle failed")
