"""DB 의 datetime 을 API 응답으로 보낼 때 UTC 임을 명시한 ISO 문자열로 변환.

문제: SQLite 가 datetime 의 tzinfo를 잃어버려서, 우리가 UTC로 저장해도
naive datetime 으로 돌아온다. naive 를 그대로 isoformat 하면
프론트의 new Date(iso) 가 로컬 시간으로 해석해 9시간 어긋남.
"""
from __future__ import annotations
from datetime import datetime, timezone


def utc_iso(dt: datetime | None) -> str | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat()
