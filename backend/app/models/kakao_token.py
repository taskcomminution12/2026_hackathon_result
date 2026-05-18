from __future__ import annotations
from datetime import datetime
from sqlmodel import SQLModel, Field


class KakaoToken(SQLModel, table=True):
    """카카오 OAuth 토큰 — 단일 사용자 가정 (id=1 고정)."""
    id: int = Field(default=1, primary_key=True)
    access_token: str
    refresh_token: str
    expires_at: datetime
    refresh_expires_at: datetime | None = None
    scope: str | None = None
    updated_at: datetime
