"""Canvas LMS REST 호출."""
from __future__ import annotations
import httpx
from ..config import settings

_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
       "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")


def _h() -> dict:
    return {
        "Authorization": f"Bearer {settings.canvas_token}",
        "Accept": "application/json",
    }


def make_client() -> httpx.Client:
    return httpx.Client(
        timeout=30,
        follow_redirects=True,
        headers={"User-Agent": _UA},
    )


def get_self(cli: httpx.Client) -> dict:
    r = cli.get(f"{settings.canvas_base_url}/api/v1/users/self/profile",
                headers=_h())
    r.raise_for_status()
    return r.json()


def get_active_courses(cli: httpx.Client) -> list[dict]:
    r = cli.get(
        f"{settings.canvas_base_url}/api/v1/courses",
        headers=_h(),
        params={"enrollment_state": "active", "per_page": 100},
    )
    r.raise_for_status()
    return r.json()


def get_modules(cli: httpx.Client, course_id: int) -> list[dict]:
    r = cli.get(
        f"{settings.canvas_base_url}/api/v1/courses/{course_id}/modules",
        headers=_h(),
        params={"per_page": 100},
    )
    r.raise_for_status()
    return r.json()


def get_module_items(cli: httpx.Client, course_id: int, module_id: int,
                     include_details: bool = False) -> list[dict]:
    params = {"per_page": 100}
    if include_details:
        params["include[]"] = "content_details"
    r = cli.get(
        f"{settings.canvas_base_url}/api/v1/courses/{course_id}/modules/{module_id}/items",
        headers=_h(),
        params=params,
    )
    r.raise_for_status()
    return r.json()


def get_assignment(cli: httpx.Client, course_id: int, assignment_id: int) -> dict | None:
    r = cli.get(
        f"{settings.canvas_base_url}/api/v1/courses/{course_id}/assignments/{assignment_id}",
        headers=_h(),
    )
    if r.status_code != 200:
        return None
    return r.json()


def get_page(cli: httpx.Client, course_id: int, page_url: str) -> dict | None:
    r = cli.get(
        f"{settings.canvas_base_url}/api/v1/courses/{course_id}/pages/{page_url}",
        headers=_h(),
    )
    if r.status_code != 200:
        return None
    return r.json()


def get_announcements(cli: httpx.Client, course_id: int) -> list[dict]:
    """과목 공지사항. include[]=attachments 로 첨부도 같이 받음."""
    r = cli.get(
        f"{settings.canvas_base_url}/api/v1/announcements",
        headers=_h(),
        params={
            "context_codes[]": f"course_{course_id}",
            "include[]": "attachments",
            "per_page": 100,
        },
    )
    if r.status_code != 200:
        return []
    return r.json()


def download_canvas_attachment(cli: httpx.Client, file_url: str) -> bytes | None:
    """Canvas 첨부 파일을 토큰으로 다운로드."""
    try:
        r = cli.get(file_url, headers=_h(), timeout=120)
        if r.status_code != 200:
            return None
        return r.content
    except Exception:
        return None


def get_assignments(cli: httpx.Client, course_id: int) -> list[dict]:
    """과제 목록 — 접근 권한 없으면 빈 리스트."""
    r = cli.get(
        f"{settings.canvas_base_url}/api/v1/courses/{course_id}/assignments",
        headers=_h(),
        params={"include[]": "submission", "per_page": 100},
    )
    if r.status_code != 200:
        return []
    return r.json()


def find_first_external_tool(cli: httpx.Client, course_id: int):
    """과목의 첫 ExternalTool 항목 — LTI launch에 쓸 정보 획득."""
    for m in get_modules(cli, course_id):
        for it in get_module_items(cli, course_id, m["id"]):
            if it.get("type") == "ExternalTool" and it.get("external_url"):
                return it["id"], it["content_id"], it["external_url"]
    return None
