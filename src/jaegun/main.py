"""FastAPI 앱 진입점."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from fastapi.staticfiles import StaticFiles

from sqlmodel import Session

from jaegun.api import announcements, events, plans
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
            "ui": "/community/",
            "docs": "/docs",
            "health": "/health",
            "announcements": "/api/announcements",
            "events": "/api/events",
            "plans_annual": "/api/plans/annual",
            "plans_monthly": "/api/plans/monthly",
        }

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/favicon.ico", include_in_schema=False)
    def favicon() -> Response:
        svg = (
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32">'
            '<rect width="32" height="32" rx="7" fill="#0f766e"/>'
            '<text x="16" y="22" text-anchor="middle" fill="white" '
            'font-size="15" font-family="system-ui,sans-serif" font-weight="600">J</text>'
            "</svg>"
        )
        return Response(
            content=svg.encode("utf-8"),
            media_type="image/svg+xml",
        )

    app.include_router(announcements.router, prefix="/api")
    app.include_router(events.router, prefix="/api")
    app.include_router(plans.router, prefix="/api")

    static_dir = Path(__file__).resolve().parent.parent.parent / "static" / "community"
    if static_dir.is_dir():
        app.mount(
            "/community",
            StaticFiles(directory=str(static_dir), html=True),
            name="community_ui",
        )
    return app


app = create_app()


def run_dev() -> None:
    import uvicorn

    uvicorn.run("jaegun.main:app", host="127.0.0.1", port=8000, reload=True)
