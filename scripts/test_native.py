"""Windows release validation in a clean, isolated source copy; never use the user's DB."""

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import socket
import sqlite3
import subprocess
import sys
import tempfile
import time

from filelock import FileLock
import psutil

ROOT = Path(__file__).resolve().parents[1]


def main():
    if os.name != "nt":
        raise SystemExit("This validates the documented Windows PowerShell path")
    for port in (8000, 5173):
        with socket.socket() as probe:
            try:
                probe.bind(("127.0.0.1", port))
            except OSError:
                raise SystemExit(f"Port {port} belongs to another process; stop it before validation") from None
    evidence = ROOT / "test-artifacts/native" / f"{datetime.now(timezone.utc):%Y%m%dT%H%M%S%fZ}"
    evidence.mkdir(parents=True)
    clean = Path(tempfile.mkdtemp(prefix="scoutai-native-"))
    print(f"Clean source copy: {clean}\nEvidence: {evidence}", flush=True)
    paths = subprocess.check_output(["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"], cwd=ROOT).decode().split("\0")
    for name in filter(None, paths):
        source = ROOT / name
        if source.is_file():
            target = clean / name
            if not target.resolve().is_relative_to(clean):
                raise RuntimeError("Source path escaped isolated checkout")
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
    assert not any((clean / name).exists() for name in (".venv", "backend/.env", "backend/data", "frontend/node_modules", "backend/weights"))
    shell = shutil.which("powershell.exe")
    steps = []
    def command(label, args, *, expected=0, env=None, cwd=clean):
        with (evidence / f"{label}.log").open("w", encoding="utf-8") as log:
            result = subprocess.run(args, cwd=cwd, env=env, stdout=log, stderr=subprocess.STDOUT, creationflags=subprocess.CREATE_NO_WINDOW)
        if (result.returncode == 0) != (expected == 0):
            raise RuntimeError(f"{label}: unexpected exit {result.returncode}; inspect its evidence log")
        steps.append(label)
        print(f"PASS {label}", flush=True)
    def control(action, **kwargs):
        command(kwargs.pop("label", action), [shell, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(clean / f"scripts/{action}.ps1")], **kwargs)
    def records():
        with sqlite3.connect(clean / "backend/data/scoutai.db") as db:
            return {table: db.execute(f"SELECT * FROM {table} ORDER BY 1").fetchall() for table in ("users", "player_profiles", "analysis_jobs", "alembic_version")}
    try:
        control("setup", label="setup-clean")
        python = str(clean / ".venv/Scripts/python.exe")
        control("start")
        control("doctor")
        control("start", label="repeat-start-refused", expected=1)
        command("second-worker-refused", [python, "-m", "app.worker"], expected=1, cwd=clean / "backend")
        env = os.environ.copy()
        env.update(SCOUTAI_E2E_MANAGED_WORKER="true", SCOUTAI_E2E_URL="http://127.0.0.1:5173", SCOUTAI_E2E_API="http://127.0.0.1:8000", SCOUTAI_E2E_ARTIFACTS=str(evidence / "browser"))
        env.pop("SCOUTAI_E2E_VIDEO", None)
        command("browser", [python, str(clean / "scripts/e2e.py")], env=env)
        control("stop")
        control("stop", label="repeat-stop-safe")
        saved = records()
        env_hash = hashlib.sha256((clean / "backend/.env").read_bytes()).hexdigest()
        control("setup", label="setup-repeat")
        assert records() == saved
        assert hashlib.sha256((clean / "backend/.env").read_bytes()).hexdigest() == env_hash
        steps.append("repeat setup preserves all database rows and configuration bytes")
        # The foreign process is a test-owned fixture, outside the checkout's manager.
        foreign = subprocess.Popen([sys.executable, "-m", "http.server", "8000", "--bind", "127.0.0.1"], cwd=evidence, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=subprocess.CREATE_NO_WINDOW)
        try:
            deadline = time.monotonic() + 10
            while True:
                try:
                    with socket.create_connection(("127.0.0.1", 8000), timeout=.2):
                        break
                except OSError:
                    if time.monotonic() > deadline:
                        raise RuntimeError("Foreign-port fixture did not start") from None
                    time.sleep(.1)
            control("start", label="foreign-port-refused", expected=1)
            process = psutil.Process(foreign.pid)
            state = {"root": str(clean), "processes": [{"name": "unrelated-fixture", "pid": foreign.pid, "created": process.create_time() - 1, "command": process.cmdline()}]}
            (clean / ".runtime/processes.json").write_text(json.dumps(state), encoding="utf-8")
            control("stop", label="stale-pid-not-killed")
            assert foreign.poll() is None
        finally:
            foreign.terminate()
            foreign.wait(timeout=10)
        with FileLock(clean / "backend/data/uploads/.worker.lock", timeout=0):
            control("start", label="active-worker-lock-refused", expected=1)
        # Force only the final component to fail; API/worker must be rolled back.
        vite = (clean / "frontend/node_modules/vite/bin/vite.js").resolve()
        backup = vite.with_suffix(".test-backup")
        assert vite.is_relative_to(clean) and backup.is_relative_to(clean)
        vite.rename(backup)
        try:
            control("start", label="partial-startup-rolled-back", expected=1)
            assert not (clean / ".runtime/processes.json").exists()
            for port in (8000, 5173):
                with socket.socket() as probe:
                    probe.bind(("127.0.0.1", port))
        finally:
            backup.rename(vite)
        control("start", label="restart-persisted-data")
        assert records() == saved
        control("stop", label="final-stop")
        (evidence / "result.json").write_text(json.dumps({"status": "PASS", "steps": steps, "clean_source_copy": str(clean), "database_preserved": True, "configuration_preserved": True}, indent=2), encoding="utf-8")
        print("Native validation PASS; isolated files retained for inspection, no user DB touched.")
    finally:
        if (clean / ".venv/Scripts/python.exe").exists():
            control("stop", label="cleanup-managed-processes")


if __name__ == "__main__":
    main()
