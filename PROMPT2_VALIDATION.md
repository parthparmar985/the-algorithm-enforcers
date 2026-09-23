# Prompt 2 - Investigation Search, Timeline, and ANPR Validation

Validated 2026-09-06. Prompt 1 evidence, PDF, ZIP, SHA-256 and RBAC workflows remain in place.

## ANPR finding and change

Prompt 1 used two inputs. The plate-only animation had readable text but no vehicle for YOLO to detect. The traffic footage produced real vehicle detections; visual inspection found UK registrations, including a readable `FL21 E50`, rather than an Indian plate. Direct EasyOCR on that crop produced raw `FLZIESO`. The previous preprocessing always resized the full vehicle crop to 120 pixels high, including downscaling a 531-pixel crop, and returned no OCR candidate. The original result was therefore caused by both unsuitable footage and destructive preprocessing.

ANPR now upscales only small crops, searches plausible plate-shaped regions plus lower-vehicle fallbacks, runs CLAHE/sharpened variants, and retries unresolved tracked vehicles every ten useful frames by default. It accepts only plausible Indian state/UT or Bharat Series formats. Normalization removes punctuation and spacing without changing characters. High-confidence OCR receives a narrow position-aware correction for common numeric slots; the raw OCR string is stored separately.

The controlled validation used a real car detected by YOLO in the existing traffic footage and rendered `GJ01AB1234` visibly on that car. This is a disclosed readability control, not a claim about the original UK plate. EasyOCR returned raw `GJO1AB1234` at 0.9620 confidence. Its high-confidence `O` in a numeric district slot normalized to `GJ01AB1234`.

The controlled clip was processed through upload, YOLO, ByteTrack, EasyOCR, normalization, database persistence and watchlist matching at two cameras. Results: 24 detections, 24 tracked detections, two stored normalized plates, two retained raw OCR strings, two alerts, two combined search results, two chronological timeline events, 1.51 km route distance, two evidence records, duplicate evidence deduplication, PDF, and ZIP.

Artifacts are under `backend/output/controlled-anpr/e6b17bbd-5a4b-4e5c-846a-7d87b17c2559/` and ignored by Git. `controlled_frame.jpg` shows exactly what OCR received; `results.json` records the result; `investigation.pdf` and `investigation.zip` are the resulting exports.

## Investigation behavior

`GET /api/search/investigations` supports combined `registration_number`, `vehicle_type`, `camera_id`, `location`, `start_time`, and `end_time` filters. Plate input is normalized. Date/time offsets are converted to UTC before querying. Invalid ranges return HTTP 400. Results are capped at 200 and ordered chronologically.

`GET /api/search/trace/{registration_number}` remains the route endpoint and now requires authentication. It and structured search share one timeline builder and transition calculation. Events contain camera/location, plate and raw OCR, plate and associated object confidence, snapshot, snapshot-provenance alerts, distance, time gap, speed and anomaly status.

The Investigation page retains Leaflet and the Prompt 1 evidence component. It adds the six filters, reset, loading/error/empty states, result selection, synchronized timeline/map selection, snapshots, alert badges, transition metrics, and timeline-to-evidence actions. Selecting a timeline card focuses its marker; selecting a marker selects the matching event and popup. Evidence actions save the existing vehicle record, so Prompt 1 duplicate constraints still apply. The shared summary now includes total route distance.

## Database

`vehicles.plate_raw_text` was added. Composite indexes were added for `vehicles(camera_id, first_seen)`, `vehicles(number_plate, first_seen)`, and `detections(camera_id, timestamp)`. `backend/migrate_evidence.py` applies these changes idempotently. They were applied to the workspace MySQL database and verified with SQLAlchemy inspection.

## Validation

| Test | Result |
|---|---|
| ANPR controlled test | PASS - real detector/tracker/OCR pipeline, disclosed rendered plate |
| Original footage classification | PASS - UK text observed/rejected; no Indian plate claimed |
| Plate normalization | PASS |
| Plate search | PASS on isolated test DB and existing MySQL |
| Combined filters | PASS |
| Date/time filtering and invalid range | PASS |
| Vehicle timeline | PASS - chronological two-camera fixture and controlled AI run |
| GIS route API | PASS |
| GIS browser rendering | NOT VERIFIED IN BROWSER - no browser backend connected |
| Timeline to Evidence | PASS through the same API/source ID; UI click not verified in browser |
| PDF export regression | PASS - text parsed and every rendered page visually inspected |
| ZIP export regression | PASS - exact safe paths, JSON and SHA-256 verified |
| WebSocket regression | PASS - connected client received broadcast |
| Login, camera CRUD, video upload, alerts | PASS via integration API |
| YOLO / ByteTrack | PASS - 24/24 detections tracked in controlled run |
| Frontend lint | PASS with unrelated existing warnings |
| Frontend production build | PASS |
| Investigation browser UI/console | NOT VERIFIED IN BROWSER - browser discovery returned no available browser |

Automated suite: `backend/venv/Scripts/python.exe -m unittest discover -s tests -v` (four tests, PASS). Controlled workflow: `backend/venv/Scripts/python.exe tests/run_controlled_anpr.py` (PASS). Frontend: `npm run lint` and `npm run build` (PASS). The production build retains the existing large-chunk warning.

## Remaining limits

Plate-region selection is heuristic and uses EasyOCR; it is not a dedicated plate detector. Accuracy still depends on plate size, angle, blur, lighting and visibility. Alerts can only be associated with a plate when they share snapshot provenance. The controlled two-camera runs occurred seconds apart, so the 1.51 km transition is correctly marked anomalous. Browser rendering, click interaction, map tiles and console output remain unverified because no browser was connected.

Prompt 2 verdict: the controlled workflow demonstrates `Detection -> ANPR -> Search -> Timeline -> GIS route API -> Evidence`. The UI build passes, but browser-level GIS and timeline interaction are not claimed as verified.
