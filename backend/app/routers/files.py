from __future__ import annotations

import os
import subprocess
import sys
from collections import defaultdict

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from ..config import settings
from ..db import get_session
from ..models import File as FileRow, Subject, Week
from ._serial import utc_iso

router = APIRouter()


# ---------- OS 탐색기 ----------

def _open_in_os(path: str, *, select_file: bool = False) -> None:
    """OS 기본 파일 매니저로 path 열기. Windows / macOS / Linux."""
    try:
        if sys.platform.startswith("win"):
            if select_file:
                subprocess.Popen(["explorer", "/select,", path])
            else:
                subprocess.Popen(["explorer", path])
        elif sys.platform == "darwin":
            subprocess.Popen(["open", "-R", path] if select_file else ["open", path])
        else:
            target = os.path.dirname(path) if select_file else path
            subprocess.Popen(["xdg-open", target])
    except Exception as e:
        raise HTTPException(500, str(e))


# ---------- 목록 / 통계 ----------

@router.get("/files")
def list_files(limit: int = 20, session: Session = Depends(get_session)):
    """최근 다운로드된 파일 (활동 피드용)."""
    rows = session.exec(
        select(FileRow).order_by(FileRow.downloaded_at.desc()).limit(limit)
    ).all()
    sub_map = {s.id: s for s in session.exec(select(Subject)).all()}
    return [
        {
            "id": f.id,
            "title": f.title,
            "file_name": f.file_name,
            "content_type": f.content_type,
            "subject": {
                "id": f.subject_id,
                "name": sub_map[f.subject_id].name if f.subject_id in sub_map else "?",
                "color": sub_map[f.subject_id].color if f.subject_id in sub_map else "blue",
            },
            "downloaded_at": utc_iso(f.downloaded_at),
        }
        for f in rows if f.downloaded_at
    ]


@router.get("/files/stats")
def stats(session: Session = Depends(get_session)):
    """대시보드 KPI + 차트용 통계 — 주차(1~15) × 과목 누적."""
    files = session.exec(select(FileRow)).all()
    weeks = session.exec(select(Week)).all()
    subjects = session.exec(select(Subject)).all()

    week_pos = {w.id: w.week_position for w in weeks}
    counts: dict[int, dict[int, int]] = defaultdict(lambda: defaultdict(int))
    for f in files:
        wp = week_pos.get(f.week_id, 0)
        if 1 <= wp <= 15:
            counts[wp][f.subject_id] += 1

    weekly = [
        {
            "week": wp,
            "by_subject": [
                {
                    "subject_id": s.id,
                    "subject_name": s.name,
                    "color": s.color,
                    "count": counts[wp].get(s.id, 0),
                }
                for s in subjects
            ],
        }
        for wp in range(1, 16)
    ]
    return {
        "total_files": len(files),
        "subjects_count": len(subjects),
        "weekly": weekly,
    }


# ---------- 폴더 / 파일 열기 ----------

@router.post("/files/{file_id}/open")
def open_file(file_id: int, session: Session = Depends(get_session)):
    """OS 탐색기에서 파일 위치 열기 (선택된 상태로)."""
    f = session.get(FileRow, file_id)
    if not f or not f.local_path:
        raise HTTPException(404, "파일 없음")
    path = os.path.abspath(f.local_path)
    if not os.path.exists(path):
        raise HTTPException(404, f"로컬 파일 없음: {path}")
    _open_in_os(path, select_file=True)
    return {"ok": True, "path": path}


@router.post("/files/open-root")
def open_download_root():
    """다운로드 루트 폴더 열기."""
    path = str(settings.download_root)
    _open_in_os(path)
    return {"ok": True, "path": path}


@router.post("/files/open-folder")
def open_folder(payload: dict):
    """임의 폴더 열기 — 과목 폴더 등."""
    folder = payload.get("path") or ""
    if not folder or not os.path.isdir(folder):
        raise HTTPException(404, f"폴더 없음: {folder}")
    _open_in_os(folder)
    return {"ok": True, "path": folder}
