# Validation record — 2 October 2026

## Football continuation

The restoration results below describe the previous phase. The current football phase starts from `e65bbfd` on `cv/football-validation`; PR#1 was still open when work began. Full experiment definitions, source/licensing, baseline and after tables, limitations and reproduction commands are in [FOOTBALL_VALIDATION.md](FOOTBALL_VALIDATION.md); numeric evidence in [validation/results](../validation/results/football-2026-10-02.json).

| Current command (root unless noted) | Executed result |
|---|---|
| `.venv\Scripts\python.exe -m pytest backend/tests -q` | PASS, 58 tests; synthetic math/camera and mocked CV require no ML weights |
| `.venv\Scripts\python.exe -m ruff check backend scripts` | PASS |
| `.venv\Scripts\python.exe -m compileall -q backend/app scripts` | PASS |
| frontend `npm ci`, `npm run lint`, `npm run build` | PASS |
| `.venv\Scripts\python.exe scripts/test_e2e.py` | PASS, demo still supported |
| `.venv\Scripts\python.exe scripts/test_e2e.py --video test-artifacts/football/clips/steady/clip.avi` | PASS, real YOLO/worker/CPU, 200 football frames |
| `.venv\Scripts\python.exe scripts/smoke_real.py` | PASS, CPU people smoke; artificial projection explicitly isolated |

Football browser flow checks actual player/scout registration, login, profile save/refresh, upload202/queue, processing/selection refresh, gallery, longest-track selection, geometry submission, completed report/path/heatmap/refresh and scout directory/detail/report. Camera motion correctly blocks physical metrics even when test confirmation/corners are supplied. Selected ID1: 200 observed frames/67 saved samples. No happy-path console/page errors, HTTP≥400, broken images, worker crash or stuck job; expected invalid-JWT401 is separate. Screenshots at1440/768/390px and worker logs: ignored `test-artifacts/football/app-e2e/`. Representative [mobile report](football/report-mobile.png) was visually checked.

Three short CC BY UVY windows, one event, 700 frames; frozen independent50-frame agent visual ROI subset plus separate publisher semi-automatic/CVAT labels. This does not establish global accuracy. HD input detail improved matched player observations; ByteTrack, lower tracker thresholds and image-coordinate EMA were rejected as defaults after measured tradeoffs. Severe blur remains unusable. Physical accuracy **NOT VALIDATED**, no completely fixed-camera football footage or measured movement reference, CUDA **NOT TESTED**. Final sequential production CPU:8.489/8.296/19.893FPS (V04/V02/V01), excluding model load/upload/DB work.

Remote football CI: implementation/evidence commit `9316049cccf106c191343074c8d60687f37a5280`, [Actions run36932896192](https://github.com/alinur527/Scout.AI/actions/runs/36932896192): **backend, frontend and demo E2E all SUCCESS** on Linux. Backend installed only requirements-dev, with no Torch/Ultralytics/weights/GPU. The final documentation-only follow-up records this observed run; PR#2 exposes its own latest checks. No merge performed. Prior restoration CI below is historical.

## Restoration phase record

Only executed checks are marked PASS. Windows PowerShell, Python 3.12, Node 25.8.0, Chromium headless via Playwright 1.58.0. CI is configured for Python 3.12 / Node 22; remote run status is separate from these local results.

## Commands and outcomes

Paths below start from the repository root unless a working directory is noted.

| Command | Outcome |
|---|---|
| `py -3.12 -m venv .venv` | PASS |
| `.venv\Scripts\python.exe -m pip install -r backend/requirements-dev.txt` | PASS; subsequent security updates reflected in final requirements |
| `..\.venv\Scripts\python.exe -m pytest -q --tb=short` (backend/) | PASS, **16 tests** |
| `.venv\Scripts\python.exe -m ruff check backend scripts` | PASS |
| `.venv\Scripts\python.exe -m compileall -q backend/app` | PASS |
| `npm ci` (frontend/) | PASS |
| `npm run lint` (frontend/) | PASS |
| `npm run build` (frontend/) | PASS, Vite 7.3.6 |
| `npm audit --audit-level=low` (frontend/) | PASS, **0 vulnerabilities** |
| `.venv\Scripts\python.exe -m pip check` | PASS, no broken requirements |
| `.venv\Scripts\python.exe -m pip_audit --progress-spinner off` | PASS for scanned installed packages, no known vulnerabilities; local `torch==2.10.0+cpu` / `torchvision==0.25.0+cpu` wheels skipped by the advisory resolver |
| `.venv\Scripts\python.exe -m playwright install chromium` | PASS |
| `.venv\Scripts\python.exe scripts/test_e2e.py` | PASS; actual API, frontend and worker, temporary SQLite DB, no mocked routes |
| `.venv\Scripts\python.exe scripts/download_model.py` | PASS; official checkpoint downloaded, 6,255,593 bytes, not committed |
| `.venv\Scripts\python.exe scripts/smoke_real.py` | PASS; actual CPU inference and persisted completed job |
| `.venv\Scripts\python.exe scripts/check_repository.py` | PASS; no findings in reachable target history at scan time |

Backend tests cover health, register/duplicate/admin-role rejection, valid/invalid login, Argon2 storage, JWT expiry/malformed JWT, authenticated/unauthenticated profile, profile update/role restriction, video type/MIME/size/decoding validation, chunked request limits, safe filenames, persistent demo queue/selection/run/result, cross-user isolation, scout list/details, real missing-weights failure, restart recovery/expiry, homography, timestamp-based distance/sprints and outlier/gap rejection.

## Browser evidence

The `webapp-testing` skill's `with_server.py` was read, its `--help` checked, and it was actually used with reviewed absolute Python/Node executables for the first browser run. Subsequent runs use the committed equivalent wrapper `scripts/test_e2e.py`, including Windows process-tree cleanup. Reconnaissance saved the rendered DOM before interacting. All interactions used the real UI and API.

Executed flow:

1. Open app; inspect rendered login controls.
2. Register player; log in.
3. Edit name, position, age, team and bio; save; view profile; refresh and restore auth.
4. Upload a valid generated AVI; observe queued state before starting the real worker.
5. Observe processing/gallery; refresh while awaiting selection; select tracked demo player 1.
6. Build report; observe completed; inspect distance/top speed/sprints; switch heatmap/path; refresh report.
7. Log out; register scout; log in; search the newly saved player through `/players`.
8. Open player details and the persisted match report.
9. Verify scout cannot navigate to upload; verify unknown-route screen.
10. Inject an invalid test JWT; verify expected 401 and return to login.

The successful happy path produced **zero console/page errors and zero HTTP responses >=400**. The final invalid-JWT check deliberately produces 401 and Chromium's associated resource-console error; this is separated from the happy path in the script. No errors were hidden or ignored to obtain a pass.

Screenshots and horizontal-overflow assertions ran at **1440×1000**, **768×1024**, and **390×844** for login, profile, report, scout directory and player detail. Desktop login, tablet directory and mobile report were visually reviewed. Repository screenshots are copied from that run, explicitly using demo data. Full local evidence: `test-artifacts/e2e/` (ignored).

Initial browser failures were fixed and rerun: Position selector accessibility, stale profile after navigation, form reference after await. The numeric assertion initially used the machine locale; the browser test now explicitly selects en-US. No production result was changed to satisfy the test.

The first remote Linux E2E exposed an AVI MIME alias missing from the whitelist (415 on upload). The backend now also accepts `video/vnd.avi`, alongside the common legacy AVI types, with actual decoding still required. A regression test covers it; the browser script prints the file MIME and checks the upload response directly to improve diagnostics. This standard mapping is also present in [CPython's MIME table](https://github.com/python/cpython/blob/main/Lib/mimetypes.py).

## Real CV smoke evidence

Actual versions: Torch **2.10.0+cpu**, TorchVision **0.25.0+cpu**, Ultralytics **8.4.26**, Supervision **0.27.0.post1**, OpenCV **4.12.0.88**, NumPy **2.2.6**, SciPy **1.17.1**. Model: YOLO11n-pose. Device used: **CPU**.

The smoke script uses `ultralytics/assets/bus.jpg` already distributed with the installed package, shifts it across **24 MJPG video frames**, validates/decodes that video, starts actual pose/BoT-SORT inference and exercises the worker state transitions. Observed **4 tracked people**, **12 sampled observations** for the chosen track, a nonempty gallery, drawn annotations, movement/heatmap and `completed` with `demo=false`. Uncalibrated distance/speed/sprints remained null as intended.

An additional report calculation applies a deliberately artificial four-corner projection to the detected track. The real MatchAnalytics and RadarVisualizer execute and return metrics/radar. This checks code execution only: the scene is not a measured pitch, so its numbers are not physical accuracy evidence. The separate pytest real-mode test verifies missing weights persist `failed` with a useful error and no demo fallback.

At restoration time no suitable football ground-truth video was supplied. Football tracking and performance are now measured in the continuation report above. **Physical metric accuracy, live-match speed, multi-video throughput and CUDA execution remain untested.** Windows lists an NVIDIA RTX 5060 Laptop GPU, but the project environment installed the small CPU Torch build; `torch.cuda.is_available()` is false there. Multi-gigabyte CUDA dependencies were not downloaded. GPU hardware presence is not presented as a CUDA test.

Nonfatal upstream warnings: Starlette deprecates its httpx-backed TestClient in favor of httpx2; Supervision/pyDeprecate emit API deprecation warnings during real inference. They are visible in logs and did not prevent the verified flows.

## Security and provenance

The initial target README/commit remains in history. Upstream repositories are read-only. No old API/database source with embedded credentials or old history was imported. Target history was scanned for credentialed DB URLs, literal JWT keys, token/private-key patterns and forbidden media/model/database artifacts. The scanner is heuristic, not a mathematical proof that no secret can exist.

`.env`, DBs, uploads, videos, weights, logs and browser artifacts are ignored. Argon2/JWT and server-side owner/role checks have executed tests. Wildcard CORS is rejected. Registration cannot grant admin. Server-only UUID filenames are not exposed by job responses. CV failures persist and uploads are cleaned. Dependency advisories found during restoration were fixed; the Torch advisory lookup limitation above remains explicit.

Remaining verification gaps: live PostgreSQL, CUDA, calibrated football accuracy, production load, internet deployment hardening and full third-party licensing review. No public deployment was performed.

## SKILLS USED

| Skill | Stage | Concrete use |
|---|---|---|
| `frontend-design` | UI planning/build/critique | Subject-specific pitch visual, token/type/layout plan in DESIGN.md, responsive screens and screenshot review |
| `webapp-testing` | Integration/E2E | Read helper and --help; actual headless Python Playwright with API/frontend/worker, screenshots, request/console checks and iterative fixes |
| `grill-me` | Pre-implementation decision check | Read SKILL.md; followed its delegation to `grilling` (no separate Skill tool is exposed in this environment) |
| `grilling` | Audit and assumptions | Read-only factual code audits delegated per instructions; decision tree reconciled against explicit user requirements; no redundant interview contrary to the user’s autonomy instruction |
| `handoff` | Completion/context preservation | Temporary OS handoff file references this repository's audit/docs/checks and suggests appropriate skills for a follow-up, without secrets or duplicated specifications |
