from __future__ import annotations
from datetime import datetime
from sqlmodel import SQLModel, Field


class Assignment(SQLModel, table=True):
    """Canvas 과제."""
    id: int = Field(primary_key=True)              # Canvas assignment id
    subject_id: int = Field(foreign_key="subject.id", index=True)
    title: str
    unlock_at: datetime | None = None              # 이용 시작
    due_at: datetime | None = None                 # 마감 (= 이용 가능 종료 권장 시점)
    lock_at: datetime | None = None                # 완전 잠금 (이용 가능 종료)
    points_possible: float | None = None
    submitted: bool = False
    html_url: str | None = None
