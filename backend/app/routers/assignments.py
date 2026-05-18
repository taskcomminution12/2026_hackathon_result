from __future__ import annotations
from datetime import datetime, timezone
from collections import Counter
from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from ..db import get_session
from ..models import Assignment, Subject
from ._serial import utc_iso

router = APIRouter()


def _bucket(due: datetime, now: datetime) -> str | None:
    """D-1 / D-3 / D-7 / D-14 분류. 마감 지난 건 None."""
    delta = (due - now).total_seconds() / 86400.0
    if delta < 0:    return None
    if delta <= 1:   return "d1"
    if delta <= 3:   return "d3"
    if delta <= 7:   return "d7"
    if delta <= 14:  return "d14"
    return None


@router.get("/assignments/upcoming")
def upcoming(limit: int = 10, session: Session = Depends(get_session)):
    """임박 과제 — 대시보드 테이블."""
    now = datetime.now(timezone.utc)
    rows = session.exec(
        select(Assignment)
        .where(Assignment.due_at.is_not(None))
        .order_by(Assignment.due_at)
    ).all()

    sub_map = {s.id: s for s in session.exec(select(Subject)).all()}
    out = []
    for a in rows:
        if not a.due_at:
            continue
        if a.due_at.tzinfo is None:
            due = a.due_at.replace(tzinfo=timezone.utc)
        else:
            due = a.due_at
        if (due - now).total_seconds() < -86400:
            continue
        s = sub_map.get(a.subject_id)
        out.append({
            "id": a.id,
            "title": a.title,
            "subject": {
                "id": a.subject_id,
                "name": s.name if s else "?",
                "color": s.color if s else "blue",
            },
            "unlock_at": utc_iso(a.unlock_at),
            "due_at": utc_iso(due),
            "lock_at": utc_iso(a.lock_at),
            "days_left": round((due - now).total_seconds() / 86400.0, 1),
            "submitted": a.submitted,
            "html_url": a.html_url,
        })
        if len(out) >= limit:
            break
    return out


@router.get("/assignments/deadline-distribution")
def deadline_distribution(session: Session = Depends(get_session)):
    """도넛용 — D-1/3/7/14 버킷."""
    now = datetime.now(timezone.utc)
    rows = session.exec(
        select(Assignment).where(Assignment.due_at.is_not(None))
    ).all()

    counter = Counter()
    for a in rows:
        if not a.due_at:
            continue
        due = a.due_at if a.due_at.tzinfo else a.due_at.replace(tzinfo=timezone.utc)
        b = _bucket(due, now)
        if b:
            counter[b] += 1
    return {
        "d1": counter["d1"],
        "d3": counter["d3"],
        "d7": counter["d7"],
        "d14": counter["d14"],
    }
