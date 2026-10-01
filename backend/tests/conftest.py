import secrets
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
from make_demo_video import make_video


@pytest.fixture
def setup(tmp_path):
    settings = Settings(
        _env_file=None,
        database_url=f"sqlite:///{tmp_path / 'test.db'}",
        jwt_secret_key=secrets.token_urlsafe(48),
        upload_dir=tmp_path / "uploads",
        SCOUTAI_DEMO_MODE=True,
        max_upload_mb=1,
    )
    app = create_app(settings)
    with TestClient(app) as client:
        yield client, app, settings


@pytest.fixture
def video(tmp_path):
    return make_video(tmp_path / "match.avi").read_bytes()


def account(client, username="player_one", role="player"):
    payload = {"username": username, "password": "Test-password-2026", "role": role}
    assert client.post("/auth/register", json=payload).status_code == 201
    response = client.post("/auth/login", json={key: payload[key] for key in ("username", "password")})
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


@pytest.fixture
def auth(setup):
    return account(setup[0])
