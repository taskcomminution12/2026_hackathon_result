from __future__ import annotations
from sqlmodel import SQLModel, Field


class AppSetting(SQLModel, table=True):
    """런타임에 변경할 수 있는 설정 (key/value). .env 보다 우선."""
    key: str = Field(primary_key=True)
    value: str
