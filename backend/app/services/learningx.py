"""LearningX (lms.suwon.ac.kr/learningx) API 호출."""
from __future__ import annotations
import httpx

LX_BASE = "https://lms.suwon.ac.kr/learningx/api/v1"


def _h(xn_token: str) -> dict:
    return {
        "Authorization": f"Bearer {xn_token}",
        "Accept": "application/json",
        "X-Requested-With": "XMLHttpRequest",
    }


def get_course_modules(cli: httpx.Client, course_id: int, xn_token: str) -> list[dict]:
    """주차/자료 트리. 자료 메타에 Xinics content_id 포함."""
    r = cli.get(f"{LX_BASE}/courses/{course_id}/modules", headers=_h(xn_token))
    r.raise_for_status()
    return r.json()


def iter_assets(weeks: list[dict]):
    """주차 트리에서 commons 자료를 모두 평탄화해서 yield.
    PDF, file (zip/실습코드 등), movie 모두 포함.
    """
    for w in weeks:
        wp = w.get("week_position") or w.get("position") or 0
        wt = w.get("title") or f"week-{wp}"
        for it in w.get("module_items", []) or []:
            cd = it.get("content_data") or {}
            icd = cd.get("item_content_data") or {}
            if not icd:
                continue
            ct = (icd.get("content_type") or "").lower()
            if ct not in ("pdf", "file", "movie"):
                continue
            xid = icd.get("content_id")
            if not xid:
                continue
            file_name = icd.get("file_name") or it.get("title", "untitled")
            yield {
                "week_id": w.get("module_id") or w.get("id"),
                "week_position": wp,
                "week_title": wt,
                "title": it.get("title", ""),
                "file_name": file_name,
                "content_type": ct,                            # pdf/file/movie
                "file_size": icd.get("total_file_size"),
                "xinics_content_id": xid,
            }


# 호환 alias
iter_pdf_assets = iter_assets


def get_commons_meta(cli, xn_token: str, content_id: str) -> dict | None:
    """13자 Xinics ID로 자료 메타 가져오기. download_url, view_url, extension 등."""
    headers = _h(xn_token)
    try:
        r = cli.get(f"{LX_BASE}/commons/contents",
                    params={"content_id": content_id}, headers=headers)
        if r.status_code != 200:
            return None
        data = r.json()
        return data.get("result") or None
    except Exception:
        return None
