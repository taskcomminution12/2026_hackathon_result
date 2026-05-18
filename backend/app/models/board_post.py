from __future__ import annotations
from datetime import datetime
from sqlmodel import SQLModel, Field


class BoardPost(SQLModel, table=True):
    """LearningX 게시판 글."""
    id: int = Field(primary_key=True)                    # learningx_board post id
    subject_id: int = Field(foreign_key="subject.id", index=True)
    board_id: int = Field(index=True)
    board_title: str
    title: str
    user_name: str | None = None
    is_notice: bool = False
    attachment_count: int = 0
    posted_at: datetime | None = None
    post_url: str | None = None                          # LMS 원본 URL
