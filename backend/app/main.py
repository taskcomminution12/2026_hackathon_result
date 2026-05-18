"""FastAPI entrypoint."""
from __future__ import annotations

import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from .config import settings
from .db import init_db
from .routers import (announcements, assignments, courses, files,
                      kakao as kakao_router, me,
                      settings as settings_router, sync)
from .services import app_settings, scheduler, watcher

# ---------- 정적 파일 위치 ----------
HERE = Path(__file__).parent
if hasattr(sys, "_MEIPASS"):
    # PyInstaller 번들 — frontend/prototype 이 _MEIPASS 안에 packed
    PROTO_DIR = (Path(sys._MEIPASS) / "frontend" / "prototype").resolve()
else:
    PROTO_DIR = (HERE / "../../frontend/prototype").resolve()


# ---------- 라이프사이클 ----------
@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    app_settings.apply_to_settings()   # DB 저장된 설정을 settings 객체에 덮어씀
    scheduler.start(interval_minutes=30)
    watcher.start()
    try:
        yield
    finally:
        scheduler.stop()
        watcher.stop()


app = FastAPI(title="수원대 LMS Sync", version="0.1.0", lifespan=lifespan)

# 같은 호스트 SPA 지만 dev 편의를 위해 CORS 풀어둠
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------- API ----------
for router, tag in [
    (me.router,             "me"),
    (courses.router,        "courses"),
    (files.router,          "files"),
    (assignments.router,    "assignments"),
    (announcements.router,  "announcements"),
    (sync.router,           "sync"),
    (kakao_router.router,   "kakao"),
    (settings_router.router, "settings"),
]:
    app.include_router(router, prefix="/api", tags=[tag])


# ---------- 페이지 ----------
@app.get("/")
def root():
    return RedirectResponse("/dashboard")


@app.get("/dashboard")
def dashboard():
    return FileResponse(PROTO_DIR / "index.html")


@app.get("/course/{course_id}")
def course_page(course_id: int):  # noqa: ARG001  (URL 파라미터는 프론트에서 사용)
    return FileResponse(PROTO_DIR / "course.html")


@app.get("/settings")
def settings_page():
    return FileResponse(PROTO_DIR / "settings.html")


if PROTO_DIR.exists():
    app.mount("/static", StaticFiles(directory=PROTO_DIR), name="static")


def run_dev() -> None:
    """개발용 실행 — `python -m app.main`."""
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=True,
        reload_dirs=[str(HERE)],
    )


if __name__ == "__main__":
    run_dev()
