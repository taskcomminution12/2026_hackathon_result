from __future__ import annotations

import hashlib
from collections import defaultdict
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlmodel import Session, select

from ..config import settings
from ..db import get_session
from ..models import File as FileRow, Subject, Week, WeekItem
from ..services.filename import build_target_path, safe
from ._serial import utc_iso

router = APIRouter()


@router.get("/courses")
def list_courses(session: Session = Depends(get_session)):
    """사이드바 + KPI에 쓸 과목 목록 + 파일 카운트."""
    subjects = session.exec(select(Subject)).all()
    counts = defaultdict(int)
    for f in session.exec(select(FileRow)).all():
        counts[f.subject_id] += 1
    return [
        {
            "id": s.id,
            "name": s.name,
            "course_code": s.course_code,
            "color": s.color or "blue",
            "file_count": counts.get(s.id, 0),
            "last_synced_at": utc_iso(s.last_synced_at),
        }
        for s in subjects
    ]


@router.get("/courses/{course_id}/tree")
def course_tree(course_id: int, session: Session = Depends(get_session)):
    """한 과목의 주차/파일 트리."""
    subj = session.get(Subject, course_id)
    if not subj:
        return {"subject": None, "weeks": []}

    weeks = session.exec(
        select(Week).where(Week.subject_id == course_id)
        .order_by(Week.week_position)
    ).all()
    files = session.exec(
        select(FileRow).where(FileRow.subject_id == course_id)
    ).all()
    week_items = session.exec(
        select(WeekItem).where(WeekItem.subject_id == course_id)
        .order_by(WeekItem.position)
    ).all()

    files_by_title: dict[tuple[int, str], FileRow] = {
        (f.week_id or 0, f.title): f for f in files if f.title and f.week_id
    }

    items_by_week: dict[int, list] = defaultdict(list)
    for it in week_items:
        item = {
            "id": it.id,
            "type": it.type,
            "title": it.title,
            "html_url": it.html_url,
            "external_url": it.external_url,
            "description": it.description,
            "due_at": utc_iso(it.due_at),
            "points_possible": it.points_possible,
            "file": None,
        }
        if it.type == "ExternalTool":
            f = files_by_title.get((it.week_id, it.title))
            if f and f.downloaded_at:
                item["file"] = {
                    "id": f.id,
                    "file_name": f.file_name,
                    "file_size": f.file_size,
                    "content_type": f.content_type,
                    "local_path": f.local_path,
                    "downloaded_at": utc_iso(f.downloaded_at),
                }
        items_by_week[it.week_id].append(item)

    # 게시판 파일
    board_files = [f for f in files if f.source == "board"]
    boards_section = []
    boards_grouped: dict[str, list] = defaultdict(list)
    for f in board_files:
        boards_grouped[f.board_title or "게시판"].append({
            "id": f.id,
            "title": f.title,
            "file_name": f.file_name,
            "file_size": f.file_size,
            "content_type": f.content_type,
            "downloaded_at": utc_iso(f.downloaded_at),
        })
    for name, lst in boards_grouped.items():
        boards_section.append({"title": name, "files": lst})

    return {
        "subject": {"id": subj.id, "name": subj.name, "color": subj.color},
        "weeks": [
            {
                "id": w.id,
                "title": w.title,
                "week_position": w.week_position,
                "items": items_by_week.get(w.id, []),
            }
            for w in weeks
        ],
        "boards": boards_section,
    }


# ---------- 수동 업로드 ----------

@router.post("/courses/{course_id}/upload")
async def upload_to_course(
    course_id: int,
    week_id: int | None = Form(default=None),
    upload: UploadFile = File(...),
    session: Session = Depends(get_session),
):
    """드래그·드롭으로 자료 추가. week_id 가 주어지면 해당 주차로,
    없으면 과목 루트 아래 `_수동자료/` 폴더로 떨어짐."""
    subj = session.get(Subject, course_id)
    if not subj:
        raise HTTPException(404, "과목 없음")

    week: Week | None = None
    if week_id:
        week = session.get(Week, week_id)
        if not week or week.subject_id != course_id:
            raise HTTPException(400, "잘못된 주차")

    content = await upload.read()
    if not content:
        raise HTTPException(400, "빈 파일")
    file_name = safe(upload.filename or "untitled.bin")

    if week:
        target = build_target_path(
            settings.download_root, subj.name,
            week.week_position, week.title, file_name,
        )
    else:
        target = settings.download_root / safe(subj.name) / "_수동자료" / file_name
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(content)

    sha = hashlib.sha256(content).hexdigest()
    title = upload.filename or file_name
    if "." in title:
        title = title.rsplit(".", 1)[0]

    row = FileRow(
        subject_id=course_id,
        week_id=week.id if week else None,
        title=title,
        file_name=file_name,
        source="manual",
        content_type=upload.content_type,
        file_size=len(content),
        local_path=str(target),
        sha256=sha,
        downloaded_at=datetime.now(timezone.utc),
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return {
        "id": row.id,
        "file_name": row.file_name,
        "local_path": row.local_path,
        "file_size": row.file_size,
        "week": {"id": week.id, "title": week.title} if week else None,
    }
