from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.core.config import Settings
from app.core.limits import BodyLimitMiddleware
from app.db.session import create_database


def create_app(settings=None):
    @asynccontextmanager
    async def lifespan(app):
        app.state.settings = settings or Settings()
        app.state.settings.upload_dir.mkdir(parents=True, exist_ok=True)
        engine, app.state.sessions = create_database(app.state.settings)
        yield
        engine.dispose()

    app = FastAPI(title="ScoutAI", version="1.0.0", lifespan=lifespan)
    # Load configuration at startup; this deliberately fails when a JWT secret is absent.
    config = settings or Settings()
    app.add_middleware(BodyLimitMiddleware, max_bytes=config.max_upload_mb * 1024 * 1024 + 65536)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.cors_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST", "PUT", "PATCH"],
        allow_headers=["Authorization", "Content-Type"],
    )
    app.include_router(router)
    return app
