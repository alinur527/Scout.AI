# Validation record — 2 October 2026

Only executed checks are marked PASS. Windows PowerShell, Python 3.12, Node 25.8.0, Chromium headless via Playwright 1.58.0. CI is configured for Python 3.12 / Node 22; remote run status is separate from these local results.

## Commands and outcomes

Paths below start from the repository root unless a working directory is noted.

| Command | Outcome |
|---|---|
| `py -3.12 -m venv .venv` | PASS |
| `.venv\Scripts\python.exe -m pip install -r backend/requirements-dev.txt` | PASS; subsequent security updates reflected in final requirements |
| `..\.venv\Scripts\python.exe -m pytest -q --tb=short` (backend/) | PASS, **15 tests** |
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

## Real CV smoke evidence

Actual versions: Torch **2.10.0+cpu**, TorchVision **0.25.0+cpu**, Ultralytics **8.4.26**, Supervision **0.27.0.post1**, OpenCV **4.12.0.88**, NumPy **2.2.6**, SciPy **1.17.1**. Model: YOLO11n-pose. Device used: **CPU**.

The smoke script uses `ultralytics/assets/bus.jpg` already distributed with the installed package, shifts it across **24 MJPG video frames**, validates/decodes that video, starts actual pose/BoT-SORT inference and exercises the worker state transitions. Observed **4 tracked people**, **12 sampled observations** for the chosen track, a nonempty gallery, drawn annotations, movement/heatmap and `completed` with `demo=false`. Uncalibrated distance/speed/sprints remained null as intended.

An additional report calculation applies a deliberately artificial four-corner projection to the detected track. The real MatchAnalytics and RadarVisualizer execute and return metrics/radar. This checks code execution only: the scene is not a measured pitch, so its numbers are not physical accuracy evidence. The separate pytest real-mode test verifies missing weights persist `failed` with a useful error and no demo fallback.

No suitable football ground-truth video was supplied. **Football tracking accuracy, metric accuracy, live-match speed, multi-video throughput and CUDA execution were not tested.** Windows lists an NVIDIA RTX 5060 Laptop GPU, but the project environment installed the small CPU Torch build; `torch.cuda.is_available()` is false there. Multi-gigabyte CUDA dependencies were not downloaded. GPU hardware presence is not presented as a CUDA test.

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
