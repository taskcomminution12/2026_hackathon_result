from __future__ import annotations
from datetime import datetime
from sqlmodel import SQLModel, Field


class WeekItem(SQLModel, table=True):
    """모듈 안의 모든 항목 — 자료/과제/페이지/퀴즈/토론/링크.
    type 별로 의미가 다르고, 'ExternalTool' 자료는 별도 File 테이블과 매핑된다.
    """
    id: int = Field(primary_key=True)                   # Canvas module_item id
    subject_id: int = Field(foreign_key="subject.id", index=True)
    week_id: int = Field(foreign_key="week.id", index=True)
    type: str = Field(index=True)                        # ExternalTool|Assignment|Page|Quiz|Discussion|ExternalUrl|SubHeader
    title: str
    position: int = 0
    html_url: str | None = None                          # Canvas LMS 항목 URL
    external_url: str | None = None                      # ExternalTool/ExternalUrl 의 외부 URL
    content_id: int | None = None                        # 외부도구·assignment·page 등의 ID
    description: str | None = None                       # HTML — 과제/페이지 본문 (별도 호출로 채움)

    # Assignment용
    due_at: datetime | None = None
    points_possible: float | None = None

    # File 매핑 (ExternalTool 자료가 다운로드된 경우 연결)
    file_id: int | None = Field(default=None, foreign_key="file.id", index=True)
