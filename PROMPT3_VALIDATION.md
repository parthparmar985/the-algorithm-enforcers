# Prompt 3: Natural-Language Investigation Search

Validated on 2026-09-06.

## Implementation

- `backend/app/services/natural_investigation.py` provides a deterministic parser. It does not call an LLM or network service.
- `backend/app/api/routes/search.py` exposes authenticated `POST /api/search/natural` and routes parsed filters through the same `run_structured_search` function used by `GET /api/search/investigations`.
- `frontend/src/pages/Investigation.jsx` adds plain-language search, interpretation/warning display, ambiguity choices, and synchronization into the existing structured controls and result/timeline/GIS/evidence flow.
- `backend/tests/test_evidence_workflow.py` covers the required query matrix, time zones, ambiguity, malformed input, authentication, injection-style input, and regressions.

## Supported language

- Valid Indian registration numbers accepted by the shared plate normalizer.
- Vehicle types currently stored by the YOLO flow: car (including the word sedan), motorcycle/motorbike, bus, and truck.
- Actual camera database IDs (`Camera 4`), codes (`CAM-004`), names, and locations. Multiple matches return `AMBIGUOUS` with choices.
- `today`, `yesterday`, `last hour`, `last N hours`, `last N minutes`, `this morning`, `this afternoon`, and `this evening`.
- `between 8 PM and 10 PM`, `after 9 PM`, and `before 11 PM`.
- ISO dates, named dates such as `September 6` and `6 September`, and explicit ISO date/time ranges introduced with `from...to` or `between...and`.
- Combined supported filters.

Plain-language times are interpreted in Asia/Kolkata (UTC+05:30). Storage, API filter values, timelines, and reports remain UTC.

## Intentionally unsupported

The parser does not infer vehicle color, make, model, owner/driver, legal conclusions, or subjective terms such as `suspicious`. Unsupported tokens are returned for officer review, while any supported subset may still be searched.

## Validation

| Test | Result |
| --- | --- |
| Plate only | PASS: normalized GJ01AB1234; structured and natural result IDs matched |
| Plate + camera | PASS: Camera 2 resolved; one matching sighting |
| Location + relative time | PASS: actual location resolved; UTC window emitted |
| Vehicle type + date | PASS: car and named date parsed; two fixture sightings |
| Explicit clock range | PASS: 20:00-22:00 IST converted to 14:30-16:30 UTC |
| Combined query | PASS: plate, actual location/camera, and time range combined |
| Unsupported description | PASS: no invented color/make/driver filters; unsupported terms returned |
| Nonsense | PASS: `UNSUPPORTED`, zero results |
| Injection-style text | PASS: handled as text; vehicle table remained intact |
| Ambiguous camera location | PASS: `AMBIGUOUS`, two choices, no query executed |
| Empty/oversize input | PASS: Pydantic validation; maximum 500 characters |
| Invalid/contradictory time | PASS: controlled HTTP 400 |
| Authentication | PASS: unauthenticated request returned 401 |
| Actual configured database | PASS: 2 cameras loaded; plate query returned 1 record; `Sector 17, Gandhinagar` resolved to camera 1 and returned 1 record |
| Backend integration suite | PASS: 6 tests |
| Controlled ANPR | PASS: 24 detections/tracks; OCR GJO1AB1234 at 0.962; normalized/stored GJ01AB1234; search/timeline/GIS/evidence chain passed |
| Evidence/PDF/ZIP/SHA-256 | PASS: report text and three images verified; ZIP manifest/extraction/JSON/hashes verified |
| PDF visual inspection | PASS: all 3 pages rendered and inspected |
| WebSocket | PASS |
| Camera API/RBAC | PASS |
| Frontend lint | PASS with pre-existing warnings outside this change |
| Frontend production build | PASS; Vite reports the existing large-chunk advisory |
| Browser UI | NOT VERIFIED IN BROWSER: no browser instance was connected |

## Browser scope not verified

Investigation rendering, parsed-interpretation display, map tiles and markers, timeline/map interaction, evidence-basket clicks, empty/error states, and browser console state were not browser-verified because browser discovery returned no available browser.

## Remaining issues

- Interactive browser behavior remains unverified in this environment.
- The production bundle remains approximately 885 kB before gzip and triggers Vite's chunk-size advisory.
