from __future__ import annotations
from datetime import datetime
from sqlmodel import SQLModel, Field


class Subject(SQLModel, table=True):
    """Canvas course."""
    id: int = Field(primary_key=True)         # Canvas course id
    name: str
    course_code: str | None = None
    color: str | None = None                   # 사이드바 표시용 (blue/purple/teal/orange/pink)
    enrollment_state: str | None = None
    last_synced_at: datetime | None = None
