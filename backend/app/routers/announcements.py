from __future__ import annotations
from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from ..db import get_session
from ..models import Announcement, Subject
from ._serial import utc_iso

router = APIRouter()


@router.get("/announcements")
def recent(limit: int = 10, session: Session = Depends(get_session)):
    rows = session.exec(
        select(Announcement)
        .order_by(Announcement.posted_at.desc())
        .limit(limit)
    ).all()
    sub_map = {s.id: s for s in session.exec(select(Subject)).all()}
    return [
        {
            "id": a.id,
            "title": a.title,
            "subject": {
                "id": a.subject_id,
                "name": sub_map.get(a.subject_id).name if sub_map.get(a.subject_id) else "?",
                "color": sub_map.get(a.subject_id).color if sub_map.get(a.subject_id) else "blue",
            },
            "posted_at": utc_iso(a.posted_at),
            "html_url": a.html_url,
            "has_attachments": a.has_attachments,
        }
        for a in rows
    ]


@router.get("/courses/{course_id}/announcements")
def by_course(course_id: int, session: Session = Depends(get_session)):
    rows = session.exec(
        select(Announcement)
        .where(Announcement.subject_id == course_id)
        .order_by(Announcement.posted_at.desc())
    ).all()
    return [
        {
            "id": a.id,
            "title": a.title,
            "posted_at": utc_iso(a.posted_at),
            "html_url": a.html_url,
            "has_attachments": a.has_attachments,
        }
        for a in rows
    ]
