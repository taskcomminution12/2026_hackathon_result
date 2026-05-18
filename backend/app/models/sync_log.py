from __future__ import annotations
from datetime import datetime
from sqlmodel import SQLModel, Field


class SyncLog(SQLModel, table=True):
    """동기화 작업 로그 — 대시보드 활동 피드 + 진행 상황 표시용."""
    id: int | None = Field(default=None, primary_key=True)
    started_at: datetime
    finished_at: datetime | None = None
    status: str = "running"                  # running/done/failed
    courses_total: int = 0
    files_added: int = 0
    files_skipped: int = 0
    files_failed: int = 0
    error: str | None = None
