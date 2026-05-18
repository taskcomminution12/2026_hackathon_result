"""DB 기반 런타임 설정 헬퍼.

config.settings 는 .env 의 초기값. AppSetting 테이블에 같은 key 가 있으면 그 값을 우선.
서버 시작 시 한 번 적용 + 변경 시 즉시 반영.
"""
from __future__ import annotations
from pathlib import Path
from sqlmodel import Session, select

from ..config import settings
from ..db import engine
from ..models import AppSetting

KEY_DOWNLOAD_ROOT = "download_root"
KEY_CANVAS_TOKEN = "canvas_token"


def _get(session: Session, key: str) -> str | None:
    row = session.exec(select(AppSetting).where(AppSetting.key == key)).first()
    return row.value if row else None


def _set(session: Session, key: str, value: str) -> None:
    row = session.exec(select(AppSetting).where(AppSetting.key == key)).first()
    if row:
        row.value = value
        session.add(row)
    else:
        session.add(AppSetting(key=key, value=value))
    session.commit()


def apply_to_settings() -> None:
    """서버 시작 시 — DB 에 저장된 값을 settings 객체에 덮어씀."""
    with Session(engine) as session:
        download_root = _get(session, KEY_DOWNLOAD_ROOT)
        if download_root:
            settings.download_root = Path(download_root).expanduser().resolve()
            settings.download_root.mkdir(parents=True, exist_ok=True)
        canvas_token = _get(session, KEY_CANVAS_TOKEN)
        if canvas_token:
            settings.canvas_token = canvas_token


def save_download_root(path: str) -> Path:
    """다운로드 폴더 변경 — DB 저장 + settings 즉시 반영."""
    p = Path(path).expanduser().resolve()
    p.mkdir(parents=True, exist_ok=True)
    with Session(engine) as session:
        _set(session, KEY_DOWNLOAD_ROOT, str(p))
    settings.download_root = p
    return p


def save_canvas_token(token: str) -> None:
    """Canvas 토큰 변경 — DB 저장 + settings 즉시 반영. 빈 문자열이면 삭제."""
    token = token.strip()
    with Session(engine) as session:
        if token:
            _set(session, KEY_CANVAS_TOKEN, token)
        else:
            row = session.exec(select(AppSetting).where(AppSetting.key == KEY_CANVAS_TOKEN)).first()
            if row:
                session.delete(row)
                session.commit()
    settings.canvas_token = token
