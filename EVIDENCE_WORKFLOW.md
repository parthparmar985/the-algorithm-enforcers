# Evidence Management and Investigation Reports

Implemented on 2026-09-05. Existing AI, tracking, WebSocket and GIS architecture is retained.

## Setup

From `backend`, install `venv/Scripts/python.exe -m pip install -r requirements.txt`, then run `venv/Scripts/python.exe migrate_evidence.py` and restart the backend. The migration has already been applied to this workspace's MySQL database. It adds `investigations` and `evidence`, and drops the unused `incidents` table only if empty. It refuses to delete populated legacy incident data. Application startup also creates the two new tables on fresh databases.

Existing ADMIN and OPERATOR roles may investigate. References belong to their creator; another operator cannot list, preview, delete or export their evidence. ADMIN may access all references. Public registration now always creates OPERATOR accounts, closing the existing self-assigned ADMIN vulnerability. Existing accounts retain their roles.

## UI workflow

Search a plate in Investigation. The page opens/reuses your saved reference for that plate. Review the actual summary and route, then add plate sightings from the existing evidence board, add detections/related alerts from the expandable results, or add the route/GIS trace. Enter an optional description before adding an item.

The persistent Evidence Basket supports authenticated snapshot/metadata preview, selection checkboxes, removal, PDF generation and ZIP download. Only checked items are exported. Duplicate sources appear once. Removal retains the original recording/snapshot. A missing or changed selected file blocks export with an error; a record that never had a snapshot remains usable as metadata-only evidence.

PDFs include UTC timestamps, counts, camera timeline, ordered location table, related alerts, selected evidence snapshots and SHA-256 values, and a human-verification disclaimer. No external map/image service is needed to generate a report. Metadata includes the entire current plate investigation context and only the selected evidence records/files. Saved route evidence additionally preserves its route at selection time.

## APIs

All paths below require a bearer token, plus ADMIN or OPERATOR role.

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/evidence/investigations` | Create/reuse own plate reference |
| GET | `/api/evidence/investigations/{reference}` | Summary, detections, vehicles, alerts, cameras and route |
| POST | `/api/evidence` | Save a database source or route |
| GET | `/api/evidence` | List with reference, plate, camera, time and type filters |
| GET | `/api/evidence/{id}` | Metadata and current file status |
| GET | `/api/evidence/{id}/file` | Authenticated hash-checked image preview |
| DELETE | `/api/evidence/{id}` | Remove an authorized basket item |
| POST | `/api/evidence/export` | PDF or ZIP for selected IDs |

Creation accepts `investigation_id`, `evidence_type`, exactly one of `vehicle_id`, `detection_id`, `alert_id`, and optional `description`. ROUTE_TRACE takes no source ID. Supported types: SNAPSHOT, DETECTION, ALERT, PLATE_DETECTION, ROUTE_TRACE. Uploaded video clips have no existing persisted clip/source model, so arbitrary video paths are not accepted.

List filters: `investigation_id`, `plate`, `camera_id`, `start_time`, `end_time`, `evidence_type`.

Export body: `{ "investigation_id": "<reference>", "evidence_ids": [1, 2], "format": "zip" }`. Formats are `pdf` and `zip`; 1–100 IDs, deduplicated. Source paths come exclusively from database records, resolve inside configured `UPLOAD_DIR/snapshots`, and are never exposed in evidence responses. Only JPEG/PNG snapshots are included; traversal, out-of-root paths and file hash changes are rejected. Each image is limited to 20 MB.

ZIP layout: `investigation/report.pdf`, `metadata.json`, `timeline.json`, `route.json`, and `evidence/evidence_<id>.jpg|png`, all under `investigation/`.

## Data association limits

There is no existing detection-to-vehicle foreign key. Detections are associated using camera, tracking ID and the vehicle's first/last-seen interval (one second tolerance for insertion order). This reduces cross-video tracking-ID collisions but remains an inferred association requiring review.

Alerts have no plate or detection foreign key. Only shared snapshot paths establish a relationship; unrelated camera alerts are not claimed as vehicle alerts. Metadata-only rule alerts therefore do not appear as related plate alerts. Summary counts reflect these database associations. Hashes demonstrate file consistency, not authenticity or a full chain of custody.

## Files

Created:

- `backend/app/models/evidence.py`
- `backend/app/api/routes/evidence.py`
- `backend/app/services/evidence_service.py`
- `backend/app/services/investigation_report.py`
- `backend/migrate_evidence.py`
- `backend/requirements-test.txt`
- `backend/tests/test_evidence_workflow.py`
- `backend/tests/run_real_inference.py`
- `frontend/src/components/InvestigationEvidence.jsx`
- `EVIDENCE_WORKFLOW.md`

Modified: `.gitignore`, `backend/app/main.py`, `backend/init_db.py`, `backend/requirements.txt`, `backend/app/api/routes/auth.py`, `frontend/src/pages/Investigation.jsx`.

Removed: `backend/app/models/incident.py`. Pre-existing uncommitted AI/connectivity edits were retained.

## Validation performed

Run from backend:

```powershell
venv/Scripts/python.exe -m pip install -r requirements-test.txt
venv/Scripts/python.exe -m unittest discover -s tests -v
venv/Scripts/python.exe tests/run_real_inference.py
```

The three integration tests exercise real API authentication, database writes/queries, report generation, ZIP extraction and file integrity using explicitly synthetic fixtures in an isolated SQLite database. Renderer failure is mocked only to test controlled error handling; PDF/ZIP success paths are not mocked. Actual MySQL login, reference creation, evidence creation, summary and ZIP export were also executed using the existing GJ01AB1234 sighting. That sighting has no snapshot and zero associated detections/alerts; its export correctly reports those facts. One reference and plate evidence item from that validation remain in the admin basket.

| Test | Result |
|---|---|
| Add evidence, list, filter | PASS |
| Preview | PASS, API bytes and metadata; UI not exercised |
| PDF generation and contents | PASS; pypdf text checks, three image placements, rendered pages visually inspected |
| ZIP generation and extraction | PASS; exact expected manifest, JSON parsed, extracted files checked |
| SHA-256 | PASS; extracted file hashes match stored values |
| Authentication / RBAC | PASS; all evidence routes reject missing token, other operators denied, admin allowed, unsupported role denied |
| Traversal / arbitrary path inclusion | PASS; request paths rejected, database path escape attempts rejected |
| Empty / invalid / duplicate selections | PASS; controlled errors or deduplication |
| Missing/deleted file and hash mismatch | PASS; metadata reports issue, preview/export rejects |
| Simulated PDF/ZIP renderer failure | PASS; controlled 500 response |
| Login, dashboard statistics, camera CRUD, alerts, investigation search | PASS, API |
| WebSocket | PASS; connected and received broadcast payload |
| Cross-camera trace / GIS coordinates | PASS, API with two-camera fixture; map UI not exercised |
| Video upload and actual YOLO/ByteTrack inference | PASS; 48 detections, 45 tracked detections, 5 vehicles, 1 alert |
| Complete AI -> plate -> evidence workflow | FAIL to complete: actual input clips produced no plate |
| Frontend production build | PASS |
| Frontend lint | PASS with pre-existing warnings |
| Browser clicks, GIS rendering, live CCTV | NOT VERIFIED; no connected browser or live camera test |

Actual AI inputs were the supplied 45-frame plate-only sample and six seconds of existing traffic footage `088a8489-f35c-4fa9-b8fc-d77250832ad0.mp4`. No detections, plates or alerts were seeded into that AI run. The watchlist contained the sample plate as a test condition. The supplied plate-only graphic is not a detected vehicle, and neither input produced an ANPR result through the pipeline. No synthetic plate was substituted to claim completion.

Local validation artifacts (ignored by Git): `backend/output/evidence-validation/` contains the PDF, ZIP and extracted package; `mysql-package.zip` and `mysql-extracted/` contain the existing MySQL-record export. Actual inference results and database: `backend/output/real-inference/e308cfe6-f0a8-412e-9151-17b74c0134ed/`.

## Remaining issues and demo status

The requested full CCTV -> AI -> ANPR -> alert -> investigation -> trace -> GIS -> evidence -> PDF -> ZIP demo is **not confirmed end to end**. ANPR did not produce a plate on the tested clips, and no browser was connected to validate the UI/GIS/live stream. Evidence -> PDF -> ZIP is verified through APIs with both fixture data and existing MySQL data. Alerts without shared snapshot provenance cannot be attributed to a plate under the current model. The build retains its existing large-bundle warning.
