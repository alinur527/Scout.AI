# Legacy audit and restoration decisions

Audit completed before implementation against the snapshots in [PROVENANCE](PROVENANCE.md). Both source checkouts were read-only and clean. All 15 backend tracked files (11 Python files, including entrypoints, models, schemas, CV, tracker configuration and ignore rules) and all 21 frontend tracked files, including lock metadata, were inspected. No AGENTS.md applied.

## Backend findings

| Area | Legacy finding | Resolution |
|---|---|---|
| Entrypoints | Streamlit `app.py` had the CV loop; FastAPI `main.py` was a separate prototype | One React → FastAPI → persisted worker flow; Streamlit removed from primary startup |
| Inference | Two `run_full_inference` definitions; the second replaced the first with a fake report link; the first also fabricated results | One real detection/report service; explicit demo fixture branch |
| Gallery | API called nonexistent `VideoProcessor.extract_gallery` | Reuse the Streamlit crop algorithm during the same tracking pass as analytics |
| Database | Only User/Profile, conflicting Base, hardcoded PostgreSQL credentials, import-time connection | Shared SQLAlchemy Base; unique player profile; AnalysisJob JSON data persisted; SQLite or PostgreSQL URI from ENV |
| Authentication | Hardcoded JWT secret, uncontrolled registration role, unprotected task endpoints | Argon2id, expiring JWT, central current-user dependency, role checks, owner checks, no public admin registration |
| Jobs | Global in-memory dict; fake sleep; no recovery or cleanup | DB queue, one file-locked worker, atomic claim, interrupt recovery, retention and upload cleanup |
| Video | No type/size/content limits; whole upload in memory | Streaming writes, ASGI body cap, extension/MIME whitelist, OpenCV decoding/FPS/duration/resolution validation, UUID filenames |
| Dependencies | Freeze of Streamlit environment omitted API dependencies | Separate base/dev/CV requirements, Python 3.12, tested torch/torchvision pair |
| Secrets/history | Credentials existed in old source | Do not import old backend entrypoints or old history. Target initial README commit remains an ancestor |

## CV findings and retained algorithms

Retained `VideoProcessor`, `MatchAnalytics`, `FieldTransformer`, `AnnotationManager`, `RadarVisualizer` and their core approach: YOLO pose, tracked bounding boxes, ankle footpoints, four-corner homography, EMA, distance/speed/sprints, annotated frame and radar.

* Removed the fixed 1280×720 ROI and fixed Streamlit calibration. These were valid for only one camera.
* Removed the unused Supervision ByteTrack instance. The committed BoT-SORT configuration now controls the actual Ultralytics tracker.
* Removed the implicit model download, duplicate YOLO import, source-less CUDA warmup and unconditional CPU FP16.
* Added confidence checks for ankles and a bbox-bottom fallback. The pose model only detects people; fake ball/goal/assist/possession metrics were removed.
* Replaced the experimental auto-calibrator: it guessed a pixel-to-metre scale and silently returned an identity matrix. Manual homography now validates finite, nondegenerate, in-frame corners in perimeter order.
* Gallery and report use a single stored set of track IDs. No second inference pass that could assign a different identity.
* Analytics uses observation timestamps. It rejects >45 km/h discontinuities and gaps over one second instead of accumulating a huge distance while clipping displayed speed. EMA uses a time constant of 0.15 seconds. Sprints are sustained >21 km/h for 0.6 seconds, counted once per burst. Thresholds are heuristics, not validated benchmarks.
* Per-player heatmaps replace the misleading global heatmap. Without calibration, the report exposes image movement and null metric values; it never calls pixels metres.
* `if detections.empty` previously always evaluated truthy because it referenced a method. It now checks actual length. Radar orientation and NumPy truth-value handling were corrected.
* Tracks are sampled at approximately 10 Hz, outputs are bounded, invalid/empty videos and missing model dependencies become persisted failures with useful messages.

## Frontend findings

Old routes were `/login`, `/register`, `/profile/view`, `/profile/edit`, `/upload`, `/dashboard`; login redirected to nonexistent `/profile`. Dashboard was a hardcoded Arman/Daniyar array and action buttons were inert. Upload stopped after displaying a file ID. There was no status polling, player selection, report, scout details or history. Profile editing started blank; auth trusted localStorage role data, logged a token and had no global 401 recovery. Multiple clients hardcoded inconsistent localhost addresses.

Retained the React/Vite stack, Router, Axios and player/scout concept. Replaced scattered calls with one client and a documented API, restore auth from the server, route/role guards, labelled forms, profile prefill, persistent job views, real player directory/search, and a complete report. Removed dead clients, Vite branding, old CSS and fabricated players.

Browser testing found and fixed three integration defects introduced during restoration: ambiguous Position accessible name; cached profile surviving the edit/view route transition; and reading a React event's currentTarget after await. Locale was fixed in the test browser so numeric assertions are deterministic; the UI continues to respect the user's locale.

## Design decision tree (grill-me → grilling)

All product decisions were already authorized by the request: React/Vite, FastAPI, local SQLite, PostgreSQL configuration, explicit demo mode, no Telegram expansion, read-only legacy and target-only push. Environment/code questions were dispatched to read-only audit agents per grilling instructions. No new interview gate was introduced because the user explicitly required autonomous implementation and limited questions to missing credentials, destructive operations, very large downloads or radical product changes.

## Deliberate limits

Single worker and local disk are an MVP architecture. Interrupted active jobs fail explicitly; queued and waiting-for-selection jobs survive restart. Users re-upload to retry. No Alembic migration suite is needed for the initial schema; `create_all` does not migrate future schema changes. PostgreSQL runtime, CUDA, football accuracy and concurrent-user load have not been verified in this environment. See [VALIDATION](VALIDATION.md) for measured results, not assumptions.
