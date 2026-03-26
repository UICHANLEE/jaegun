"""FastAPI 앱 진입점."""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles

from sqlmodel import Session

from jaegun.api import admin, announcements, board, events, plans
from jaegun.config import get_project_root, get_settings
from jaegun.db import engine, init_db, seed_if_empty

log = logging.getLogger(__name__)


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
            "board_posts": "/api/board/posts",
            "admin_ui": "/admin/",
            "admin_api": "/admin",
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

    app.include_router(admin.router)
    app.include_router(announcements.router, prefix="/api")
    app.include_router(board.router, prefix="/api")
    app.include_router(events.router, prefix="/api")
    app.include_router(plans.router, prefix="/api")

    project_root = get_project_root()
    static_community = project_root / "static" / "community"
    static_admin = project_root / "static" / "admin"
    admin_index = static_admin / "index.html"

    if static_community.is_dir() and not static_admin.is_dir():
        log.warning(
            "static/community 는 있으나 static/admin 이 없습니다. "
            "/admin UI 404 — 프로젝트 루트: %s (필요 시 JAEGUN_PROJECT_ROOT)",
            project_root,
        )

    @app.get("/admin", include_in_schema=False)
    def admin_ui_redirect() -> RedirectResponse:
        if not admin_index.is_file():
            raise HTTPException(
                status_code=404,
                detail="관리자 UI 없음: static/admin/index.html 이 프로젝트에 없습니다.",
            )
        return RedirectResponse(url="/admin/", status_code=307)

    @app.get("/admin/", include_in_schema=False)
    def admin_ui_index() -> FileResponse:
        if not admin_index.is_file():
            raise HTTPException(
                status_code=404,
                detail="관리자 UI 없음: static/admin/index.html 이 프로젝트에 없습니다.",
            )
        return FileResponse(admin_index, media_type="text/html; charset=utf-8")

    if static_community.is_dir():
        app.mount(
            "/community",
            StaticFiles(directory=str(static_community), html=True),
            name="community_ui",
        )
    if static_admin.is_dir():
        app.mount(
            "/admin",
            StaticFiles(directory=str(static_admin), html=False),
            name="admin_ui",
        )
    return app


app = create_app()


def run_dev() -> None:
    import uvicorn

    uvicorn.run("jaegun.main:app", host="127.0.0.1", port=8000, reload=True)
