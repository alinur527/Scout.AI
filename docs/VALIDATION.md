# Validation record

## Portfolio v1 candidate — 3 October 2026

Release preparation starts after [PR #4](https://github.com/alinur527/Scout.AI/pull/4), verified at `40351dd18faca0ba9d3136ed83c5773fccbbf9fd` with [Actions 37045893830](https://github.com/alinur527/Scout.AI/actions/runs/37045893830) and merged as `445a400c77ce343f84ad4fc648c4bd6b633577e2`. Fresh baseline: 106 tests, Ruff, frontend install/lint/build and reachable-history scan passed. No baseline test failures were found.

The candidate adds consent/privacy, history/export/print, migrations and reproducible native/Compose operation. Production CV models, thresholds, detector policy, inference algorithms and safety gates are unchanged. No new video or model downloads were needed. Existing panoramic/broadcast clips and weights were reused; the historical experiment matrix was intentionally not rerun.

| Executed command / check | Result |
|---|---|
| `.venv/Scripts/python.exe -m pytest -q backend/tests` | PASS, 117 tests, 0 skipped; one upstream Starlette/httpx deprecation |
| `python -m ruff check backend scripts`; `python -m compileall -q backend/app scripts` | PASS |
| Frontend `npm ci`, `npm run lint`, `npm run build`, `npm audit --audit-level=low` | PASS; clean native setup also installs/builds twice; 0 npm vulnerabilities |
| `python -m pip check`; `python -m pip_audit --progress-spinner off` | PASS; audit found no known vulnerabilities among audited packages; local `torch 2.10.0+cpu` and `torchvision 0.25.0+cpu` skipped because PyPI could not match those wheel identifiers |
| `python scripts/test_native.py` | PASS, fresh OS-temp source copy without env/venv/node_modules/DB/weights; both setup runs, full browser flow, restart persistence, unchanged config bytes/all DB rows, repeated start/stop, second worker, foreign port, stale PID, worker lock and partial-start rollback |
| `docker compose -p scoutai-v1-validation build` then `up -d --wait` | PASS locally on Docker Desktop, Engine 29.8.0; API/worker/frontend healthy |
| `scripts/e2e.py` against Compose `8080` and `/api`, managed worker | PASS; restart preserved all test users/profile/job rows on named volume |
| `python scripts/test_e2e.py` | PASS, production-built DEMO UI; later native/Compose flows also exercised cached-report revocation |
| `python scripts/test_e2e.py --video test-artifacts/football/soccertrack/117093/window/clip.avi` | PASS, actual CPU REAL panorama, 120 decoded frames, person profile, physical metrics null |
| Broadcast browser flow with reviewed webapp-testing `with_server.py` and `scripts/e2e.py` | PASS, actual CPU REAL `steady/clip.avi`, 200 frames, pose profile, camera-motion veto, physical metrics null |
| `python scripts/smoke_real.py` | PASS, actual CPU inference: 24 frames, 4 IDs, 12 selected observations; blank-frame REAL input failed clearly, export denied, no DEMO fallback |
| Fresh + original-schema upgrade + repeated upgrade + isolated restore | PASS in backend tests; original users/hashes/jobs/results retained; old profiles private; unknown/missing-constraint schemas rejected |
| `scripts/backup_sqlite.py` on isolated native test database | PASS, SQLite backup API and integrity check; real user DB untouched |
| Responsive UI and print | PASS overflow assertions at 1440/768/390 px; report, entry, gallery, tablet scout and mobile/print captures inspected; print action invoked and Chromium PDF rendered |

The [machine-readable summary](../validation/results/portfolio-v1-2026-10-03.json) records run IDs and results extracted from actual artifacts. Local artifact directories are ignored and use UTC names; the release document date is Asia/Qyzylorda. Native evidence: `test-artifacts/native/20261002T200742467874Z/`. Compose evidence: `test-artifacts/e2e/20261002T201000Z-compose-demo/`. REAL runs: `20261002T200955448189Z-real-window` and `20261002T201256448802Z-real-steady-helper`. CPU smoke: `test-artifacts/real/20261002T201844959253Z-cpu-smoke/`. Runs remain separate.

Browser checks include registration/login/profile, synthetic sample or real upload, queue/stages/gallery/selection, saved report/history/relogin, protected JSON export, print rendering, explicit publication, scout search/detail/report and revocation of a report already open in another context. Happy-path console/HTTP errors are zero. Expected negative 404 (revocation) and 401 (invalid JWT) occur after that assertion. API tests cover private foreign IDs, admin registration rejection, expired/malformed JWT, malformed/oversized upload, missing weights, permissions and cleanup/recovery. Actual blank-video inference checks no-detections failure. The smoke's artificial calibration fixture is isolated/rolled back and is not physical-accuracy evidence.

Read-only agent reviews checked access/export, migration adoption, native process identity, cleanup, Compose and notices. Concrete findings (CI missing build, person-only doctor requirement, orphan cleanup, cached-revocation coverage and migration constraints) were fixed and verified. This is agent review, not human approval. The initial print-action test exposed a test-expression side effect; it was corrected and rerun. An initial Docker build hit Debian network errors; the final image uses the same OpenCV version's headless wheel without unnecessary GUI libraries and built successfully. Failed attempts are retained in local artifacts and are not counted as PASS.

Unverified: CUDA, live PostgreSQL, public hosting, industrial load and physical measurement accuracy. Upstream inference deprecation warnings remain. Audits/scanners are bounded checks, not security certification. Final remote candidate CI and publication status are recorded in the PR/release draft; historical CI below is not evidence for the candidate. Public v1 remains held for [rights confirmation](PROVENANCE.md#publication-status).

## Player filtering and continuity phase (historical)

PR#3 was checked at `54f5c25428fc94af9945841a4a2d528bbe4e1d24`: base main, mergeable, scoped diff, local77-test/Ruff/security PASS and [CI37039995800](https://github.com/alinur527/Scout.AI/actions/runs/37039995800) backend/frontend/E2E SUCCESS. It was merged as `e423ae6dd4d8d046c58c17304fa0094100bd3151`; clean updated main was the base of `cv/player-filtering-continuity`.

Status **PARTIAL**: pitch/kit filters failed DEV; conservative continuity improved DEV but produced no links or improvement on the new TeamTrack fisheye sealed source after freeze `6dbf40104b6cb7453a10fb2a975e70b3526c3126`. Production config/inference were restored to main. Final actual-processor runs match six prior clips' raw/tracked scores, identity coverage, IDs/switches/fragments and small-player bins exactly. Source/license/false-merge evidence, timing caveats and commands: [PLAYER_FILTERING_CONTINUITY.md](PLAYER_FILTERING_CONTINUITY.md); [final regression + E2E](../validation/results/player-filtering-regression-2026-10-02.json).

| Executed local command | Result |
|---|---|
| `.venv\Scripts\python.exe -m pytest backend/tests -q` | PASS,106 tests; one upstream Starlette deprecation warning |
| `.venv\Scripts\python.exe -m ruff check backend scripts` | PASS |
| `.venv\Scripts\python.exe -m compileall -q backend/app scripts` | PASS |
| frontend `npm ci`, `npm run lint`, `npm run build`, `npm audit --audit-level=low` | PASS,0 vulnerabilities |
| `.venv\Scripts\python.exe scripts/test_e2e.py` | PASS, demo |
| `scripts/test_e2e.py --video test-artifacts/football/soccertrack/117093/window/clip.avi` | PASS, real panorama120frames |
| `scripts/test_e2e.py --video test-artifacts/football/clips/steady/clip.avi` | PASS, real broadcast200frames |
| `.venv\Scripts\python.exe scripts/smoke_real.py` | PASS, CPU24frames/4IDs/12selected observations; artificial math separate |
| Actual `--production` harness + SoccerTrack/UVY scorers on six clips | PASS, exact baseline agreement |

Browser flows covered register/login/profile/save/refresh/upload202/queued/processing/gallery/selection/report/refresh/scout/search/saved report/guards/404 with temporary SQLite and actual worker. Happy-path console/page/HTTP/image failures0; intentional invalid JWT produces two expected401 responses outside that assertion. Overflow checks1440/768/390 PASS; panoramic390 and broadcast1440 report images inspected. Real-run outputs share an ignored folder and earlier records are overwritten; numeric evidence discloses this. Physical metrics remain unavailable, physical_accuracy=not_validated. Current remote PR checks must be read from its final head; historical CI below is not evidence for this round.

## Small-player phase (historical)

PR#1 was verified open/mergeable against main, with green [CI36928035973](https://github.com/alinur527/Scout.AI/actions/runs/36928035973), and merged as `d03a2700317c751ea50bbb050a584801fd215d77`. PR#2 base changed from revive/scout-ai to main without rewriting its head/history; the resulting5-commit/39-file diff contained only football-phase changes. Local58-test/backend/frontend/demo/CPU/three-clip regressions and [CI36933062448](https://github.com/alinur527/Scout.AI/actions/runs/36933062448) passed before merge `24a389bad4aa2b777f04eb8fe25c1b895e680b07`. Main was updated by fast-forward and clean before creating independent `cv/small-player-detection`. Historical branches remain.

The new phase adds three different SoccerTrackv2 matches, a preregistered DEV/HOLDOUT split, a bounded detector/ROI/tiling matrix and one frozen-candidate holdout round. Protocol, sources, rejected regressions and measured results: [SMALL_PLAYER_EXPERIMENTS.md](SMALL_PLAYER_EXPERIMENTS.md); [numeric evidence](../validation/results/small-player-2026-10-02.json). Raw detection F1 rose0→.7302/.4492 on DEV and0→.5067 on HOLDOUT; this is publisher-box agreement on short panoramic windows, not global football accuracy. Auto chooses person weights only for panoramic geometry; ordinary broadcast stays on configured pose weights. Physical accuracy remains **NOT VALIDATED**, CUDA **NOT TESTED**.

| Executed local command | Result |
|---|---|
| `.venv\Scripts\python.exe -m pytest backend/tests -q` | PASS,77 tests; weights/GPU-free deterministic tests |
| `.venv\Scripts\python.exe -m ruff check backend scripts` | PASS |
| `.venv\Scripts\python.exe -m compileall -q backend/app scripts` | PASS |
| frontend `npm ci`, `npm run lint`, `npm run build`, `npm audit` | PASS;0 vulnerabilities |
| `.venv\Scripts\python.exe scripts/test_e2e.py` | PASS, full demo browser flow |
| `.venv\Scripts\python.exe scripts/smoke_real.py` | PASS, CPU pipeline smoke; not accuracy |
| Real panoramic E2E through reviewed webapp-testing `with_server.py` helper | PASS,117093/120frames; real API/frontend/worker/auto person |
| `.venv\Scripts\python.exe scripts/test_e2e.py --video test-artifacts/football/clips/steady/clip.avi` | PASS,200frames; auto preserves pose, moving-camera veto |
| Actual `--production` harness plus publisher scorers on steady/zoom/blur | PASS; raw/tracked TP/FP/FN exactly match phase2 |

Panoramic browser flow covered player/scout accounts, profile/save/refresh, upload202/queue/gallery/selection, report/path/heatmap/preview/refresh, search/detail and guards. ID1 had120observed frames/40saved samples; physical metrics were null without calibration. It explicitly checked that enabled calibration without stationary confirmation blocks submission, then ran without calibration. Legacy E2E supplied synthetic corners/confirmation but detected camera motion still vetoed physical metrics. Both happy paths had no console/page/HTTP/image errors, worker crash or stuck job. Desktop/mobile screenshots were inspected, with overflow assertions at1440/768/390px. Full local logs/screenshots remain ignored under `test-artifacts/small-player` and `test-artifacts/football/app-e2e`.

Final automatic-policy old-clip raw /tracked TP,FP,FN: steady `1217,264,1650 /1202,265,1665`; zoom `53,571,387 /42,510,398`; blur `0,21,500 /0,6,500`. These are unchanged. New PR CI is recorded separately after its actual remote execution; this local section does not claim a remote result.

Remote small-player CI: evidence/implementation head `0d0b74be59a1816a97114b59ccdea86d284848b6`, [Actions run37039654120](https://github.com/alinur527/Scout.AI/actions/runs/37039654120): **backend, frontend and demo E2E all SUCCESS**. Final-head CI37039995800 also passed. [PR#3](https://github.com/alinur527/Scout.AI/pull/3) was subsequently verified and merged as `e423ae6dd4d8d046c58c17304fa0094100bd3151` for the continuity round above.

## First football phase (historical)

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
