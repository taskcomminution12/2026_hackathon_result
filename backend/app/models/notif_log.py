from __future__ import annotations
from datetime import datetime
from sqlmodel import SQLModel, Field


class NotifLog(SQLModel, table=True):
    """알림 발송 이력. (assignment_id, days_left) 단위로 1회만 보내도록 중복 방지에 사용."""
    id: int | None = Field(default=None, primary_key=True)
    assignment_id: int = Field(index=True)
    days_left_bucket: int = Field(index=True)        # 7 / 3 / 1 / 0 (당일)
    sent_at: datetime
    success: bool = True
    error: str | None = None
