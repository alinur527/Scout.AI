from pathlib import Path
import json
import sqlite3
import os
import time
import shutil

import pytest
from sqlalchemy import text

from app.db.migrate import HEAD, upgrade
from app.db.session import create_database
from app.models.entities import AnalysisJob
from app.worker import cleanup, process_next, recover
from conftest import account
from test_api import upload


def complete(client, app, settings, auth, video):
    jid = upload(client, auth, video).json()["id"]
    process_next(app.state.sessions, settings)
    client.patch(f"/analyses/{jid}/player", headers=auth, json={"player_id": 1})
    client.post(f"/analyses/{jid}/run", headers=auth, json={})
    process_next(app.state.sessions, settings)
    return jid


def test_publication_revocation_export_and_no_private_enumeration(setup, auth, video):
    client, app, settings = setup
    jid = complete(client, app, settings, auth, video)
    other = account(client, "private_other")
    scout = account(client, "privacy_scout", "scout")
    profile = client.get("/profile/me", headers=auth).json()["profile"]
    uid = profile.pop("user_id")
    profile["full_name"] = "Synthetic Release Player"
    for path in (f"/players/{uid}", f"/analyses/{jid}/export"):
        assert client.get(path).status_code == 401
        assert client.get(path, headers=scout).status_code == 404
    assert client.get(f"/analyses/{jid}/export", headers=other).status_code == 404
    assert client.get("/players?q=player_one", headers=scout).json() == []
    owner_export = client.get(f"/analyses/{jid}/export", headers=auth)
    assert owner_export.status_code == 200
    assert owner_export.headers["cache-control"] == "no-store"
    assert "attachment" in owner_export.headers["content-disposition"]
    payload = owner_export.json()
    assert payload["report"]["demo"] is True and payload["report"]["warnings"]
    assert "annotated_preview" not in payload["report"]
    assert "stored_filename" not in owner_export.text and "password_hash" not in owner_export.text
    profile["scout_visible"] = True
    assert client.put("/profile/me", headers=auth, json=profile).status_code == 200
    assert len(client.get("/players", headers=scout).json()) == 1
    assert client.get(f"/players/{uid}", headers=scout).status_code == 200
    assert client.get(f"/analyses/{jid}/export", headers=scout).json() == payload
    # Publication never grants access to raw job/gallery data or another private user.
    assert client.get(f"/analyses/{jid}/players", headers=scout).status_code == 403
    assert client.get(f"/players/{uid + 1}", headers=scout).status_code == 404
    profile["scout_visible"] = False
    client.put("/profile/me", headers=auth, json=profile)
    assert client.get("/players", headers=scout).json() == []
    assert client.get(f"/players/{uid}", headers=scout).status_code == 404
    assert client.get(f"/analyses/{jid}/export", headers=scout).status_code == 404
    assert client.get(f"/analyses/{jid}/export", headers=auth).status_code == 200


def test_export_preserves_null_and_history_pagination(setup, auth, video):
    client, app, settings = setup
    ids = [complete(client, app, settings, auth, video) for _ in range(3)]
    with app.state.sessions() as db:
        job = db.get(AnalysisJob, ids[0])
        job.result = {**job.result, "demo": False, "metrics": {"total_distance_m": None, "top_speed_kmh": None, "sprint_count": None}, "internal_path": "PRIVATE-DO-NOT-EXPORT"}
        db.commit()
    payload = client.get(f"/analyses/{ids[0]}/export", headers=auth).json()
    assert payload["report"]["metrics"]["total_distance_m"] is None
    assert "internal_path" not in payload["report"]
    first = client.get("/analyses?limit=2", headers=auth).json()
    second = client.get("/analyses?limit=2&offset=2", headers=auth).json()
    assert len(first) == 2 and len(second) == 1
    assert {j["id"] for j in first + second} == set(ids)
    assert client.get("/analyses?limit=101", headers=auth).status_code == 422
    assert client.get("/analyses?offset=-1", headers=auth).status_code == 422


def test_sample_is_authenticated_player_only_and_demo_only(setup, auth):
    client, _, settings = setup
    assert client.get("/demo/sample").status_code == 401
    scout = account(client, "sample_scout", "scout")
    assert client.get("/demo/sample", headers=scout).status_code == 403
    response = client.get("/demo/sample", headers=auth)
    assert response.status_code == 200 and response.content[:4] == b"RIFF"
    settings.demo_mode = False
    assert client.get("/demo/sample", headers=auth).status_code == 404


@pytest.mark.parametrize("failure", [False, True])
def test_cleanup_failure_cannot_lose_job_state(setup, auth, video, monkeypatch, failure):
    client, app, settings = setup
    jid = upload(client, auth, video).json()["id"]
    original = Path.unlink
    def denied(path, *args, **kwargs):
        if path.suffix == ".avi":
            raise PermissionError("isolated simulated file lock")
        return original(path, *args, **kwargs)
    monkeypatch.setattr(Path, "unlink", denied)
    if failure:
        def broken(*args):
            raise ValueError("private/internal/path and credentials must not be public")
        monkeypatch.setattr("app.worker.detect", broken)
    assert process_next(app.state.sessions, settings)
    state = client.get(f"/analyses/{jid}", headers=auth).json()
    assert state["status"] == ("failed" if failure else "processing")
    assert "private/internal" not in (state["error"] or "")
    if not failure:
        assert state["stage"] == "awaiting_selection"
    with app.state.sessions() as db:
        job = db.get(AnalysisJob, jid)
        job.status, job.stage = "processing", "detection"
        db.commit()
    recover(app.state.sessions, settings)
    assert client.get(f"/analyses/{jid}", headers=auth).json()["status"] == "failed"


def test_fresh_migration_repeat_and_backup_restore(setup, auth, tmp_path):
    _, app, settings = setup
    with app.state.sessions() as db:
        assert db.scalar(text("SELECT version_num FROM alembic_version")) == HEAD
    engine, _ = create_database(settings)
    upgrade(engine)
    engine.dispose()
    source = Path(settings.database_url.removeprefix("sqlite:///"))
    backup = tmp_path / "isolated-backup.db"
    with sqlite3.connect(source) as original, sqlite3.connect(backup) as destination:
        original.backup(destination)
    with sqlite3.connect(backup) as restored:
        assert restored.execute("SELECT count(*) FROM users").fetchone() == (1,)
        assert restored.execute("SELECT scout_visible FROM player_profiles").fetchone() == (0,)
    restored_path = tmp_path / "restored.db"
    shutil.copy2(backup, restored_path)
    restored_settings = settings.model_copy(update={"database_url": f"sqlite:///{restored_path}"})
    restored_engine, restored_sessions = create_database(restored_settings)
    with restored_sessions() as db:
        assert db.scalar(text("SELECT username FROM users")) == "player_one"
        assert db.scalar(text("SELECT version_num FROM alembic_version")) == HEAD
    restored_engine.dispose()


def test_locked_orphan_cannot_stop_worker_cleanup(setup, monkeypatch):
    _, app, settings = setup
    orphan = settings.upload_dir / "old-orphan.avi"
    orphan.write_bytes(b"isolated test")
    old = time.time() - 90000
    os.utime(orphan, (old, old))
    original = Path.unlink
    def denied(path, *args, **kwargs):
        if path == orphan:
            raise PermissionError("isolated simulated file lock")
        return original(path, *args, **kwargs)
    monkeypatch.setattr(Path, "unlink", denied)
    cleanup(app.state.sessions, settings)
    assert orphan.exists()


def test_upgrade_original_unversioned_schema_preserves_data(setup, tmp_path):
    settings = setup[2].model_copy(update={"database_url": f"sqlite:///{tmp_path / 'legacy.db'}"})
    path = tmp_path / "legacy.db"
    with sqlite3.connect(path) as old:
        old.executescript((Path(__file__).parent / "fixtures/legacy-schema.sql").read_text())
        old.execute("INSERT INTO users VALUES (1, 'legacy_player', 'preserved-argon-hash', 'player', '2026-01-01')")
        old.execute("INSERT INTO player_profiles VALUES (1, 'Legacy fixture', 'Forward', 22, 'Fixture team', 'Keep this biography')")
        report = json.dumps({"demo": False, "metrics": {"total_distance_m": None}, "warnings": ["Physical accuracy not validated"]})
        old.execute("INSERT INTO analysis_jobs (id,user_id,status,stage,progress,original_filename,stored_filename,demo,created_at,video,gallery,tracks,result) VALUES ('legacy-job',1,'completed','done',100,'test.avi','server.avi',0,'2026-01-01','{}','[]','{}',?)", (report,))
        users = old.execute("SELECT * FROM users").fetchall()
        jobs = old.execute("SELECT * FROM analysis_jobs").fetchall()
    engine, _ = create_database(settings)
    upgrade(engine)
    engine.dispose()
    with sqlite3.connect(path) as current:
        assert current.execute("SELECT * FROM users").fetchall() == users
        assert current.execute("SELECT * FROM analysis_jobs").fetchall() == jobs
        assert current.execute("SELECT scout_visible, bio FROM player_profiles").fetchone() == (0, "Keep this biography")
        assert current.execute("SELECT version_num FROM alembic_version").fetchone() == (HEAD,)


def test_unknown_database_schema_is_not_silently_adopted(setup, tmp_path):
    path = tmp_path / "unknown.db"
    with sqlite3.connect(path) as db:
        db.execute("CREATE TABLE unrelated (value TEXT)")
        db.execute("INSERT INTO unrelated VALUES ('preserve')")
    settings = setup[2].model_copy(update={"database_url": f"sqlite:///{path}"})
    with pytest.raises(RuntimeError, match="Unrecognized legacy"):
        create_database(settings)
    with sqlite3.connect(path) as db:
        assert db.execute("SELECT value FROM unrelated").fetchone() == ("preserve",)


@pytest.mark.parametrize("constraint", ["unique", "foreign"])
def test_legacy_schema_missing_access_constraints_is_rejected(setup, tmp_path, constraint):
    path = tmp_path / "unsupported.db"
    schema = (Path(__file__).parent / "fixtures/legacy-schema.sql").read_text()
    if constraint == "unique":
        schema = schema.replace("CREATE UNIQUE INDEX ix_users_username ON users (username);", "")
    else:
        schema = schema.replace(",\n\tFOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE", "")
    with sqlite3.connect(path) as db:
        db.executescript(schema)
    settings = setup[2].model_copy(update={"database_url": f"sqlite:///{path}"})
    with pytest.raises(RuntimeError, match="Legacy"):
        create_database(settings)
    with sqlite3.connect(path) as db:
        assert len(db.execute("PRAGMA table_info(player_profiles)").fetchall()) == 6
