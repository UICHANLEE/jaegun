"""FastAPI 앱 진입점."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from sqlmodel import Session

from jaegun.api import announcements, events
from jaegun.config import get_settings
from jaegun.db import engine, init_db, seed_if_empty


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    init_db()
    with Session(engine) as session:
        seed_if_empty(session)
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name, lifespan=lifespan)

    origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
    if origins == ["*"] or not origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=False,
            allow_methods=["*"],
            allow_headers=["*"],
        )
    else:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    @app.get("/")
    def root() -> dict[str, str]:
        return {
            "service": "Jaegun API",
            "docs": "/docs",
            "health": "/health",
            "announcements": "/api/announcements",
            "events": "/api/events",
        }

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    app.include_router(announcements.router, prefix="/api")
    app.include_router(events.router, prefix="/api")
    return app


app = create_app()


def run_dev() -> None:
    import uvicorn

    uvicorn.run("jaegun.main:app", host="127.0.0.1", port=8000, reload=True)
