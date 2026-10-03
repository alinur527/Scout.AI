# Local operations

Verified v1 profile: Windows PowerShell native setup, SQLite, one worker, built frontend; Linux containers through Docker Desktop for DEMO. Public hosting, live PostgreSQL and CUDA are unverified. See [Quick Start](../README.md) for exact initial commands.

## Native lifecycle

Run scripts from any current directory using their path. They resolve the checkout root and start API/worker with `backend/` as their working directory.

| Command | Behavior |
|---|---|
| `scripts/setup.ps1` | Python 3.12/Node 22.12+ check; create venv if missing; install dependencies; preserve existing `.env`; build UI; migrate; doctor |
| `scripts/start.ps1` | Check ports 8000/5173 and worker lock; start API → worker → Vite production preview; wait for readiness; roll back its children if startup fails |
| `scripts/doctor.ps1` | Validate configuration without displaying secrets, packages, writable storage, ports, frontend build, and REAL dependencies/weights when applicable |
| `scripts/stop.ps1` | Stop only recorded processes with matching PID, creation time, command and checkout; preserve configuration/database/uploads |

Use `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\start.ps1` (or the other script name). This changes execution policy only for that invocation. No administrator shell or global policy change is required.

Runtime identities and per-run logs live under ignored `.runtime/`. Never commit that directory. A stale PID record is not authority to kill a process. Occupied ports are reported; identify their owner yourself. If a managed component exited, use stop then start. Do not run setup while services are active: stop first so dependency replacement is deterministic.

The browser uses the built frontend. After source or build-time API URL changes, run `npm run build` in `frontend/`, then restart. Native preview is a local demonstration server. Compose serves the same production assets with Nginx.

The v1.0.0 UI offers its complete corresponding source and public license/notices. For a modified deployment, publish the source of the actual running version, update `frontend/src/release.js` and the root NOTICE, then build. Keep that source freely available to users, together with build/run instructions and all applicable upstream notices. Do not substitute a moving or unrelated source version. Models and independent dataset/image assets retain their original terms; see [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).

## Configuration

`backend/.env` is created once with an independent random signing secret. API and worker read the same configuration; process environment overrides the file. Do not print or commit `.env`. Changing the signing secret invalidates existing sessions. Setup never silently switches an existing REAL environment to DEMO.

| Setting | Default / purpose |
|---|---|
| `DATABASE_URL` | `sqlite:///./data/scoutai.db`; relative to `backend/` |
| `UPLOAD_DIR` | `./data/uploads`; same directory for API and one worker |
| `JWT_SECRET_KEY` | Required, at least 32 characters; no public fallback |
| `JWT_ALGORITHM` | HS256 only |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | 120; no refresh-token service |
| `CORS_ORIGINS` | Explicit JSON array for localhost/127.0.0.1:5173; no wildcard |
| `SCOUTAI_DEMO_MODE` | setup sets true; code defaults false; legacy `DEMO_MODE` alias accepted |
| `MODEL_WEIGHTS` | `./weights/yolo11n-pose.pt` |
| `PERSON_MODEL_WEIGHTS` | `./weights/yolo11n.pt` |
| `CV_DETECTOR_POLICY` | `auto`: person for width ≥1920 and aspect ≥3, configured base otherwise; explicit `pose`/`person` also supported |
| `MAX_UPLOAD_MB` | 200; streaming and total multipart request limits |
| `MAX_VIDEO_SECONDS` / `MAX_VIDEO_FRAMES` | 1800 / 54000; other decoder/resolution/FPS limits also apply |
| `JOB_RETENTION_DAYS` | 7; expire unfinished jobs and clear old gallery/raw track data; completed report retained |
| `VITE_API_BASE_URL` | frontend build-time setting; default `http://localhost:8000`; Compose builds `/api` |

Use trusted local model weights. Downloads are explicit commands in the README. Failed REAL jobs remain failed; mode is captured at upload and is never retroactively relabelled.

## Database upgrades and backup/restore

Alembic revisions are `0001_legacy` and `0002_privacy`. Fresh databases are created through those migrations. Adoption of the previous unversioned schema checks tables, columns, primary keys, unique usernames and ownership foreign keys. Unknown layouts fail without deleting existing records. Existing profiles become private because no historical consent was recorded. SQLite migration uses a file lock; API readiness requires the current revision. Worker requires an already migrated database.

Stop services and make a backup before updating an existing installation. From a configured candidate checkout:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\stop.ps1
.\.venv\Scripts\python.exe scripts/backup_sqlite.py .\scoutai-before-upgrade.db
```

This uses SQLite's backup API (including committed WAL data), performs `integrity_check`, and refuses an existing destination. The backup contains private user data and password hashes; keep it outside Git/release attachments with appropriate local access restrictions. Preserve the matching private configuration separately. Copying only an active SQLite main file is not a reliable backup.

After updating source/dependencies, setup applies the migration. It can also be run explicitly:

```powershell
Push-Location backend
..\.venv\Scripts\python.exe -m app.db.migrate
Pop-Location
```

Migrations are repeatable. A failure is a reason to inspect the schema/backup, not delete the real database. Destructive downgrade is disabled.

Restore into a **new** filename with services stopped, keeping the current database intact:

```powershell
if (Test-Path backend/data/restored.db) { throw 'Choose a new restore destination.' }
Copy-Item -LiteralPath .\scoutai-before-upgrade.db -Destination backend/data/restored.db
notepad backend/.env
```

Set `DATABASE_URL=sqlite:///./data/restored.db`, retain the intended upload directory/signing key, then migrate, doctor and start. Roll back application code only together with a compatible pre-upgrade backup. Isolated tests verify fresh creation, legacy-data preservation, repeat upgrade and restored-backup opening; no real user database was erased for validation. PostgreSQL migration compatibility has not been executed against a live server.

## Worker persistence and privacy

- Queued jobs survive restart. An interrupted active detection/report stage becomes `failed` with an actionable re-upload message. Waiting-for-selection jobs remain selectable; completed reports remain available.
- Source videos are deleted after detection or failure; the DB retains the gallery/preview/observations needed for selection/reporting. A locked source or stale orphan logs a cleanup failure and is retried later; it must not discard the job state or prevent worker startup.
- One worker owns `.worker.lock` in the shared upload directory. Do not run workers against the same DB with different upload roots or across hosts.
- New and upgraded profiles are private. Publication applies to all completed reports on that profile and to search/list/detail/export. Revocation denies subsequent server requests; an open scout page clears denied data on its next poll (10 seconds) or focus. Printed/downloaded copies remain outside server control.
- Argon2 hashes, expiry-checked JWTs, server role/owner/consent checks and upload validation are tested. They do not supply an internet perimeter. This release is local; no public deployment is claimed.

## Compose lifecycle

`scripts/configure_local.py --docker` creates ignored `.env.docker` with a separate signing key; it preserves an existing file. `docker compose up --build -d --wait` starts API and exactly one worker sharing `/data` on the `scoutai-data` named volume. Nginx publishes only `127.0.0.1:8080` and proxies `/api`; the API has no host port. Deep frontend links fall back to `index.html`.

```powershell
docker compose ps
docker compose logs --tail 80 api worker frontend
docker compose down
```

Down retains the named volume. Do not use `down --volumes` as a troubleshooting shortcut. Native and Compose are separate local databases/secrets; sharing is not automatic. The verified container profile is DEMO only. Build context excludes secrets, local data, raw videos, model weights and test artifacts; runtime dependency notices remain installed.

## Troubleshooting

| Symptom | Action |
|---|---|
| Port occupied | Stop its actual owner; scripts deliberately do not kill by port |
| Worker offline | Inspect the latest `.runtime/*/worker.log` or Compose worker logs; check shared DB/upload root and one-worker lock |
| REAL weights/dependencies missing | Follow the explicit CPU setup; doctor checks configured policy requirements |
| No trackable people | Use a clearer/longer short clip; the job fails rather than fabricating a result |
| Session expired | Sign in again; saved jobs/results remain |
| Private player disappears | Owner revoked publication; scout detail/export now return 404 |
| Physical values unavailable | Read report warnings; moving cameras/unsupported calibration/timestamps intentionally keep nulls |
| Unknown legacy DB | Preserve it and its backup; inspect the schema difference instead of stamping/deleting |

Local release verification commands and limitations are in [VALIDATION.md](VALIDATION.md).
