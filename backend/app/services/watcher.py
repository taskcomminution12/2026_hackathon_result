"""Watchdog — 다운로드 폴더에 새 파일이 떨어지면 인덱스 + 활동 로그.

iPad GoodNotes 자동 백업 → OneDrive → PC 동기화 → 우리가 감지.
주의: 우리 sync가 만든 파일도 같이 잡힐 수 있어 단순히 'created' 이벤트만 기록.
"""
from __future__ import annotations
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileCreatedEvent, FileMovedEvent

from ..config import settings

log = logging.getLogger(__name__)

_observer: Optional[Observer] = None
_recent_events: list[dict] = []         # 최근 50개
_MAX = 50


class _Handler(FileSystemEventHandler):
    def on_created(self, event):
        if event.is_directory:
            return
        self._record(event.src_path, "created")

    def on_moved(self, event: FileMovedEvent):
        if event.is_directory:
            return
        self._record(event.dest_path, "moved")

    def _record(self, path: str, kind: str):
        try:
            p = Path(path)
            if not p.exists():
                return
            # 0바이트는 스킵 (생성 직후 잠깐 0인 경우 많음)
            try:
                if p.stat().st_size == 0:
                    return
            except OSError:
                return
            entry = {
                "path": str(p),
                "name": p.name,
                "size": p.stat().st_size,
                "kind": kind,
                "at": datetime.utcnow().isoformat(),
                "rel": str(p.relative_to(settings.download_root))
                       if str(p).startswith(str(settings.download_root))
                       else p.name,
            }
            _recent_events.insert(0, entry)
            del _recent_events[_MAX:]
            log.info("watcher %s: %s", kind, entry["rel"])
        except Exception as e:
            log.exception("watcher record failed: %s", e)


def start() -> None:
    global _observer
    if _observer:
        return
    root = settings.download_root
    root.mkdir(parents=True, exist_ok=True)
    _observer = Observer()
    _observer.schedule(_Handler(), str(root), recursive=True)
    _observer.daemon = True
    _observer.start()
    log.info("watcher started: %s", root)


def stop() -> None:
    global _observer
    if _observer:
        _observer.stop()
        _observer.join(timeout=2)
        _observer = None


def recent(limit: int = 20) -> list[dict]:
    return _recent_events[:limit]
