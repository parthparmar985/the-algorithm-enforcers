# Prompt 4: Camera Health Monitoring

Validated on 2026-09-06.

## Status semantics

`Camera.status` remains the existing operator-configured runtime state for compatibility. It does not prove that a stream is reachable. `Camera.health_status` is measured by opening the validated stream and reading a real frame.

- `UNKNOWN`: no health check has completed, including migrated cameras and cameras whose stream URL changed.
- `ONLINE`: a connection opened, a non-empty frame was read, and measured open/frame latency was below 1500 ms by default.
- `DEGRADED`: the first failed check, or a successful frame whose measured latency was at least 1500 ms.
- `OFFLINE`: two consecutive failed checks by default. Further failures retain this state without generating more offline alerts.

Thresholds are bounded and configurable through `CAMERA_HEALTH_TIMEOUT_MS`, `CAMERA_HEALTH_OFFLINE_FAILURES`, `CAMERA_HEALTH_DEGRADED_LATENCY_MS`, `CAMERA_HEALTH_CONCURRENCY`, `CAMERA_HEALTH_INTERVAL_SECONDS`, and `CAMERA_HEALTH_OFFLINE_RETRY_SECONDS`.

## Implementation

- Camera health fields: status, last check, last successful connection, last valid frame, measured latency, failure count, stream availability, and diagnostic message.
- URL validation is shared by camera CRUD, live inference, streaming, and health probes. Only RTSP/HTTP/HTTPS with a host are accepted. File, FTP, JavaScript, link-local, multicast, unspecified, and default loopback targets are rejected. Loopback is available only through the explicit `CAMERA_HEALTH_ALLOW_LOOPBACK=true` test/development setting.
- OpenCV uses bounded open/read timeouts and releases `VideoCapture` in `finally`.
- Manual and bulk checks use per-camera locks. Bulk checks use a single-flight guard and 1-8 workers, defaulting to four.
- The periodic task starts once per FastAPI application process, waits 60 seconds by default, checks without blocking the event loop, backs off offline cameras to 180 seconds, and is cancelled at shutdown.
- State transitions are stored in the existing alerts table and sent through the existing thread-safe WebSocket manager.
- Latest detection timestamps are aggregated from the detections table rather than copied into cameras.

## API

- `GET /api/cameras/` now returns measured health and `last_detection_at`.
- `GET /api/cameras/health-summary` returns actual state counts.
- `POST /api/cameras/{camera_id}/health-check` performs one authenticated operator/admin check.
- `POST /api/cameras/health-check-all` performs an authenticated bounded bulk check.
- `GET /api/analytics/summary` now includes `camera_health` and uses measured online status.

## Validation

| Test | Result |
| --- | --- |
| Reachable stream | PASS: real local MJPEG endpoint opened and yielded a valid JPEG frame |
| Invalid/unreachable stream | PASS: reserved unreachable RTSP address returned failure |
| Timeout | PASS: 300 ms OpenCV timeout returned in under 2 seconds |
| Resource cleanup | PASS: fake capture verified `release()` after frame failure |
| UNKNOWN -> DEGRADED | PASS: first controlled failed check |
| DEGRADED -> OFFLINE | PASS: second controlled failed check |
| ONLINE | PASS: controlled valid frame at 80 ms |
| High-latency DEGRADED | PASS: controlled valid frame at 2000 ms |
| OFFLINE -> ONLINE | PASS |
| Offline alert deduplication | PASS: three failures produced exactly one `CAMERA_OFFLINE` alert |
| Recovery deduplication | PASS: repeated successes produced exactly one `CAMERA_RECOVERED` alert |
| WebSocket | PASS: offline and recovery events received through existing `/ws/alerts` |
| Bulk check | PASS: two cameras checked with bounded worker pool and correct totals |
| Authentication/RBAC | PASS: unauthenticated 401; viewer 403; operator/admin allowed |
| URL safety | PASS: file URL, localhost, and link-local metadata address rejected |
| Latest detection | PASS: camera API returned aggregate detection timestamp |
| Existing configured database | PASS: migration is idempotent; 2 existing cameras preserved as UNKNOWN; analytics and camera health counts agree |
| Background lifecycle | PASS: one app task created and the integration TestClient shut down without a lingering task |
| Backend integration | PASS: 7 tests, including camera CRUD, natural search, evidence, PDF/ZIP/SHA-256, and WebSocket |
| AI/ANPR | PASS: 24 detections/tracks, OCR 0.962, normalized plate stored and searched, timeline/GIS/evidence chain passed |
| Frontend build | PASS |
| Browser UI | NOT VERIFIED IN BROWSER |

The controlled transition values are explicitly marked `SIMULATION` in tests. Production endpoints do not provide fake-health controls.

## Scalability

This MVP limits probes within one application process. A production deployment could publish camera IDs to partitioned queues and run regional health workers with leases, per-network rate limits, centralized state transitions, and WebSocket/event fan-out. The probe/state contract can remain the same; that distributed infrastructure is intentionally outside this hackathon implementation.

## Remaining issues

- Browser rendering and interaction could not be verified without an available browser instance.
- The configured database currently has two cameras without stream URLs, so they remain `UNKNOWN` until real URLs are configured and checked.
- `JWT_SECRET` is unset in the current environment and remains ephemeral across backend restarts.
- Vite continues to report the existing large-bundle advisory.
