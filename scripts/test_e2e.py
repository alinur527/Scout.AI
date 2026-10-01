"""Portable server wrapper for the committed E2E script, without shell commands."""

import os
from pathlib import Path
import secrets
import shutil
import socket
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]


def stop_process(process):
    if process.poll() is None:
        if os.name == "nt":
            subprocess.run(
                ["taskkill", "/PID", str(process.pid), "/T", "/F"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
            )
        else:
            process.terminate()
        process.wait(timeout=15)


def ready(port):
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=0.5):
            return True
    except OSError:
        return False


def main():
    if any(ready(port) for port in (8000, 5173)):
        raise SystemExit("Ports 8000 and 5173 must be free for an isolated E2E test")
    with tempfile.TemporaryDirectory(prefix="scoutai-e2e-") as temporary:
        env = os.environ.copy()
        env.update(
            JWT_SECRET_KEY=secrets.token_urlsafe(48),
            SCOUTAI_DEMO_MODE="true",
            DATABASE_URL=f"sqlite:///{Path(temporary).as_posix()}/test.db",
            UPLOAD_DIR=f"{Path(temporary).as_posix()}/uploads",
            VITE_API_BASE_URL="http://127.0.0.1:8000",
        )
        servers = []
        artifacts = ROOT / "test-artifacts/e2e"
        artifacts.mkdir(parents=True, exist_ok=True)
        handles = []
        try:
            for name, args, cwd, port in [
                (
                    "api",
                    [
                        sys.executable,
                        "-m",
                        "uvicorn",
                        "app.main:create_app",
                        "--factory",
                        "--host",
                        "127.0.0.1",
                        "--port",
                        "8000",
                    ],
                    ROOT / "backend",
                    8000,
                ),
                (
                    "frontend",
                    [
                        shutil.which("node"),
                        "node_modules/vite/bin/vite.js",
                        "--host",
                        "127.0.0.1",
                        "--port",
                        "5173",
                        "--strictPort",
                    ],
                    ROOT / "frontend",
                    5173,
                ),
            ]:
                handle = (artifacts / f"{name}.log").open("w", encoding="utf-8")
                handles.append(handle)
                process = subprocess.Popen(
                    args, cwd=cwd, env=env, stdout=handle, stderr=subprocess.STDOUT
                )
                servers.append(process)
                deadline = time.monotonic() + 30
                while not ready(port):
                    if process.poll() is not None or time.monotonic() > deadline:
                        raise RuntimeError(
                            f"{name} did not start; see test-artifacts/e2e/{name}.log"
                        )
                    time.sleep(0.2)
            return subprocess.run(
                [sys.executable, str(ROOT / "scripts/e2e.py")], cwd=ROOT, env=env
            ).returncode
        finally:
            for process in reversed(servers):
                stop_process(process)
            for handle in handles:
                handle.close()


if __name__ == "__main__":
    raise SystemExit(main())
