from __future__ import annotations
from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException
from pydantic import BaseModel, Field
from sqlmodel import Session, select

from ..db import get_session, engine
from ..models import SyncLog
from ..services.sync import run_full_sync
from ..services import scheduler, watcher
from ._serial import utc_iso

router = APIRouter()


def _bg_sync():
    """백그라운드용 — 별도 세션 만들어서 실행."""
    with Session(engine) as s:
        run_full_sync(s)


@router.post("/sync")
def trigger_sync(bg: BackgroundTasks, session: Session = Depends(get_session)):
    """수동 동기화 트리거. 진행 중인 잡 있으면 무시."""
    running = session.exec(
        select(SyncLog).where(SyncLog.status == "running")
    ).first()
    if running:
        return {"started": False, "running_id": running.id}
    bg.add_task(_bg_sync)
    return {"started": True}


@router.get("/sync/history")
def sync_history(limit: int = 20, session: Session = Depends(get_session)):
    rows = session.exec(
        select(SyncLog).order_by(SyncLog.id.desc()).limit(limit)
    ).all()
    return [
        {
            "id": r.id,
            "started_at": utc_iso(r.started_at),
            "finished_at": utc_iso(r.finished_at),
            "status": r.status,
            "files_added": r.files_added,
            "files_skipped": r.files_skipped,
            "files_failed": r.files_failed,
            "error": r.error,
        }
        for r in rows
    ]


@router.get("/sync/scheduler")
def get_scheduler():
    return scheduler.status()


class IntervalIn(BaseModel):
    # 0 = 실시간 모드 (sync 끝나면 즉시 재시작)
    minutes: int = Field(ge=0, le=720)


@router.put("/sync/scheduler")
def set_scheduler(payload: IntervalIn):
    scheduler.set_interval(payload.minutes)
    return scheduler.status()


@router.get("/sync/watcher")
def watcher_recent(limit: int = 20):
    return {"recent": watcher.recent(limit)}


@router.get("/sync/status")
def sync_status(session: Session = Depends(get_session)):
    """대시보드 동기화 카드 — 최근 잡 상태."""
    last = session.exec(
        select(SyncLog).order_by(SyncLog.id.desc()).limit(1)
    ).first()
    if not last:
        return {"status": "idle"}
    return {
        "id": last.id,
        "status": last.status,
        "started_at": utc_iso(last.started_at),
        "finished_at": utc_iso(last.finished_at),
        "courses_total": last.courses_total,
        "files_added": last.files_added,
        "files_skipped": last.files_skipped,
        "files_failed": last.files_failed,
        "error": last.error,
    }
