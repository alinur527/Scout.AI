"""Actual CPU/CUDA YOLO smoke test. Uses bundled bus.jpg, not football accuracy data."""

import json
from pathlib import Path
import secrets
import sys
import tempfile

import cv2
import numpy as np
import torch
import ultralytics
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from app.core.config import Settings  # noqa: E402
from app.main import create_app  # noqa: E402
from app.worker import process_next  # noqa: E402
from app.models.entities import AnalysisJob  # noqa: E402
from app.services.inference import report  # noqa: E402


def main():
    artifacts = ROOT / "test-artifacts/real"
    artifacts.mkdir(parents=True, exist_ok=True)
    source = Path(ultralytics.__file__).parent / "assets/bus.jpg"
    frame = cv2.imread(str(source))
    if frame is None:
        raise RuntimeError(f"Bundled Ultralytics sample is missing: {source}")
    frame = cv2.resize(frame, (480, 640))
    video = artifacts / "people-smoke.avi"
    writer = cv2.VideoWriter(
        str(video), cv2.VideoWriter_fourcc(*"MJPG"), 12, (480, 640)
    )
    if not writer.isOpened():
        raise RuntimeError("Video writer failed")
    for index in range(24):
        shifted = cv2.warpAffine(
            frame, np.float32([[1, 0, index * 0.3], [0, 1, 0]]), (480, 640)
        )
        writer.write(shifted)
    writer.release()
    with tempfile.TemporaryDirectory(prefix="scoutai-real-") as temporary:
        settings = Settings(
            _env_file=None,
            jwt_secret_key=secrets.token_urlsafe(48),
            database_url=f"sqlite:///{Path(temporary).as_posix()}/smoke.db",
            upload_dir=Path(temporary) / "uploads",
            SCOUTAI_DEMO_MODE=False,
            model_weights=ROOT / "backend/weights/yolo11n-pose.pt",
        )
        app = create_app(settings)
        with TestClient(app) as client:
            credentials = {
                "username": "smoke_player",
                "password": secrets.token_urlsafe(20),
            }
            assert client.post("/auth/register", json=credentials).status_code == 201
            token = client.post("/auth/login", json=credentials).json()["access_token"]
            auth = {"Authorization": f"Bearer {token}"}
            response = client.post(
                "/analyses",
                headers=auth,
                files={"video": ("people.avi", video.read_bytes(), "video/x-msvideo")},
            )
            assert response.status_code == 202, response.text
            jid = response.json()["id"]
            assert process_next(app.state.sessions, settings)
            state = client.get(f"/analyses/{jid}", headers=auth).json()
            assert state["stage"] == "awaiting_selection", state
            gallery = client.get(f"/analyses/{jid}/players", headers=auth).json()[
                "players"
            ]
            assert gallery and gallery[0]["thumbnail"]
            tid = max(gallery, key=lambda entry: entry["observations"])["id"]
            # Exercise the inherited metric/radar algorithms on a deliberately artificial projection.
            # A bus image is not a measured football pitch; these values are never accuracy evidence.
            with app.state.sessions() as db:
                metric_fixture = db.get(AnalysisJob, jid)
                metric_fixture.selected_player_id = tid
                metric_fixture.calibration = {
                    "stationary_camera": True,
                    "points": [[0, 0], [479, 0], [479, 639], [0, 639]],
                    "field_length": 40,
                    "field_width": 20,
                }
                # Artificially authorize this isolated math/radar smoke, then roll back.
                # The shifted bus video itself is not evidence of a stationary camera.
                metric_fixture.tracks = dict(
                    metric_fixture.tracks,
                    camera_motion={"status": "no_motion_detected"},
                )
                calibrated = report(metric_fixture)
                assert calibrated["metrics"]["total_distance_m"] is not None
                assert calibrated["radar"] and calibrated["calibrated"]
                db.rollback()
            assert (
                client.patch(
                    f"/analyses/{jid}/player", headers=auth, json={"player_id": tid}
                ).status_code
                == 200
            )
            assert (
                client.post(f"/analyses/{jid}/run", headers=auth, json={}).status_code
                == 202
            )
            assert process_next(app.state.sessions, settings)
            result = client.get(f"/analyses/{jid}/result", headers=auth).json()
            assert result["demo"] is False and result["frames_processed"] == 24
            assert result["metrics"]["total_distance_m"] is None
            assert result["movement"] and result["annotated_preview"]
            assert (
                client.get(f"/analyses/{jid}", headers=auth).json()["status"]
                == "completed"
            )
            summary = {
                "status": "PASS",
                "fixture": "Ultralytics bundled bus.jpg shifted across 24 MJPG frames",
                "football_accuracy_test": False,
                "cuda_available": torch.cuda.is_available(),
                "device": result["device"],
                "frames_processed": result["frames_processed"],
                "players_found": len(gallery),
                "selected_track_observations": result["observations"],
                "calibrated": False,
                "completed": True,
                "metric_and_radar_code_smoke": "PASS on artificial projection; no accuracy claim",
            }
            (artifacts / "result.json").write_text(
                json.dumps(summary, indent=2), encoding="utf-8"
            )
            print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
