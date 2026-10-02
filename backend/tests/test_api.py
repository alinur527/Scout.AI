from datetime import timedelta
import jwt
import pytest
from sqlalchemy import select

from app.models.entities import AnalysisJob, User, utcnow
from app.worker import cleanup, process_next, recover
from conftest import account


def upload(client, auth, video, name="match.avi", mime="video/x-msvideo"):
    return client.post("/analyses", headers=auth, files={"video": (name, video, mime)})


def test_health(setup):
    result = setup[0].get("/health")
    assert result.status_code == 200
    assert result.json()["demo_mode"] is True


def test_auth_profile(setup, auth):
    client, app, settings = setup
    assert client.get("/profile/me").status_code == 401
    assert (
        client.post(
            "/auth/register", json={"username": "player_one", "password": "Test-password-2026"}
        ).status_code
        == 409
    )
    assert (
        client.post("/auth/login", json={"username": "player_one", "password": "wrong-password"}).status_code
        == 401
    )
    assert (
        client.post(
            "/auth/register",
            json={"username": "admin_one", "password": "Test-password-2026", "role": "admin"},
        ).status_code
        == 403
    )
    assert (
        client.post(
            "/auth/register", json={"username": "bad_role", "password": "Test-password-2026", "role": "root"}
        ).status_code
        == 422
    )
    profile = {
        "full_name": "Test Player",
        "position": "Forward",
        "age": 22,
        "team": "Local FC",
        "bio": "Left foot",
    }
    assert client.put("/profile/me", headers=auth, json=profile).status_code == 200
    assert client.get("/profile/me", headers=auth).json()["profile"]["full_name"] == "Test Player"
    with app.state.sessions() as db:
        user = db.scalar(select(User))
        assert user.password_hash.startswith("$argon2id$")
    expired = jwt.encode(
        {"sub": "1", "iat": utcnow() - timedelta(hours=2), "exp": utcnow() - timedelta(hours=1)},
        settings.jwt_secret_key,
        algorithm="HS256",
    )
    assert client.get("/profile/me", headers={"Authorization": f"Bearer {expired}"}).status_code == 401
    assert client.get("/profile/me", headers={"Authorization": "Bearer invalid"}).status_code == 401


@pytest.mark.parametrize(
    "name,mime,data,expected",
    [
        ("bad.exe", "video/mp4", b"bad", 415),
        ("bad.mp4", "text/plain", b"bad", 415),
        ("bad.mp4", "video/mp4", b"bad", 422),
        ("empty.avi", "video/x-msvideo", b"", 422),
        ("large.mp4", "video/mp4", b"x" * (1024 * 1024 + 1), 413),
    ],
    ids=["extension", "mime", "invalid", "empty", "oversized"],
)
def test_upload_validation(setup, auth, name, mime, data, expected):
    assert upload(setup[0], auth, data, name, mime).status_code == expected
    assert list(setup[2].upload_dir.glob("*")) == []


def test_complete_flow_persistence_and_access(setup, auth, video):
    client, app, settings = setup
    response = upload(client, auth, video, "../../match.avi")
    assert response.status_code == 202
    job = response.json()
    jid = job["id"]
    assert job["status"] == "queued" and job["original_filename"] == "match.avi"
    assert "stored_filename" not in job
    assert client.get(f"/analyses/{jid}/result", headers=auth).status_code == 409
    assert process_next(app.state.sessions, settings)
    assert client.get(f"/analyses/{jid}/status", headers=auth).json()["stage"] == "awaiting_selection"
    assert list(settings.upload_dir.glob("*.avi")) == []
    gallery = client.get(f"/analyses/{jid}/players", headers=auth).json()
    assert len(gallery["players"]) == 2
    assert client.patch(f"/analyses/{jid}/player", headers=auth, json={"player_id": 999}).status_code == 422
    assert client.patch(f"/analyses/{jid}/player", headers=auth, json={"player_id": 1}).status_code == 200
    assert client.post(f"/analyses/{jid}/run", headers=auth, json={}).status_code == 202
    assert client.post(f"/analyses/{jid}/run", headers=auth, json={}).status_code == 409
    assert process_next(app.state.sessions, settings)
    result = client.get(f"/analyses/{jid}/result", headers=auth).json()
    assert result["demo"] and result["metrics"]["total_distance_m"] == 1250.5
    assert len(result["heatmap"]) == 12 and result["movement"]
    assert client.get(f"/analyses/{jid}", headers=auth).json()["progress"] == 100
    with app.state.sessions() as db:
        saved = db.get(AnalysisJob, jid)
        assert saved.status == "completed" and saved.result == result and saved.tracks == {}
    second = account(client, "player_two")
    for suffix in ("", "/status", "/players", "/result"):
        assert client.get(f"/analyses/{jid}{suffix}", headers=second).status_code == 404
    assert client.patch(f"/analyses/{jid}/player", headers=second, json={"player_id": 1}).status_code == 404
    assert client.get("/players", headers=auth).status_code == 403
    scout = account(client, "scout_one", "scout")
    assert upload(client, scout, video).status_code == 403
    assert client.get("/players", headers=scout).json() == []
    profile = client.get("/profile/me", headers=auth).json()["profile"]
    assert profile["scout_visible"] is False
    profile.pop("user_id")
    profile.update(full_name="Synthetic Test Player", scout_visible=True)
    assert client.put("/profile/me", headers=auth, json=profile).status_code == 200
    cards = client.get("/players", headers=scout).json()
    card = next(card for card in cards if card["user"]["username"] == "player_one")
    assert card["latest_analysis"]["result"]["demo"]
    assert client.get(f"/players/{card['user']['id']}", headers=scout).json()["analyses"]


def test_real_mode_missing_weights_fails_without_demo(setup, auth, video):
    client, app, settings = setup
    settings.demo_mode = False
    settings.model_weights = settings.upload_dir / "missing.pt"
    jid = upload(client, auth, video).json()["id"]
    process_next(app.state.sessions, settings)
    state = client.get(f"/analyses/{jid}", headers=auth).json()
    assert state["status"] == "failed" and not state["demo"]
    assert "weights are missing" in state["error"]
    assert not list(settings.upload_dir.glob("*.avi"))


def test_recovery_and_expiry(setup, auth, video):
    client, app, settings = setup
    jid = upload(client, auth, video).json()["id"]
    with app.state.sessions() as db:
        db.get(AnalysisJob, jid).status = "processing"
        db.commit()
    recover(app.state.sessions, settings)
    assert client.get(f"/analyses/{jid}", headers=auth).json()["status"] == "failed"
    jid2 = upload(client, auth, video).json()["id"]
    with app.state.sessions() as db:
        db.get(AnalysisJob, jid2).created_at = utcnow() - timedelta(days=9)
        db.commit()
    cleanup(app.state.sessions, settings)
    assert client.get(f"/analyses/{jid2}", headers=auth).json()["status"] == "failed"


def test_calibration_rejected(setup, auth, video):
    client, app, settings = setup
    jid = upload(client, auth, video).json()["id"]
    process_next(app.state.sessions, settings)
    client.patch(f"/analyses/{jid}/player", headers=auth, json={"player_id": 1})
    result = client.post(
        f"/analyses/{jid}/run",
        headers=auth,
        json={"calibration": {"points": [[0, 0]] * 4, "field_length": 40, "field_width": 20}},
    )
    assert result.status_code == 422


def test_request_size_limit_including_chunked(setup, auth):
    client = setup[0]
    assert (
        client.post("/analyses", headers={**auth, "Content-Length": "999999999"}, content=b"").status_code
        == 413
    )
    chunks = (b"x" * 400000 for _ in range(4))
    assert (
        client.post(
            "/analyses", headers={**auth, "Content-Type": "multipart/form-data; boundary=x"}, content=chunks
        ).status_code
        == 413
    )


def test_profile_role_and_search_empty(setup, auth):
    client = setup[0]
    assert client.get("/analyses", headers=auth).json() == []
    scout = account(client, "test_scout", "scout")
    assert (
        client.put(
            "/profile/me", headers=scout, json={"full_name": "Scout", "position": "Forward"}
        ).status_code
        == 403
    )
    assert client.get("/players?q=no_such_player", headers=scout).json() == []
    assert client.get("/players/999", headers=scout).status_code == 404


def test_standard_avi_mime(setup, auth, video):
    assert upload(setup[0], auth, video, mime="video/vnd.avi").status_code == 202
