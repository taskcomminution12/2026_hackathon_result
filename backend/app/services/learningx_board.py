"""LearningX 게시판(learningx_board) API 호출."""
from __future__ import annotations
import httpx
from .learningx import LX_BASE


def _h(xn_token: str) -> dict:
    return {
        "Authorization": f"Bearer {xn_token}",
        "Accept": "application/json",
        "X-Requested-With": "XMLHttpRequest",
    }


def list_boards(cli: httpx.Client, course_id: int, xn_token: str) -> list[dict]:
    r = cli.get(f"{LX_BASE}/learningx_board/courses/{course_id}/boards",
                headers=_h(xn_token))
    if r.status_code != 200:
        return []
    data = r.json()
    if isinstance(data, dict):
        data = data.get("items") or data.get("boards") or data.get("result") or []
    return data if isinstance(data, list) else []


def list_posts(cli: httpx.Client, course_id: int, board_id: int,
               xn_token: str, per_page: int = 100) -> list[dict]:
    r = cli.get(f"{LX_BASE}/learningx_board/courses/{course_id}/boards/{board_id}/posts",
                headers=_h(xn_token), params={"per_page": per_page})
    if r.status_code != 200:
        return []
    data = r.json()
    if isinstance(data, dict):
        data = data.get("items") or data.get("posts") or []
    return data if isinstance(data, list) else []


def get_post(cli: httpx.Client, course_id: int, board_id: int,
             post_id: int, xn_token: str) -> dict | None:
    r = cli.get(
        f"{LX_BASE}/learningx_board/courses/{course_id}/boards/{board_id}/posts/{post_id}",
        headers=_h(xn_token),
    )
    if r.status_code != 200:
        return None
    return r.json()


def is_qna_board(board: dict) -> bool:
    """Q&A 류 게시판 판별 — 동기화 제외 대상."""
    btype = (board.get("type") or "").lower()
    title = (board.get("title") or "")
    if btype == "qna":
        return True
    if "Q&A" in title or "Q & A" in title or "질문" in title:
        return True
    return False
