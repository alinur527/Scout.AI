from pathlib import Path
from uuid import uuid4
import time

from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, UploadFile
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse, Response
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import defer
from starlette.concurrency import run_in_threadpool

from app.core.security import current_user, passwords, player_user, scout_user, session, token_for
from app.models.entities import AnalysisJob, PlayerProfile, User
from app.schemas.contracts import Login, ProfileUpdate, Register, RunAnalysis, Selection
from app.services.video import inspect_video

router = APIRouter()


def public_user(user):
    return {"id": user.id, "username": user.username, "role": user.role}


def public_profile(profile):
    if profile is None:
        return None
    return {key: getattr(profile, key) for key in ("user_id", "full_name", "position", "age", "team", "bio", "scout_visible")}


def public_job(job):
    return {
        key: getattr(job, key)
        for key in (
            "id",
            "status",
            "stage",
            "progress",
            "original_filename",
            "selected_player_id",
            "demo",
            "created_at",
            "started_at",
            "completed_at",
            "error",
            "video",
        )
    }


def owned_job(db, analysis_id, user):
    job = db.get(AnalysisJob, analysis_id)
    if job is None or job.user_id != user.id:
        raise HTTPException(404, "Analysis not found")
    return job


@router.get("/health")
def health(request: Request):
    settings = request.app.state.settings
    heartbeat = settings.upload_dir / ".worker-heartbeat"
    age = time.time() - heartbeat.stat().st_mtime if heartbeat.exists() else None
    return {
        "status": "ok",
        "demo_mode": settings.demo_mode,
        "worker_online": age is not None and age < 120,
        "max_upload_mb": settings.max_upload_mb,
        "max_video_seconds": settings.max_video_seconds,
    }


@router.post("/auth/register", status_code=201)
def register(data: Register, db=Depends(session)):
    if data.role == "admin":
        raise HTTPException(403, "Administrator accounts cannot be self-registered")
    user = User(username=data.username, password_hash=passwords.hash(data.password), role=data.role)
    db.add(user)
    try:
        db.flush()
        if user.role == "player":
            db.add(PlayerProfile(user_id=user.id))
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Username is already registered") from None
    return public_user(user)


@router.post("/auth/login")
def login(data: Login, request: Request, db=Depends(session)):
    user = db.scalar(select(User).where(User.username == data.username))
    if user is None or not passwords.verify(data.password, user.password_hash):
        raise HTTPException(401, "Invalid username or password", headers={"WWW-Authenticate": "Bearer"})
    return {
        "access_token": token_for(user, request.app.state.settings),
        "token_type": "bearer",
        "user": public_user(user),
    }


@router.get("/profile/me")
def me(user=Depends(current_user), db=Depends(session)):
    return {"user": public_user(user), "profile": public_profile(db.get(PlayerProfile, user.id))}


@router.put("/profile/me")
def update_profile(data: ProfileUpdate, user=Depends(player_user), db=Depends(session)):
    profile = db.get(PlayerProfile, user.id)
    for key, value in data.model_dump().items():
        setattr(profile, key, value)
    db.commit()
    return public_profile(profile)


@router.get("/analyses")
def analyses(offset: int = Query(default=0, ge=0), limit: int = Query(default=20, ge=1, le=100), user=Depends(player_user), db=Depends(session)):
    jobs = db.scalars(
        select(AnalysisJob)
        .options(defer(AnalysisJob.tracks), defer(AnalysisJob.gallery), defer(AnalysisJob.result))
        .where(AnalysisJob.user_id == user.id)
        .order_by(AnalysisJob.created_at.desc(), AnalysisJob.id.desc())
        .offset(offset)
        .limit(limit)
    )
    return [public_job(job) for job in jobs]


@router.post("/analyses", status_code=202)
async def upload(
    request: Request, video: UploadFile = File(...), user=Depends(player_user), db=Depends(session)
):
    settings = request.app.state.settings
    original = (video.filename or "").replace("\\", "/").split("/")[-1][:255]
    extension = Path(original).suffix.lower()
    allowed = {
        ".mp4": {"video/mp4"},
        ".mov": {"video/quicktime", "video/mp4"},
        ".avi": {"video/x-msvideo", "video/avi", "video/msvideo", "video/vnd.avi"},
    }
    if extension not in allowed or video.content_type not in allowed[extension]:
        await video.close()
        raise HTTPException(415, "Use MP4, MOV or AVI with the matching video MIME type")
    filename = f"{uuid4()}{extension}"
    target = settings.upload_dir / filename
    size = 0
    try:
        with target.open("xb") as handle:
            while chunk := await video.read(1024 * 1024):
                size += len(chunk)
                if size > settings.max_upload_mb * 1024 * 1024:
                    raise HTTPException(413, f"Video exceeds {settings.max_upload_mb} MB")
                await run_in_threadpool(handle.write, chunk)
        try:
            metadata = await run_in_threadpool(inspect_video, target, settings)
        except ValueError as error:
            raise HTTPException(422, str(error)) from error
        job = AnalysisJob(
            user_id=user.id,
            original_filename=original,
            stored_filename=filename,
            demo=settings.demo_mode,
            video=metadata,
        )
        db.add(job)
        db.commit()
        db.refresh(job)
        return public_job(job)
    except BaseException:
        target.unlink(missing_ok=True)
        raise
    finally:
        await video.close()


@router.get("/demo/sample")
def demo_sample(request: Request, user=Depends(player_user)):
    if not request.app.state.settings.demo_mode:
        raise HTTPException(404, "Synthetic sample is available only in DEMO mode")
    from app.services.demo_sample import sample_bytes

    return Response(sample_bytes(), media_type="video/x-msvideo", headers={"Content-Disposition": 'attachment; filename="synthetic-demo.avi"'})


@router.get("/analyses/{analysis_id}")
@router.get("/analyses/{analysis_id}/status")
def analysis(analysis_id: str, user=Depends(player_user), db=Depends(session)):
    return public_job(owned_job(db, analysis_id, user))


@router.get("/analyses/{analysis_id}/players")
def gallery(analysis_id: str, user=Depends(player_user), db=Depends(session)):
    job = owned_job(db, analysis_id, user)
    return {"players": job.gallery, "preview": job.tracks.get("preview"), "video": job.video}


@router.patch("/analyses/{analysis_id}/player")
def select_player(analysis_id: str, data: Selection, user=Depends(player_user), db=Depends(session)):
    job = owned_job(db, analysis_id, user)
    if job.stage != "awaiting_selection" or job.status != "processing":
        raise HTTPException(409, "Player selection is not available at this stage")
    if data.player_id not in [p["id"] for p in job.gallery]:
        raise HTTPException(422, "Choose a player from this analysis")
    job.selected_player_id = data.player_id
    db.commit()
    return public_job(job)


@router.post("/analyses/{analysis_id}/run", status_code=202)
def run(analysis_id: str, data: RunAnalysis, user=Depends(player_user), db=Depends(session)):
    job = owned_job(db, analysis_id, user)
    if job.stage != "awaiting_selection" or job.status != "processing" or job.selected_player_id is None:
        raise HTTPException(409, "Wait for detection and select your player first")
    calibration = data.calibration.model_dump() if data.calibration else None
    if calibration:
        from app.cv.calibration import FieldTransformer

        try:
            FieldTransformer(
                calibration["points"],
                calibration["field_length"],
                calibration["field_width"],
                frame_size=(job.video["width"], job.video["height"]),
            )
        except ValueError as error:
            raise HTTPException(422, str(error)) from error
    changed = db.execute(
        update(AnalysisJob)
        .where(
            AnalysisJob.id == analysis_id,
            AnalysisJob.stage == "awaiting_selection",
            AnalysisJob.status == "processing",
        )
        .values(status="queued", stage="reporting", calibration=calibration)
    )
    if changed.rowcount != 1:
        db.rollback()
        raise HTTPException(409, "Analysis has already been queued")
    db.commit()
    db.refresh(job)
    return public_job(job)


@router.get("/analyses/{analysis_id}/result")
def result(analysis_id: str, user=Depends(player_user), db=Depends(session)):
    job = owned_job(db, analysis_id, user)
    if job.status != "completed":
        raise HTTPException(409, "Analysis is not completed")
    return job.result


def published_profile(db, player_id):
    profile = db.get(PlayerProfile, player_id)
    if profile is None or not profile.scout_visible:
        raise HTTPException(404, "Player not found or no longer shared")
    return profile


@router.get("/analyses/{analysis_id}/export")
def export_report(analysis_id: str, user=Depends(current_user), db=Depends(session)):
    job = db.get(AnalysisJob, analysis_id)
    if job is None:
        raise HTTPException(404, "Analysis not found")
    if job.user_id != user.id:
        if user.role not in ("scout", "admin"):
            raise HTTPException(404, "Analysis not found")
        published_profile(db, job.user_id)
    if job.status != "completed" or not job.result:
        raise HTTPException(409, "Analysis is not completed")
    # Explicit projection excludes source paths, private job state and binary media.
    fields = ("player_id", "demo", "calibrated", "calibration_provided", "physical_metrics_status", "physical_accuracy", "ground_position_method", "detector_profile", "camera_motion", "timestamp_basis", "coordinate_space", "metrics", "movement", "movement_segments", "heatmap", "observations", "duration_seconds", "frames_processed", "device", "rejected_segments", "warnings", "tracking_quality")
    payload = {
        "schema_version": "1.0",
        "analysis": {key: getattr(job, key) for key in ("id", "original_filename", "created_at", "completed_at", "demo")},
        "report": {key: job.result[key] for key in fields if key in job.result},
        "export_notice": "Anonymous track, not verified identity. Physical accuracy is not validated. DEMO metrics are synthetic. Sharing can be revoked for future requests; downloaded copies cannot be recalled.",
    }
    return JSONResponse(jsonable_encoder(payload), headers={"Content-Disposition": 'attachment; filename="scoutai-report.json"', "Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"})


def player_card(db, user):
    latest = db.scalar(
        select(AnalysisJob)
        .where(AnalysisJob.user_id == user.id, AnalysisJob.status == "completed")
        .order_by(AnalysisJob.completed_at.desc())
        .limit(1)
    )
    return {
        "user": public_user(user),
        "profile": public_profile(db.get(PlayerProfile, user.id)),
        "latest_analysis": {"id": latest.id, "result": latest.result} if latest else None,
    }


@router.get("/players")
def players(q: str = "", offset: int = 0, user=Depends(scout_user), db=Depends(session)):
    statement = (
        select(User).join(PlayerProfile, PlayerProfile.user_id == User.id).where(User.role == "player", PlayerProfile.scout_visible.is_(True))
    )
    if q:
        pattern = "%" + q[:100].replace("%", "\\%").replace("_", "\\_") + "%"
        statement = statement.where(
            User.username.ilike(pattern, escape="\\") | PlayerProfile.full_name.ilike(pattern, escape="\\")
        )
    return [
        player_card(db, player)
        for player in db.scalars(statement.order_by(User.id).offset(max(0, offset)).limit(50))
    ]


@router.get("/players/{player_id}")
def player_detail(player_id: int, user=Depends(scout_user), db=Depends(session)):
    published_profile(db, player_id)
    player = db.get(User, player_id)
    if player is None or player.role != "player":
        raise HTTPException(404, "Player not found")
    card = player_card(db, player)
    jobs = db.scalars(
        select(AnalysisJob)
        .where(AnalysisJob.user_id == player_id, AnalysisJob.status == "completed")
        .order_by(AnalysisJob.completed_at.desc())
        .limit(10)
    )
    card["analyses"] = [
        {"id": job.id, "completed_at": job.completed_at, "result": job.result} for job in jobs
    ]
    return card
