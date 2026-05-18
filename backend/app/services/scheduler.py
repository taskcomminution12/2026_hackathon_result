"""APScheduler — 백그라운드 자동 동기화.

interval_minutes:
  0  → 실시간 모드 (sync 끝나면 곧바로 다음 sync 시작, 사이에 10초 간격만 둠)
  >0 → 그 주기로 cron 식 interval
"""
from __future__ import annotations

import logging
import threading
import time
from datetime import datetime

from apscheduler.schedulers.background import BackgroundScheduler
from sqlmodel import Session, select

from ..db import engine
from ..models import AppSetting, SyncLog
from . import notify
from .sync import run_full_sync

log = logging.getLogger(__name__)

KEY_INTERVAL = "sync_interval_minutes"
REALTIME_GAP_SEC = 10                  # 실시간 모드에서 sync 사이 최소 휴식

_scheduler: BackgroundScheduler | None = None
_state = {"interval_minutes": 30, "last_run": None, "next_run": None,
          "realtime": False}
_realtime_thread: threading.Thread | None = None
_realtime_stop = threading.Event()


# ---------- DB 영구화 ----------

def _load_interval() -> int:
    with Session(engine) as session:
        row = session.exec(select(AppSetting).where(AppSetting.key == KEY_INTERVAL)).first()
        if row and row.value.isdigit():
            return int(row.value)
        return 30


def _save_interval(minutes: int) -> None:
    with Session(engine) as session:
        row = session.exec(select(AppSetting).where(AppSetting.key == KEY_INTERVAL)).first()
        if row:
            row.value = str(minutes)
            session.add(row)
        else:
            session.add(AppSetting(key=KEY_INTERVAL, value=str(minutes)))
        session.commit()


# ---------- 동기화 잡 ----------

def _run_sync_once() -> SyncLog | None:
    with Session(engine) as session:
        running = session.exec(
            select(SyncLog).where(SyncLog.status == "running").limit(1)
        ).first()
        if running:
            log.info("auto-sync skipped — already running (id=%s)", running.id)
            return None
        log.info("auto-sync started")
        result = run_full_sync(session)
        _state["last_run"] = datetime.utcnow().isoformat()
        log.info("auto-sync done id=%s status=%s added=%s skipped=%s failed=%s",
                 result.id, result.status, result.files_added,
                 result.files_skipped, result.files_failed)
        return result


def _job():
    _run_sync_once()


def _notify_job():
    try:
        notify.run_once()
    except Exception:
        log.exception("notify job failed")


# ---------- 실시간 모드 ----------

def _realtime_loop():
    """sync 끝나면 GAP 잠깐 쉬고 다시 sync."""
    log.info("realtime sync loop started")
    while not _realtime_stop.is_set():
        try:
            _run_sync_once()
        except Exception:
            log.exception("realtime sync failed")
        # 짧은 휴식 — 다른 작업이 끼어들 여지
        if _realtime_stop.wait(timeout=REALTIME_GAP_SEC):
            break
    log.info("realtime sync loop stopped")


def _start_realtime() -> None:
    global _realtime_thread
    _stop_realtime()
    _realtime_stop.clear()
    _realtime_thread = threading.Thread(target=_realtime_loop, daemon=True)
    _realtime_thread.start()
    _state["realtime"] = True


def _stop_realtime() -> None:
    global _realtime_thread
    if _realtime_thread and _realtime_thread.is_alive():
        _realtime_stop.set()
        _realtime_thread.join(timeout=2)
    _realtime_thread = None
    _state["realtime"] = False


# ---------- entry ----------

def start(interval_minutes: int | None = None) -> None:
    global _scheduler
    if _scheduler:
        return

    # DB 에 저장된 값이 있으면 그것을 우선. 인자 값은 디폴트.
    db_val = _load_interval()
    interval = db_val if db_val is not None else (interval_minutes or 30)

    _scheduler = BackgroundScheduler(timezone="Asia/Seoul")
    # 알림 — 매시 정각
    _scheduler.add_job(_notify_job, "cron", minute=0,
                       id="notify", replace_existing=True,
                       max_instances=1, coalesce=True)
    _scheduler.start()

    _apply_interval(interval, persist=False)
    log.info("scheduler started — interval %s", _interval_label(interval))


def stop() -> None:
    global _scheduler
    _stop_realtime()
    if _scheduler:
        _scheduler.shutdown(wait=False)
        _scheduler = None


def set_interval(minutes: int) -> None:
    """주기 변경 + DB 영구 저장. 0 이면 실시간 모드."""
    _apply_interval(minutes, persist=True)


def _apply_interval(minutes: int, *, persist: bool) -> None:
    if _scheduler is None:
        # start() 호출 전이면 상태만 저장
        _state["interval_minutes"] = minutes
        if persist:
            _save_interval(minutes)
        return

    # 1) 기존 full-sync 잡 제거
    if _scheduler.get_job("full-sync"):
        _scheduler.remove_job("full-sync")
    _stop_realtime()

    if minutes <= 0:
        # 실시간 모드
        _start_realtime()
    else:
        _scheduler.add_job(_job, "interval", minutes=minutes,
                           id="full-sync", replace_existing=True,
                           max_instances=1, coalesce=True)

    _state["interval_minutes"] = minutes
    if persist:
        _save_interval(minutes)
    log.info("scheduler interval → %s", _interval_label(minutes))


def _interval_label(minutes: int) -> str:
    return "realtime" if minutes <= 0 else f"every {minutes}min"


def status() -> dict:
    next_run = None
    if _scheduler and _scheduler.get_job("full-sync"):
        nrt = _scheduler.get_job("full-sync").next_run_time
        if nrt:
            next_run = nrt.isoformat()
    return {
        "enabled": _scheduler is not None,
        "interval_minutes": _state["interval_minutes"],
        "realtime": _state["realtime"],
        "last_run": _state["last_run"],
        "next_run": next_run,
    }
