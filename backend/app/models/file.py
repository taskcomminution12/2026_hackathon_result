from __future__ import annotations
from datetime import datetime
from sqlmodel import SQLModel, Field


class File(SQLModel, table=True):
    """다운로드된 자료. source: module | announcement | board."""
    id: int | None = Field(default=None, primary_key=True)
    subject_id: int = Field(foreign_key="subject.id", index=True)
    week_id: int | None = Field(default=None, foreign_key="week.id", index=True)
    title: str
    file_name: str
    source: str = Field(default="module", index=True)
    xinics_content_id: str | None = Field(default=None, index=True, unique=True)
    canvas_file_id: int | None = Field(default=None, index=True)
    announcement_id: int | None = Field(default=None, foreign_key="announcement.id", index=True)
    board_post_id: int | None = Field(default=None, foreign_key="boardpost.id", index=True)
    board_title: str | None = None                          # 게시판 이름 (보기용)
    content_type: str | None = None
    file_size: int | None = None
    local_path: str | None = None
    sha256: str | None = None
    downloaded_at: datetime | None = None
