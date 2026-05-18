"""과제 마감 임박 알림 발송 — APScheduler 잡."""
from __future__ import annotations
import logging
from datetime import datetime, timezone, timedelta
from sqlmodel import Session, select

from ..config import settings
from ..db import engine
from ..models import Assignment, Subject, NotifLog
from . import kakao

log = logging.getLogger(__name__)


def _buckets() -> list[int]:
    raw = settings.notify_days_before or "7,3,1,0"
    out = []
    for s in raw.split(","):
        s = s.strip()
        if s.isdigit():
            out.append(int(s))
    return sorted(set(out), reverse=True)


def _bucket_for(days_left: float, buckets: list[int]) -> int | None:
    """남은 일수가 어느 버킷에 해당하는지. 0보다 작으면 None."""
    if days_left < 0:
        return None
    # buckets: [7,3,1,0]
    # 7.0 → 7,  3.5 → 3, 1.2 → 1, 0.5 → 0
    for b in buckets:
        if days_left <= b:
            continue
        # days_left > b 인 경우 못 찾음 — 다음으로
    matched = None
    for b in buckets:
        if days_left <= b:
            matched = b
    return matched


def run_once() -> None:
    """현재 시각 기준 임박 과제를 점검해 카톡 발송."""
    buckets = _buckets()
    if not buckets:
        return

    with Session(engine) as session:
        token = kakao.get_valid_token(session)
        if not token:
            log.info("notify: 카톡 토큰 없음 — 스킵")
            return

        now = datetime.now(timezone.utc)
        assigns = session.exec(
            select(Assignment).where(Assignment.due_at.is_not(None))
        ).all()
        sub_map = {s.id: s for s in session.exec(select(Subject)).all()}

        for a in assigns:
            if a.submitted:
                continue
            due = a.due_at if a.due_at.tzinfo else a.due_at.replace(tzinfo=timezone.utc)
            days_left = (due - now).total_seconds() / 86400.0
            bucket = _bucket_for(days_left, buckets)
            if bucket is None:
                continue

            # 중복 방지 — (assignment_id, bucket) 별 1회
            already = session.exec(
                select(NotifLog).where(
                    (NotifLog.assignment_id == a.id) &
                    (NotifLog.days_left_bucket == bucket)
                )
            ).first()
            if already:
                continue

            subj = sub_map.get(a.subject_id)
            subj_name = subj.name if subj else "?"

            d_label = f"D-{bucket}" if bucket > 0 else "오늘"
            title = f"[{d_label}] {subj_name} — {a.title}"
            body = (
                f"마감: {due.astimezone().strftime('%Y-%m-%d %H:%M')}\n"
                f"{('점수: ' + str(a.points_possible) + '점') if a.points_possible else ''}"
            ).strip()

            ok = kakao.send_memo(
                token, title=title, body=body,
                link_url=a.html_url or "https://lms.suwon.ac.kr",
            )
            session.add(NotifLog(
                assignment_id=a.id, days_left_bucket=bucket,
                sent_at=datetime.utcnow(), success=ok,
                error=None if ok else "kakao API 실패",
            ))
            session.commit()
            log.info("notify sent: %s (bucket=%s) ok=%s", title, bucket, ok)
