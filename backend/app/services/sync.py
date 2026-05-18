"""전체 동기화 — Canvas + LearningX → DB upsert + 자료 다운로드.

flow:
  Canvas API 활성 과목
  └ 과목별 (순차):
     - 과제 메타 (Assignment)
     - 공지사항 + 첨부 다운 (Announcement)
     - LTI launch 로 xn_api_token 발급
       └ LearningX modules → 주차/자료 (Week, File)
       └ LearningX 게시판(Q&A 제외) → 글 + 첨부 (BoardPost, File)
     - Canvas 모듈 항목 통합 (WeekItem) — 과제/페이지 description 포함
  마지막에 디스크에 없는 File 레코드 정리
"""
from __future__ import annotations

import hashlib
import logging
import os
from datetime import datetime, timezone

from sqlmodel import Session, select

from ..config import settings
from ..models import (Announcement, Assignment, BoardPost,
                      File as FileRow, Subject, SyncLog, Week, WeekItem)
from . import canvas, learningx, learningx_board, lti, xinics
from .filename import assign_colors, build_target_path, safe

log = logging.getLogger(__name__)

# 게시판 도구 ID — 자료 ExternalTool 이 없는 과목에서 토큰 발급용 폴백
BOARD_TOOL_ID = 5


# ---------- 공통 유틸 ----------

def _now() -> datetime:
    return datetime.now(timezone.utc)


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _save_attachment(session: Session, *, content: bytes, target,
                     subject: Subject, sync_log: SyncLog,
                     source: str, file_query, base_row: dict) -> None:
    """Canvas attachment 다운로드 결과를 디스크 + DB에 반영."""
    new_hash = hashlib.sha256(content).hexdigest()
    target.parent.mkdir(parents=True, exist_ok=True)

    if target.exists() and xinics.sha256_of(target) == new_hash:
        status = "skip"
    else:
        target.write_bytes(content)
        status = "ok"

    existing = file_query(session)
    base_row.update({
        "local_path": str(target),
        "sha256": new_hash,
        "source": source,
        "subject_id": subject.id,
    })
    if existing:
        for k, v in base_row.items():
            setattr(existing, k, v)
        if status == "ok":
            existing.downloaded_at = _now()
        session.add(existing)
    else:
        base_row["downloaded_at"] = _now()
        session.add(FileRow(**base_row))

    if status == "ok":
        sync_log.files_added += 1
    else:
        sync_log.files_skipped += 1


# ---------- subjects ----------

def upsert_subjects(session: Session, courses: list[dict]) -> list[Subject]:
    color_map = assign_colors([c["id"] for c in courses])
    out = []
    for c in courses:
        existing = session.get(Subject, c["id"])
        kw = dict(
            name=c.get("name") or "(이름 없음)",
            course_code=c.get("course_code"),
            color=color_map.get(c["id"], "blue"),
            enrollment_state=c.get("enrollment_state"),
        )
        if existing:
            for k, v in kw.items():
                setattr(existing, k, v)
            session.add(existing)
            out.append(existing)
        else:
            row = Subject(id=c["id"], **kw)
            session.add(row)
            out.append(row)
    session.commit()
    return out


# ---------- weeks + module 자료 (Xinics) ----------

def upsert_weeks_and_files(session: Session, subject: Subject,
                           weeks_payload: list[dict],
                           cli, sync_log: SyncLog) -> None:
    for w in weeks_payload:
        wid = w.get("module_id") or w.get("id")
        if not wid:
            continue
        wp = w.get("week_position") or w.get("position") or 0
        title = w.get("title") or f"week-{wp}"
        existing = session.get(Week, wid)
        if existing:
            existing.subject_id = subject.id
            existing.title = title
            existing.week_position = wp
            session.add(existing)
        else:
            session.add(Week(id=wid, subject_id=subject.id,
                             title=title, week_position=wp))
    session.commit()

    xn_token = cli.cookies.get("xn_api_token")

    for asset in learningx.iter_assets(weeks_payload):
        download_url = None
        extension = None
        if xn_token:
            meta = learningx.get_commons_meta(cli, xn_token, asset["xinics_content_id"])
            if meta:
                download_url = meta.get("download_url")
                extension = meta.get("extension")

        target = build_target_path(
            settings.download_root, subject.name,
            asset["week_position"], asset["week_title"], asset["file_name"],
            content_type=asset["content_type"],
            extension=extension,
        )

        if download_url:
            status, _size, sha = xinics.download_via_url(
                cli, download_url, target,
                expected_type=asset["content_type"],
            )
        else:
            status, _size, sha = xinics.download(
                cli, asset["xinics_content_id"], asset["file_name"], target,
            )

        existing = session.exec(
            select(FileRow).where(FileRow.xinics_content_id == asset["xinics_content_id"])
        ).first()
        kw = dict(
            subject_id=subject.id,
            week_id=asset["week_id"],
            title=asset["title"],
            file_name=asset["file_name"],
            source="module",
            xinics_content_id=asset["xinics_content_id"],
            content_type=asset["content_type"],
            file_size=asset["file_size"],
            local_path=str(target) if status in ("ok", "skip") else None,
            sha256=sha,
        )
        if existing:
            for k, v in kw.items():
                setattr(existing, k, v)
            if status == "ok":
                existing.downloaded_at = _now()
            session.add(existing)
        else:
            kw["downloaded_at"] = _now() if status in ("ok", "skip") else None
            session.add(FileRow(**kw))

        if status == "ok":
            sync_log.files_added += 1
        elif status == "skip":
            sync_log.files_skipped += 1
        else:
            sync_log.files_failed += 1

    session.commit()


# ---------- announcements ----------

def upsert_announcements(session: Session, subject: Subject,
                         payload: list[dict], cli, sync_log: SyncLog) -> None:
    for ann in payload:
        ann_id = ann.get("id")
        if not ann_id:
            continue
        attachments = ann.get("attachments") or []

        existing = session.get(Announcement, ann_id)
        kw = dict(
            subject_id=subject.id,
            title=ann.get("title") or "(제목 없음)",
            posted_at=_parse_dt(ann.get("posted_at") or ann.get("created_at")),
            html_url=ann.get("html_url"),
            has_attachments=bool(attachments),
        )
        if existing:
            for k, v in kw.items():
                setattr(existing, k, v)
            session.add(existing)
        else:
            session.add(Announcement(id=ann_id, **kw))
        session.commit()

        for att in attachments:
            f_url = att.get("url")
            f_name = att.get("display_name") or att.get("filename") or f"attachment_{att.get('id', '')}"
            f_id = att.get("id")
            if not f_url or not f_id:
                continue

            content = canvas.download_canvas_attachment(cli, f_url)
            if content is None:
                sync_log.files_failed += 1
                continue

            target = (settings.download_root
                      / safe(subject.name) / "_공지사항" / safe(f_name))

            _save_attachment(
                session, content=content, target=target, subject=subject,
                sync_log=sync_log, source="announcement",
                file_query=lambda s, fid=f_id: s.exec(
                    select(FileRow).where(
                        (FileRow.canvas_file_id == fid) & (FileRow.source == "announcement")
                    )
                ).first(),
                base_row=dict(
                    week_id=None,
                    title=ann.get("title") or f_name,
                    file_name=f_name,
                    canvas_file_id=f_id,
                    announcement_id=ann_id,
                    content_type=att.get("content-type") or att.get("content_type"),
                    file_size=att.get("size"),
                ),
            )
        session.commit()


# ---------- board posts ----------

def upsert_board_posts(session: Session, subject: Subject,
                       xn_token: str, cli, sync_log: SyncLog) -> None:
    boards = learningx_board.list_boards(cli, subject.id, xn_token)
    if not boards:
        return

    for b in boards:
        if learningx_board.is_qna_board(b):
            continue
        bid = b.get("id")
        btitle = b.get("title") or "게시판"
        if not bid:
            continue

        for p in learningx_board.list_posts(cli, subject.id, bid, xn_token):
            pid = p.get("id")
            if not pid:
                continue

            kw = dict(
                subject_id=subject.id,
                board_id=bid,
                board_title=btitle,
                title=p.get("title") or "(제목 없음)",
                user_name=p.get("user_name"),
                is_notice=bool(p.get("is_notice")),
                attachment_count=int(p.get("attachment_count") or 0),
                posted_at=_parse_dt(p.get("created_at")),
                post_url=None,
            )
            attachments: list[dict] = []
            if (p.get("attachment_count") or 0) > 0:
                detail = learningx_board.get_post(cli, subject.id, bid, pid, xn_token)
                if detail:
                    attachments = detail.get("attachments") or []
                    kw["post_url"] = detail.get("post_url")

            existing_post = session.get(BoardPost, pid)
            if existing_post:
                for k, v in kw.items():
                    setattr(existing_post, k, v)
                session.add(existing_post)
            else:
                session.add(BoardPost(id=pid, **kw))
            session.commit()

            for att in attachments:
                f_url = att.get("url")
                f_name = att.get("filename") or att.get("display_name") or f"attach_{att.get('id', '')}"
                f_id = att.get("canvas_file_id") or att.get("id")
                if not f_url or not f_id:
                    continue

                content = canvas.download_canvas_attachment(cli, f_url)
                if content is None:
                    sync_log.files_failed += 1
                    continue

                target = (settings.download_root
                          / safe(subject.name) / "_게시판"
                          / safe(btitle) / safe(f_name))

                _save_attachment(
                    session, content=content, target=target, subject=subject,
                    sync_log=sync_log, source="board",
                    file_query=lambda s, fid=f_id: s.exec(
                        select(FileRow).where(
                            (FileRow.canvas_file_id == fid) & (FileRow.source == "board")
                        )
                    ).first(),
                    base_row=dict(
                        week_id=None,
                        title=p.get("title") or f_name,
                        file_name=f_name,
                        canvas_file_id=f_id,
                        board_post_id=pid,
                        board_title=btitle,
                        content_type=att.get("content-type") or att.get("content_type"),
                        file_size=att.get("filesize") or att.get("size"),
                    ),
                )
            session.commit()


# ---------- week items (Canvas modules → 모든 항목) ----------

def upsert_week_items(session: Session, subject: Subject, cli) -> None:
    try:
        modules = canvas.get_modules(cli, subject.id)
    except Exception:
        log.exception("modules fetch failed for course %s", subject.id)
        return

    for m in modules:
        wid = m.get("id")
        if not wid:
            continue
        try:
            items = canvas.get_module_items(cli, subject.id, wid, include_details=True)
        except Exception:
            log.exception("module items fetch failed for course %s module %s", subject.id, wid)
            continue

        for it in items:
            mi_id = it.get("id")
            t = it.get("type") or ""
            if not mi_id or t == "SubHeader":
                continue
            cd = it.get("content_details") or {}

            description: str | None = None
            if t == "Assignment" and it.get("content_id"):
                a = canvas.get_assignment(cli, subject.id, it["content_id"])
                if a:
                    description = a.get("description")
            elif t == "Page" and it.get("page_url"):
                p = canvas.get_page(cli, subject.id, it["page_url"])
                if p:
                    description = p.get("body")

            kw = dict(
                subject_id=subject.id,
                week_id=wid,
                type=t,
                title=it.get("title") or "(제목 없음)",
                position=it.get("position", 0),
                html_url=it.get("html_url"),
                external_url=it.get("external_url"),
                content_id=it.get("content_id"),
                due_at=_parse_dt(cd.get("due_at")),
                points_possible=cd.get("points_possible"),
                description=description,
            )
            existing = session.get(WeekItem, mi_id)
            if existing:
                for k, v in kw.items():
                    setattr(existing, k, v)
                session.add(existing)
            else:
                session.add(WeekItem(id=mi_id, **kw))
        session.commit()


# ---------- assignments ----------

def upsert_assignments(session: Session, subject_id: int,
                       payload: list[dict]) -> None:
    for a in payload:
        sub = a.get("submission") or {}
        submitted = (
            bool(sub.get("submitted_at"))
            or sub.get("workflow_state") in ("submitted", "graded")
        )
        kw = dict(
            subject_id=subject_id,
            title=a.get("name") or "(제목 없음)",
            unlock_at=_parse_dt(a.get("unlock_at")),
            due_at=_parse_dt(a.get("due_at")),
            lock_at=_parse_dt(a.get("lock_at")),
            points_possible=a.get("points_possible"),
            submitted=submitted,
            html_url=a.get("html_url"),
        )
        existing = session.get(Assignment, a["id"])
        if existing:
            for k, v in kw.items():
                setattr(existing, k, v)
            session.add(existing)
        else:
            session.add(Assignment(id=a["id"], **kw))
    session.commit()


# ---------- 정리 ----------

def _prune_missing_files(session: Session) -> int:
    """디스크에 없는 File 레코드를 DB에서 삭제. 반환: 삭제 건수."""
    rows = session.exec(select(FileRow)).all()
    removed = 0
    for f in rows:
        if not f.local_path:
            continue
        if not os.path.exists(f.local_path):
            session.delete(f)
            removed += 1
    if removed:
        session.commit()
        log.info("pruned %s missing file rows", removed)
    return removed


# ---------- entry point ----------

def _ensure_xn_token(cli, course_id: int) -> str | None:
    """LearningX 토큰 발급. ExternalTool 자료가 있으면 그쪽으로, 없으면 게시판 도구 폴백."""
    ext = canvas.find_first_external_tool(cli, course_id)
    if ext:
        mi_id, tool_id, ext_url = ext
        token = lti.get_xn_api_token(cli, course_id, mi_id, tool_id, ext_url)
        if token:
            return token
    return lti.get_xn_api_token(cli, course_id, tool_id=BOARD_TOOL_ID)


def run_full_sync(session: Session) -> SyncLog:
    """전체 동기화 — 과목들을 순차 처리. 항상 SyncLog 반환."""
    sync_log = SyncLog(started_at=_now(), status="running")
    session.add(sync_log)
    session.commit()
    session.refresh(sync_log)

    try:
        with canvas.make_client() as cli:
            courses = canvas.get_active_courses(cli)
            subjects = upsert_subjects(session, courses)
            sync_log.courses_total = len(subjects)
            session.add(sync_log)
            session.commit()

            for subj in subjects:
                upsert_assignments(session, subj.id, canvas.get_assignments(cli, subj.id))
                upsert_announcements(session, subj,
                                     canvas.get_announcements(cli, subj.id),
                                     cli, sync_log)

                xn_token = _ensure_xn_token(cli, subj.id)
                if xn_token:
                    try:
                        weeks = learningx.get_course_modules(cli, subj.id, xn_token)
                        upsert_weeks_and_files(session, subj, weeks, cli, sync_log)
                    except Exception:
                        log.exception("modules sync failed for course %s", subj.id)
                    try:
                        upsert_board_posts(session, subj, xn_token, cli, sync_log)
                    except Exception:
                        log.exception("board sync failed for course %s", subj.id)

                upsert_week_items(session, subj, cli)

                subj.last_synced_at = _now()
                session.add(subj)
                session.commit()

        _prune_missing_files(session)
        sync_log.status = "done"
    except Exception as e:  # noqa: BLE001
        log.exception("run_full_sync failed")
        sync_log.status = "failed"
        sync_log.error = str(e)[:500]
    finally:
        sync_log.finished_at = _now()
        session.add(sync_log)
        session.commit()
        session.refresh(sync_log)

    return sync_log
