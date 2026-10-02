"""Manage only this checkout's local API, single worker and built frontend."""

import argparse
from datetime import datetime, timezone
import importlib.metadata
import importlib.util
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from urllib.request import urlopen

from filelock import FileLock, Timeout
import psutil
from pydantic import ValidationError
from sqlalchemy.engine import make_url

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / ".runtime"
STATE = RUNTIME / "processes.json"
sys.path.insert(0, str(ROOT / "backend"))
from app.core.config import Settings  # noqa: E402


def settings():
    os.chdir(ROOT / "backend")
    try:
        return Settings()
    except ValidationError as error:
        fields = ", ".join(".".join(map(str, item["loc"])) for item in error.errors())
        raise RuntimeError(f"Invalid configuration fields: {fields}. Values are intentionally hidden.") from None


def occupied(port):
    with socket.socket() as check:
        try:
            check.bind(("127.0.0.1", port))
            return False
        except OSError:
            return True


def health():
    with urlopen("http://127.0.0.1:8000/health", timeout=2) as response:
        return json.load(response)


def doctor(require_free=False):
    if sys.version_info[:2] != (3, 12):
        raise RuntimeError("Use the Python 3.12 project virtual environment")
    node = shutil.which("node")
    if not node:
        raise RuntimeError("Node 22.12+ is required")
    version = subprocess.check_output([node, "--version"], text=True).strip()
    if tuple(map(int, version.lstrip("v").split(".")[:2])) < (22, 12):
        raise RuntimeError("Node 22.12+ is required")
    config = settings()
    url = make_url(config.database_url)
    folders = [config.upload_dir.resolve()]
    if url.drivername.startswith("sqlite") and url.database and url.database != ":memory:":
        folders.append(Path(url.database).resolve().parent)
    for folder in folders:
        folder.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryFile(dir=folder) as probe:
            probe.write(b"storage check")
    for package in ("fastapi", "sqlalchemy", "alembic", "opencv-python", "psutil"):
        print(f"{package}: {importlib.metadata.version(package)}")
    print(f"Python {sys.version.split()[0]}; Node {version}; mode {'DEMO (synthetic)' if config.demo_mode else 'REAL (local inference)'}")
    print(f"Database: {url.drivername}; media storage: {config.upload_dir.resolve()}")
    for port in (8000, 5173):
        busy = occupied(port)
        print(f"Port {port}: {'in use' if busy else 'available'}")
        if require_free and busy:
            raise RuntimeError(f"Port {port} is occupied. Stop its owner yourself; it was not killed.")
    if not (ROOT / "frontend/dist/index.html").is_file():
        raise RuntimeError("Built frontend is missing; run setup.ps1 or npm run build in frontend")
    if not config.demo_mode:
        for module in ("torch", "ultralytics", "supervision", "lap"):
            if importlib.util.find_spec(module) is None:
                raise RuntimeError("REAL dependencies are missing; follow the explicit CPU setup in README")
        weights = [] if config.cv_detector_policy == "person" else [config.model_weights]
        if config.cv_detector_policy in ("auto", "person"):
            weights.append(config.person_model_weights)
        if any(not path.is_file() for path in weights):
            raise RuntimeError("REAL model weights are missing; use the documented explicit download commands")
        print("REAL dependencies and configured weights found; this is not an accuracy check.")
    if not require_free and occupied(8000):
        try:
            print(f"API reachable; worker online: {health()['worker_online']}")
        except (OSError, ValueError, KeyError):
            print("Port8000 is in use but ScoutAI health was not confirmed.")
    return config


def owned(row):
    try:
        process = psutil.Process(row["pid"])
        if abs(process.create_time() - row["created"]) > .001 or process.cmdline() != row["command"]:
            return None
        if not any(str(ROOT).lower() in argument.lower() for argument in row["command"]):
            return None
        return process
    except (psutil.Error, KeyError, TypeError):
        return None


def write_state(rows):
    temporary = STATE.with_suffix(".tmp")
    temporary.write_text(json.dumps({"root": str(ROOT), "processes": rows}, indent=2), encoding="utf-8")
    temporary.replace(STATE)


def stop_rows(rows):
    for row in reversed(rows):
        process = owned(row)
        if process is None:
            print(f"Skipped stale or unverified process record: {row.get('name', 'unknown')}")
            continue
        children = process.children(recursive=True)
        for child in reversed(children):
            try:
                child.terminate()
            except psutil.NoSuchProcess:
                pass
        try:
            process.terminate()
        except psutil.NoSuchProcess:
            pass
        _, alive = psutil.wait_procs([process, *children], timeout=10)
        for remaining in alive:
            try:
                remaining.kill()
            except psutil.NoSuchProcess:
                pass
        psutil.wait_procs(alive, timeout=5)
        print(f"Stopped {row['name']}")


def load_rows():
    if not STATE.exists():
        return []
    state = json.loads(STATE.read_text(encoding="utf-8"))
    if state.get("root") != str(ROOT):
        raise RuntimeError("Runtime state belongs to another checkout; no process was stopped")
    return state["processes"]


def start():
    rows = load_rows()
    if any(owned(row) for row in rows):
        raise RuntimeError("This checkout is already running. Use scripts/stop.ps1 first.")
    config = doctor(require_free=True)
    with FileLock(config.upload_dir / ".worker.lock", timeout=0):
        pass
    log_dir = RUNTIME / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    log_dir.mkdir(parents=True)
    rows = []
    commands = [
        ("api", [sys.executable, "-m", "uvicorn", "app.main:create_app", "--factory", "--host", "127.0.0.1", "--port", "8000"], ROOT / "backend"),
        ("worker", [sys.executable, "-m", "app.worker"], ROOT / "backend"),
        ("frontend", [shutil.which("node"), str(ROOT / "frontend/node_modules/vite/bin/vite.js"), "preview", "--host", "127.0.0.1", "--port", "5173", "--strictPort"], ROOT / "frontend"),
    ]
    try:
        for name, command, cwd in commands:
            with (log_dir / f"{name}.log").open("w", encoding="utf-8") as log:
                child = subprocess.Popen(command, cwd=cwd, stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT, creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
            process = psutil.Process(child.pid)
            rows.append({"name": name, "pid": child.pid, "created": process.create_time(), "command": process.cmdline()})
            write_state(rows)
            deadline = time.monotonic() + 45
            while True:
                if child.poll() is not None:
                    raise RuntimeError(f"{name} exited during startup. See {log_dir / (name + '.log')}")
                try:
                    if name == "frontend":
                        with urlopen("http://127.0.0.1:5173", timeout=2) as response:
                            ready = response.status == 200
                    else:
                        data = health()
                        ready = data.get("status") == "ok"
                        if name == "worker":
                            heartbeat = config.upload_dir / ".worker-heartbeat"
                            ready = ready and data.get("worker_online") and heartbeat.exists() and heartbeat.stat().st_mtime >= rows[-1]["created"]
                    if ready:
                        break
                except (OSError, ValueError):
                    pass
                if time.monotonic() >= deadline:
                    raise RuntimeError(f"{name} readiness timed out. See {log_dir}")
                time.sleep(.25)
        print(f"ScoutAI ready: http://127.0.0.1:5173\nLogs: {log_dir}\nStop: scripts/stop.ps1")
    except BaseException:
        stop_rows(rows)
        STATE.unlink(missing_ok=True)
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("doctor", "start", "stop"))
    args = parser.parse_args()
    RUNTIME.mkdir(exist_ok=True)
    try:
        with FileLock(RUNTIME / "control.lock", timeout=1):
            if args.action == "doctor":
                doctor()
            elif args.action == "start":
                start()
            else:
                stop_rows(load_rows())
                STATE.unlink(missing_ok=True)
                print("Project-managed processes stopped; data retained.")
    except Timeout:
        raise SystemExit("Another project control operation or worker is active; no processes were stopped.") from None
    except (RuntimeError, OSError, ValueError) as error:
        raise SystemExit(str(error)) from None


if __name__ == "__main__":
    main()
