from __future__ import annotations
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..config import settings
from ..services import app_settings

router = APIRouter()


class SettingsOut(BaseModel):
    canvas_base_url: str
    download_root: str
    has_canvas_token: bool
    canvas_token_preview: str | None = None       # 앞 4·뒤 4자만 노출


class SettingsIn(BaseModel):
    download_root: str | None = None
    canvas_token: str | None = None


def _preview(token: str) -> str | None:
    if not token:
        return None
    if len(token) <= 10:
        return "*" * len(token)
    return f"{token[:4]}…{token[-4:]}"


def _out() -> SettingsOut:
    return SettingsOut(
        canvas_base_url=settings.canvas_base_url,
        download_root=str(settings.download_root),
        has_canvas_token=bool(settings.canvas_token),
        canvas_token_preview=_preview(settings.canvas_token),
    )


@router.get("/settings", response_model=SettingsOut)
def get_settings():
    return _out()


@router.put("/settings", response_model=SettingsOut)
def update_settings(payload: SettingsIn):
    """설정 변경. DB 에 영구 저장 + 즉시 반영."""
    if payload.download_root is not None:
        try:
            app_settings.save_download_root(payload.download_root)
        except Exception as e:
            raise HTTPException(400, f"폴더를 만들 수 없음: {e}")

    if payload.canvas_token is not None:
        app_settings.save_canvas_token(payload.canvas_token)

    return _out()
