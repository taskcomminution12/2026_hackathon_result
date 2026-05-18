from __future__ import annotations
from datetime import datetime
from sqlmodel import SQLModel, Field


class Announcement(SQLModel, table=True):
    """Canvas 공지사항."""
    id: int = Field(primary_key=True)              # Canvas announcement id
    subject_id: int = Field(foreign_key="subject.id", index=True)
    title: str
    posted_at: datetime | None = None
    html_url: str | None = None
    has_attachments: bool = False
