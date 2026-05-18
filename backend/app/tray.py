"""Windows 트레이 앱 — uvicorn 서버를 백그라운드로 띄우고 트레이 메뉴 제공.

실행:
  python -m app.tray
"""
from __future__ import annotations
import os
import sys
import threading
import time
import webbrowser

# PyInstaller windowed 빌드 (--noconsole) 에선 sys.stdout/stderr 가 None 이라
# uvicorn 의 로그 출력이 즉시 죽음. 더미 스트림으로 대체.
if sys.stdout is None:
    sys.stdout = open(os.devnull, "w")
if sys.stderr is None:
    sys.stderr = open(os.devnull, "w")

import httpx
import pystray
import uvicorn
from PIL import Image, ImageDraw, ImageFont

# 절대 import — PyInstaller 로 묶었을 때도 동작하도록
try:
    from app.config import settings
except ImportError:                                    # 개발 모드 (python -m app.tray)
    from .config import settings  # type: ignore


# ---------- 아이콘 (런타임 생성) ----------
def _make_icon(text: str = "SU", color: str = "#2563EB") -> Image.Image:
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    # 둥근 사각형
    d.rounded_rectangle([2, 2, 62, 62], radius=14, fill=color)
    # 텍스트 (시스템 기본 폰트)
    try:
        font = ImageFont.truetype("seguibl.ttf", 24)
    except Exception:
        font = ImageFont.load_default()
    bbox = d.textbbox((0, 0), text, font=font)
    w = bbox[2] - bbox[0]; h = bbox[3] - bbox[1]
    d.text(((64 - w) / 2 - bbox[0], (64 - h) / 2 - bbox[1] - 2),
           text, fill="#fff", font=font)
    return img


# ---------- uvicorn 백그라운드 ----------
_server: uvicorn.Server | None = None
_server_thread: threading.Thread | None = None


def _run_server():
    global _server
    config = uvicorn.Config(
        "app.main:app",
        host=settings.host, port=settings.port,
        log_level="warning",
    )
    _server = uvicorn.Server(config)
    _server.run()


def _start_server() -> None:
    global _server_thread
    _server_thread = threading.Thread(target=_run_server, daemon=True)
    _server_thread.start()
    # 헬스체크 — 5초 안에 안 뜨면 그냥 진행
    for _ in range(50):
        try:
            httpx.get(f"http://{settings.host}:{settings.port}/api/me", timeout=0.5)
            return
        except Exception:
            time.sleep(0.1)


def _stop_server() -> None:
    if _server:
        _server.should_exit = True


# ---------- 트레이 액션 ----------
def _open_dashboard(_icon=None, _item=None):
    webbrowser.open(f"http://{settings.host}:{settings.port}/dashboard")


def _open_settings(_icon=None, _item=None):
    webbrowser.open(f"http://{settings.host}:{settings.port}/settings")


def _open_folder(_icon=None, _item=None):
    try:
        os.startfile(str(settings.download_root))
    except Exception:
        pass


def _sync_now(_icon=None, _item=None):
    try:
        httpx.post(f"http://{settings.host}:{settings.port}/api/sync", timeout=5)
    except Exception:
        pass


def _quit(icon: pystray.Icon, _item=None):
    _stop_server()
    icon.stop()


def main():
    _start_server()

    icon = pystray.Icon(
        name="suwon-lms-sync",
        title="수원대 LMS Sync",
        icon=_make_icon("SU"),
        menu=pystray.Menu(
            pystray.MenuItem("대시보드 열기", _open_dashboard, default=True),
            pystray.MenuItem("설정", _open_settings),
            pystray.MenuItem("다운로드 폴더 열기", _open_folder),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("지금 동기화", _sync_now),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("종료", _quit),
        ),
    )
    # 시작 시 대시보드 자동 오픈
    threading.Timer(1.5, _open_dashboard).start()
    icon.run()


if __name__ == "__main__":
    main()
