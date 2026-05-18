from __future__ import annotations
from sqlmodel import SQLModel, Field


class Week(SQLModel, table=True):
    """주차 (LearningX module = 한 주차)."""
    id: int = Field(primary_key=True)            # LearningX module_id
    subject_id: int = Field(foreign_key="subject.id", index=True)
    title: str                                    # "1주차"
    week_position: int                            # 1..15
