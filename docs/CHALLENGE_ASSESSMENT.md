# Project challenge assessment

Audit date: 24 September 2026. Evidence: current repository, implementation changes, and tests executed during this audit. Earlier validation documents are not proof of current behavior. No vendor VMS, physical camera, WAN/VPN, production database, GPU, object store or multi-host deployment was available for acceptance testing.

All four formal challenges were initially **PARTIAL** and remain **PARTIAL**. Confidence is high in the repository findings, not in untested production behavior. Unavailable infrastructure checks are **NOT TESTABLE IN CURRENT ENVIRONMENT**.

## Initial assessment and remediation

Initially, camera URLs and uploaded files shared DetectionService, but a failed live read ended processing, runtime health was absent, duplicate starts loaded duplicate models, and missing URLs silently became generated demo feeds. Probe health was separate from processing; health broadcasts called a nonexistent method, rule alerts called undefined `run_async`, and exceptions were swallowed. Browser URLs assumed localhost. Model loading happened in the start handler and capture cleanup was not guaranteed.

| Challenge | Initial Status | Gap | Can Fix Safely Now? | Planned Change |
|---|---|---|---|---|
| 01 | PARTIAL | Localhost coupling; inconsistent upload root; mandatory cloud import | Yes, completed | Configurable frontend URL, consistent static root, optional cloud imports |
| 01 | PARTIAL | No VMS/discovery/storage/AMC abstraction | No small fix | Define adapters and validate real vendor systems |
| 02 | PARTIAL | No processing reconnect, timeout, telemetry, guaranteed release | Yes, completed | ResilientCapture, runtime measurements, bounded retry, cleanup |
| 02 | PARTIAL | Demo fallback and broken health broadcast | Yes, completed | Reject missing source; remove mock fallback; repair broadcast |
| 02 | PARTIAL | Browser socket never reconnects | Yes, completed | Shared reconnect helper with capped exponential delay |
| 03 | PARTIAL | Broken rule events and cross-camera progress/deletion | Yes, completed | Correct broadcast; camera-scoped progress and deletion |
| 03 | PARTIAL | No analytics contract; unvalidated OCR/rules | No broad rewrite | Typed analytics/events and labeled acceptance data |
| 04 | PARTIAL | Duplicate jobs and models loaded in start handler | Yes, completed | Reserve camera before scheduling; initialize in background task |
| 04 | PARTIAL | No leases, broker, shared storage, department isolation | No small fix | Design ownership and tenant boundaries before distribution |

Intentional behavior changes: missing streams return errors instead of simulated feeds; Cloudinary uploads require `CLOUDINARY_UPLOAD_ENABLED=true`; local snapshots remain default. Frontend uses `VITE_BACKEND_URL`. No migration is required for process-local runtime metrics; existing probe-health columns still require the existing camera-health migration on older databases.

## Challenge 01 — Heterogeneous Infrastructure

**Status: PARTIAL**

**Evidence / supported today.** `backend/app/api/routes/cameras.py:create_camera/update_camera` provides authenticated database-backed URL onboarding; `models/camera.py:Camera.stream_url` stores sources. `services/camera_url.py:validate_stream_url` permits RTSP, HTTP and HTTPS. A vendor exposing a compatible URL can be onboarded without source edits; no specific vendor interoperability is thereby proven.

`api/routes/video.py:upload_video` accepts `.mp4`, `.avi`, `.mkv` filename extensions; `process_video` accepts an existing server file path. Live execution is `start_live_inference → schedule_processing → DetectionService.process_video_file → ResilientCapture`. Preview separately opens a capture and returns multipart JPEG to browser `<img>` elements.

| Source | Implemented support | Actual verification |
|---|---|---|
| HTTP MJPEG | OpenCV FFmpeg capture | Real loopback probe and 1/2/4/8-stream ingestion |
| RTSP | Validated URL and FFmpeg capture | Failure/timeout and mocked recovery; no successful physical RTSP source |
| HTTPS | Validated URL and FFmpeg capture | No real TLS stream; certificate/decoder interoperability unverified |
| Local files | Upload/path API; automatic OpenCV backend | Real MP4 pipeline and generated MJPEG-in-AVI fixture |
| MKV / other codecs | Filename accepted; runtime decoder decides | Not independently decoded; no universal codec support claim |
| Webcam/device index | No device configuration or public input path | Unsupported despite theoretical OpenCV capability |
| ONVIF, proprietary VMS, discovery, SRT, WebRTC | No implemented integration found | Unsupported today |

OpenCV VideoCapture performs decoding. Network ingestion explicitly selects CAP_FFMPEG; files use automatic backend selection. No standalone FFmpeg process, GStreamer pipeline or vendor SDK was found. Compatibility depends on the installed OpenCV/FFmpeg build, codec, source authentication and transport. This environment used OpenCV 5.0.0.

**Storage.** `database/database.py` uses SQLAlchemy with environment-selected DATABASE_URL and a localhost MySQL/PyMySQL default. SQLite was actually tested; production MySQL was not. Detection, Vehicle, Alert, Investigation and Evidence store relational metadata. Uploaded clips and snapshots use local paths under UPLOAD_DIR; `main.py` now mounts the same root. There is no continuous camera recording/segmentation, retention manager, NAS adapter or object-store interface. Optional Cloudinary upload rewrites snapshot references asynchronously, whereas `evidence_service.snapshot_bytes` accepts restricted local files only. Cloud and local evidence are not interchangeable.

**Missing / risks.** Complete source/configuration searches found no VMS/ONVIF adapter, discovery, camera credential lifecycle or AMC workflow. Port 8080 still automatically appends `/video`, an IP-webcam assumption. Camera URL strings may contain credentials and are returned by camera APIs. `main.py` seeds a known admin password; helper scripts contain demo credentials; `init_db.py` assumes local MySQL; run/setup scripts target Windows/XAMPP. Existing `.env` secret values were not reproduced. File processing checks existence without restricting input to the upload root; preview and WebSocket routes lack authentication.

**Assessment answer.** Compatible URL cameras are straightforward to add. Heterogeneous proprietary VMS, storage and maintenance systems cannot be onboarded through a stable abstraction today.

**Recommended improvements.** Define source/VMS and storage interfaces; replace URL rewriting with explicit configuration; add credential references/discovery as supported by vendors; secure bootstrap/stream access; validate a real vendor/codec matrix.

## Challenge 02 — Geographical Dispersion

**Status: PARTIAL**

**Evidence.** `services/stream_runtime.py:ResilientCapture._open/read/release` requests 3-second FFmpeg open/read timeouts, releases failed captures, and allows six attempts with backoff waits of 1, 2, 4, 8 and 8 seconds. A good frame resets consecutive failures. Exhaustion ends the job; a later recovery needs another start request. Native backend timeout support is a dependency, not an OS-enforced guarantee.

`camera_health.py:probe_stream/apply_probe_result/check_all_cameras/monitor_loop` independently probes reachability. Defaults are a 60-second interval, four workers (configurable 1–8), two failed probes for OFFLINE, 1500 ms degraded latency, and 180 seconds between offline reprobes. Probes add a separate connection and do not restart analytics. Camera stores last probe/frame/online timestamps and transition alerts; UNKNOWN means unprobed, not healthy.

Authenticated `GET /api/video/{camera_id}/runtime-health` and `GET /api/cameras/` expose process-local runtime metrics. CameraManagement displays them on its 30-second polling cycle. Fields: camera_id, status ONLINE/DEGRADED/OFFLINE, active, processing_fps, decoder-reported source_fps, last_frame_at, frames_received, frames_processed, skipped_frames, failed_reads, consecutive_failures, last_error, mean processing latency, and application queue depth. Unprocessed cameras have null runtime metrics. State resets on a new run/process restart. A completed file is inactive/OFFLINE, not proof the physical camera is offline.

| Scenario | Final behavior | Limitation |
|---|---|---|
| Startup connection fails | OFFLINE, release and bounded retry | Actual successful remote reconnect not tested |
| Connection drops | Failed-read count and reopen/backoff | Verified with deterministic fake captures |
| Temporary outage | Recovers within retry budget | No WAN fault injection |
| Camera returns after exhaustion | Probe can recover; analytics needs manual restart | No durable supervisor |
| Slow stream | Frame gap >1.5 seconds marks DEGRADED | Includes inference/read time, not pure network delay |
| FPS drops | Processing rate and counts visible | No relative-FPS alarm; 30→5 FPS may remain ONLINE |
| Frames stop | Timeout/retry; last-frame age >5 s DEGRADED, >15 s OFFLINE at API read | Cannot force-kill a hung native thread |
| Network latency increases | Probe latency and frame-gap measurements | No jitter buffer policy/adaptive bitrate |
| Multiple cameras fail | Separate captures/sessions; per-job and per-probe errors contained | Shared thread pool, DB, memory/process remain common failure domains |

`frontend/src/services/endpoints.js:connectAlerts` retries WebSockets with a capped 30-second exponential delay. AlertContext retains at most 200 alerts. `websocket/manager.py` removes failed clients and bounds each send to two seconds. There is no durable replay, heartbeat, bounded outgoing queue or cluster fanout. Preview now requests timeouts and releases in finally, but still terminates at disconnection; the image consumer does not recover automatically. Browser reconnection was build-checked, not interactively failure-tested.

**Infrastructure assumptions.** This is centralized processing on the API server. No edge agent, metadata uplink or hybrid topology exists. Operation depends on routable endpoints, aggregate bitrate/bandwidth, latency/loss, firewall/VPN/security, credentials and server placement. Physical distance of 1,000 km is not a scalability metric and was not treated as proof of feasibility.

**Assessment answer / recommendations.** Ordinary network failures are handled more defensively, but reliable statewide service is not established. Add supervised cancellable camera workers, durable ownership, retry jitter, bounded latest-frame buffering and calibrated freshness/FPS alerts; recover previews and test actual WAN outages/latency/loss.

## Challenge 03 — Unified Analytics

**Status: PARTIAL**

**Pipeline / evidence.** Database URL or uploaded file → `video.py:schedule_processing` → `DetectionService.process_video_file` → `ResilientCapture.read` → source-FPS-based skipping → `cv2.convertScaleAbs(alpha=1.1,beta=5)` → `VideoAnalyzer.process_frame` using YOLO.track/ByteTrack, classes 2/3/5/7 → `ANPREngine.extract_number_plate` for selected crops → local snapshot and Detection/Vehicle persistence → watchlist match and RuleEngine.evaluate → Alert persistence → manager.sync_broadcast_alert → `/ws/alerts` → AlertContext. Detections/vehicles are fetched via `/api/detections/`, `/api/vehicles/` and search routes. VideoManagement filters progress by camera. Investigations associate detections by camera, track and sighting interval.

**Current analytics.** Vehicle detection/tracking, CPU EasyOCR on vehicle crops, watchlist matching, simplified rules, historical plate/route investigations and aggregate counts. OCR enhances the whole crop and permissively accepts text of length >=4; there is no dedicated plate detector. `ai/plate_utils.py` validation helpers are not wired into the live OCR path. `activity_detector.py:RuleEngine` calls a track stationary after 30 sightings without testing displacement; its motorcycle class differs from the detector's bike. Its person rule is unreachable through the vehicle-only detector. Crowd, helmet, wrong-way and abandoned-object analytics are absent. Dashboard “today” counts in `api/routes/analytics.py` actually count all rows.

| Framework question | Actual finding |
|---|---|
| Multiple cameras share pipeline? | Yes, common service code; models/services instantiated separately per job |
| Camera association? | Detection/Vehicle/Alert rows and now all progress events carry camera IDs |
| Consistent timestamps? | Mostly naive UTC database time; runtime uses explicit UTC offset; uploaded frames receive processing time, not capture time |
| Common event schema? | Similar ad hoc dictionaries, no validated/versioned contract; health/analytics fields differ |
| Consistent persistence? | Common tables, but per-frame/per-alert commits and async cloud rewrites; no transactional outbox |
| Multiple-camera frontend? | Shared alert socket consumes camera IDs, progress is scoped; no tenant/camera subscriptions |
| Extend modules? | Classes can be edited, but no plugin registration/configuration contract |
| Coupling to endpoint/camera? | Not hard-coded to a camera; tightly coupled to vehicle SQL models and large service method |
| New analytics without ingestion rewrite? | Capture reuse is feasible, but filters/service/storage/UI need changes; not a supported plugin capability |
| AI failure isolation? | Python exceptions clean up one job and mark it offline; OOM/native crashes remain process-wide risks |

**Tests.** Actual CPU uploads persisted 163 tracked detections and 18 vehicles; recognized plates and alerts were both zero. Real ANPR accuracy, natural watchlist triggers and rule correctness remain unverified. A disclosed controlled test stubs AI outputs while running real file capture, preprocessing, storage, rule broadcast call and model-failure cleanup. Existing tests exercise real WebSocket delivery for synthetic health alerts. Fixtures do not prove AI accuracy.

**Assessment answer / extensibility.** This is a shared vehicle pipeline, not a genuinely general analytics/event framework. Future intrusion/crowd/helmet/wrong-way/abandoned-object modules would need detector filters, typed outputs, per-camera configuration and appropriate schemas/rules; theoretical extensibility is not acceptance.

**Recommended improvements.** Extract typed frame context/analytics interfaces, versioned camera/time/job events, capture timestamps, transactional outbox and bounded track lifecycle. Validate OCR and rules independently using labeled footage.

## Challenge 04 — Scalability

**Status: PARTIAL**

**Computational evidence/limitations.** `DetectionService.__init__` loads YOLO and EasyOCR per job, not per frame. The singleton detector helper is unused by this path. Separate models preserve camera tracker separation but multiply memory/setup cost. OCR is CPU-only; YOLO now accepts YOLO_DEVICE=cpu. Every frame is decoded even when skipped. OCR upscales crops 2.5x and filters them; detections incur object rows/commits, watchlist queries and snapshots. Local JPEG writing plus separate encoding duplicates work. Optional Cloudinary uses unbounded per-snapshot threads and can race row commit; it is now disabled by default and imported only when enabled.

There is no application frame queue (queue_depth=0), but native decoder/socket buffers are unmeasured and may retain stale frames. Active vehicles, rule track maps, camera runtime registry and camera locks have no long-run eviction. Preview independently decodes/encodes per browser request; health probes and inference do not share it. No global admission limit, process isolation, inference batching or worker budget exists. WebSocket sends are serial; unawaited cross-thread scheduling can accumulate futures under load.

Heavy start work now runs inside a synchronous FastAPI background function, rather than in the start response handler. This still uses the application's thread resources, not durable workers. Probe monitoring offloads work through asyncio.to_thread; cancellation cannot terminate native blocking work. Browser camera/dashboard polling is 30 seconds, MJPEG preview aims at 15 FPS per client, and progress is emitted on processed frames. Browser alerts are bounded, but backend retention/event pressure is not.

| Addition | Current architectural impact |
|---|---|
| One compatible camera | API/UI registration and manual start; no source edits |
| Ten cameras | Same mechanics; full-pipeline capacity not established |
| Department | No department entity, tenant scope, camera ownership or event isolation |
| VMS | Compatible stream URLs work if available; otherwise custom integration |
| Analytics | Edit detector/service/models/events/UI; no plugin contract |
| Worker/server | Requires durable jobs/leases, shared transport and scheduling |
| Storage backend | Refactor direct filesystem/Cloudinary behavior into interface |

**Horizontal scaling.** Multiple processes may start, but correctness is not established. Each starts its own health monitor and keeps reservations, metrics, locks, trackers and sockets locally. Hosts can process the same camera and insert duplicates; events do not reach clients connected elsewhere. A common SQL database does not synchronize camera jobs. Files are local; JWT secrets differ unless explicitly configured; startup admin creation can race. Same-process duplicate-start prevention is not distributed ownership.

**Low-end hardware.** CPU-only execution ran successfully, but the traffic clip averaged 631.74 ms per processed frame and 1.39 processing FPS including setup. There is no claim of real-time support for any camera count on lower-end hardware. Frame/resolution budgets, OCR throttling and longer benchmarks are required.

**Assessment answer / recommendations.** Additional compatible cameras can be configured easily, but departments, servers and arbitrary integrations need substantial architecture work. Bound jobs/cloud/event queues and expire tracks; share capture; profile and budget inference/OCR; add durable leases/outbox/shared storage, then measure full workloads over longer runs.

## Executed tests and reproducibility

From backend:

```powershell
venv/Scripts/python.exe -m unittest discover -s tests -p 'test_*.py'
venv/Scripts/python.exe tests/benchmark_streams.py
venv/Scripts/python.exe tests/benchmark_streams.py --ai
$env:YOLO_DEVICE='cpu'
$env:CAMERA_HEALTH_MONITOR_ENABLED='false'
venv/Scripts/python.exe tests/run_real_inference.py
```

From frontend: `npm run build`.

Final combined suite: **15 tests passed**, comprising eight API/evidence/pipeline tests and seven runtime tests. Build passed with a large-chunk warning; git diff --check passed. Windows sandbox permissions initially blocked temporary SQLite access and Vite child processes; approved escalation enabled those checks. A test fixture was adapted for the correctly precreated upload directory. Missing Cloudinary exposed unnecessary import coupling, now removed for local processing. No cloud upload was tested.

Benchmark uses 640×360 loopback HTTP MJPEG, nominal 15 emitted FPS: 45 frames per stream for ingestion, 15 for CPU YOLO. Each AI stream has a separate model; Torch intra-op threads are set to two. Model loading is outside component timing, but first inference includes cold initialization, explaining why one-camera AI is slower than two-camera AI. Short runs are not steady-state sizing curves. CPU percentage is process CPU relative to one core and includes the synthetic server; values can exceed 100%. RSS includes test/models. OCR/database/browser work is excluded.

| Mode | Streams | Aggregate processing FPS | Mean read+process latency ms | Peak RSS MiB | CPU % of one core |
|---|---:|---:|---:|---:|---:|
| Ingestion | 1 | 15.09 | 66.05 | 63.0 | 3.7 |
| Ingestion | 2 | 30.19 | 66.04 | 65.6 | 7.3 |
| Ingestion | 4 | 60.18 | 66.28 | 72.8 | 13.5 |
| Ingestion | 8 | 120.20 | 66.38 | 85.3 | 18.6 |
| CPU YOLO only | 1 | 4.38 | 228.32 | 403.1 | 250.5 |
| CPU YOLO only | 2 | 26.62 | 74.90 | 477.5 | 622.7 |
| CPU YOLO only | 4 | 26.13 | 152.84 | 601.6 | 594.6 |
| CPU YOLO only | 8 | 22.84 | 350.34 | 840.5 | 657.6 |

Exact per-stream inference FPS is in [cpu-yolo.json](challenge-audit/cpu-yolo.json): 4.43 at one stream, 13.75–14.00 at two, approximately 6.68–6.98 at four and 2.85–3.16 at eight. Successful component runs report zero failed reads and zero deliberate skips; application queue depth is zero. Packet loss, pre-decode drops and native buffer depth are **not measured**, not claimed zero. Decoder FPS reported 25 despite a 15-FPS generator: source_fps is metadata, not measured arrival rate.

The initial ingestion run interrupted three four-camera workers at 25 frames when memory exceeded 85%; the guard did not propagate that stop to later stages. The harness was corrected to latch the stop, then rerun successfully. [ingestion-initial-interrupted.json](challenge-audit/ingestion-initial-interrupted.json) is retained but excluded from acceptance. Final results: [ingestion.json](challenge-audit/ingestion.json). No machine instability was observed. These runs do not certify sustained eight-camera service.

[Real full-pipeline results](challenge-audit/real-inference.json): plate-only clip had 45 received/15 processed/30 skipped, 2.24 FPS, 58.20 ms mean processing time; traffic had 150/30/120, 1.39 FPS, 631.74 ms. Both had zero failed reads. Full-pipeline CPU/RSS and concurrent OCR capacity were not measured. Zero plates were recognized; no fabricated plate completed exports.

## Final challenge acceptance matrix

| # | Challenge | Status | Confidence | Key Evidence | Main Gap |
|---|-----------|--------|------------|--------------|----------|
| 01 | Heterogeneous Infrastructure | PARTIAL | High | Database onboarding; real HTTP/file decoding; configurable deployment URL/root | No VMS/discovery/storage/AMC adapters; vendor matrix unverified |
| 02 | Geographical Dispersion | PARTIAL | High | Recovery tests, probe health, runtime metrics, cleanup | No WAN acceptance, durable restart, preview recovery or process isolation |
| 03 | Unified Analytics | PARTIAL | High | Shared service; 163 detections; controlled events and camera IDs | No analytics/event contract; no successful ANPR; simplistic rules |
| 04 | Scalability | PARTIAL | High | Progressive component benchmarks; same-process duplicate protection | Per-job models, retained state, no distributed ownership/tenant design |

## Traceability matrix

Paths are relative to repository root. PASS applies only to the narrow capability, not its whole challenge. Runtime unit tests are in `backend/tests/test_stream_runtime.py`; API/integration checks are in `backend/tests/test_evidence_workflow.py`.

| Requirement | Implementation | Files | Test | Result |
|-------------|----------------|-------|------|--------|
| Database/API camera onboarding | create_camera/update_camera, Camera | backend/app/api/routes/cameras.py; backend/app/models/camera.py | API create/update/URL validation | PASS |
| Actual HTTP ingestion | FFmpeg capture | backend/app/services/stream_runtime.py; backend/app/services/camera_health.py | Loopback probe and benchmark_streams.py | PASS |
| Local video pipeline | Upload/process and DetectionService | backend/app/api/routes/video.py; backend/app/services/detection_service.py | run_real_inference.py and AVI fixture | PASS |
| Successful RTSP/HTTPS vendor interoperability | Accepted schemes/network open | backend/app/services/camera_url.py; backend/app/services/stream_runtime.py | RTSP failure only; no vendor source | NOT TESTABLE IN CURRENT ENVIRONMENT |
| VMS/ONVIF/device/AMC integration | Absent | Repository-wide source/config search | Static inspection | FAIL |
| Bounded retry and ordinary capture cleanup | ResilientCapture | backend/app/services/stream_runtime.py | Startup/drop/exhaustion/exception unit tests | PASS |
| Runtime measurement/staleness | snapshot/processed/skipped and API | backend/app/services/stream_runtime.py; backend/app/api/routes/video.py | Unit tests, actual counters and API response | PASS |
| Probe transition persistence and events | apply_probe_result and broadcast | backend/app/services/camera_health.py; backend/app/websocket/manager.py | Health API/WebSocket integration | PASS |
| Long-outage autonomous restart | Finite retry only | backend/app/services/stream_runtime.py | Static trace | PARTIAL |
| Camera isolation | Per-camera capture/session, shared process | backend/app/services/stream_runtime.py; backend/app/services/detection_service.py | Fake failed/healthy capture and model-exception tests | PARTIAL |
| Vehicle inference/persistence | YOLO/ByteTrack and relational rows | backend/app/ai/detector.py; backend/app/models/detection.py | Real 163 detections/18 vehicles | PASS |
| Real ANPR/watchlist capability | EasyOCR and match query | backend/app/ai/anpr.py; backend/app/services/detection_service.py | No recognized plates from real clips | PARTIAL |
| Unified extensible analytics/events | Shared vehicle service; ad hoc payloads | backend/app/services/detection_service.py; backend/app/ai/activity_detector.py | Static trace and controlled rules | PARTIAL |
| Camera-scoped progress | Camera ID and browser filter | backend/app/services/detection_service.py; frontend/src/pages/VideoManagement.jsx | Integration execution/build; no interactive browser test | PARTIAL |
| Browser socket recovery | connectAlerts | frontend/src/services/endpoints.js | Build only | PARTIAL |
| CPU-only execution | YOLO_DEVICE=cpu, OCR gpu=False | backend/app/ai/detector.py; backend/app/ai/anpr.py | CPU component and full pipeline runs | PASS |
| Production multi-camera capacity | Per-job models/background tasks | backend/tests/benchmark_streams.py | Short component runs only | PARTIAL |
| Departments / distributed ownership | No tenant model/leases/broker | backend/app/models; backend/app/main.py; backend/app/websocket/manager.py | Static inspection | FAIL |
| Local evidence export | Restricted paths and checksums | backend/app/services/evidence_service.py; backend/app/api/routes/evidence.py | API tests with synthetic data, PDF/ZIP/hash checks | PASS |
| Interchangeable storage | Local files plus optional Cloudinary | backend/app/services/evidence_service.py; backend/app/services/detection_service.py | Local only; cloud untested | PARTIAL |

## PROJECT CHALLENGE ASSESSMENT

Heterogeneous Infrastructure: **PARTIAL**.
Reason: Database/API onboarding and tested HTTP/file decoding support compatible sources without camera-specific edits. No VMS, discovery, AMC or interchangeable storage integration exists; real vendor RTSP/HTTPS compatibility was not verified.

Geographical Dispersion: **PARTIAL**.
Reason: Measurements, timeouts, bounded retries and cleanup improve centralized ingestion. WAN acceptance, persistent restart, native process isolation and preview recovery remain missing.

Unified Analytics: **PARTIAL**.
Reason: Cameras share the vehicle pipeline and relational records, and tests confirm persistence and controlled events. There is no general analytics contract; current rules have semantic gaps and real samples produced no plate recognition.

Scalability: **PARTIAL**.
Reason: Actual CPU operation and progressive component tests provide local evidence. Per-job models, retained state, local files/sockets and absent worker ownership prevent production horizontal-scaling acceptance.

FULLY SATISFIED:
None of the four complete formal challenges. Narrow verified capabilities are PASS in the traceability matrix.

PARTIALLY SATISFIED:
All four formal challenges.

NOT SATISFIED:
VMS/ONVIF/device discovery, AMC workflows, interchangeable storage, department isolation, durable distributed ownership, general analytics plugins/events, autonomous restart after exhausted retries, and unimplemented future analytics examples.

NOT VERIFIED:
Real vendor RTSP/HTTPS/codecs; WAN/VPN/loss/latency operation; production MySQL/multi-host synchronization; cloud/evidence interoperability; natural-footage ANPR/watchlist accuracy; interactive browser recovery; GPU and sustained full-pipeline concurrency.

TOP 5 REMAINING GAPS:
1. No durable camera/job ownership, cancellation and supervision across workers.
2. No real-validated vendor/VMS and storage adapter contracts.
3. No validated general analytics/event contract; OCR and rules lack acceptance evidence.
4. Retained long-running state, optional upload/event queues, duplicate preview decoding and per-job model cost.
5. Missing department/access boundaries and secure remote deployment verification.

NEXT 5 RECOMMENDED ENGINEERING ACTIONS:
1. Add supervised bounded workers, camera leases and durable stop/restart/job state.
2. Introduce source/storage adapters and execute vendor/codec/WAN fault acceptance tests.
3. Extract typed analytics/events, capture timestamps and transactional outbox; validate OCR/rules on labeled footage.
4. Add track TTLs, bounded upload/event queues, shared capture and long-duration full-pipeline resource tests.
5. Implement department authorization, authenticated streams/events and secure credential/bootstrap configuration.
