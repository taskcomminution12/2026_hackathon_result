"""Canvas → LearningX LTI launch 흐름."""
from __future__ import annotations
import re
import httpx
from ..config import settings


def get_xn_api_token(cli: httpx.Client, course_id: int,
                     module_item_id: int = 0, tool_id: int = 0,
                     external_url: str = "") -> str | None:
    """LTI launch 흐름으로 xn_api_token 발급. 실패 시 None.

    module_item_id 가 0 이면 navigation 도구로 launch (게시판처럼 도구 자체 진입).
    """
    try:
        params = {"id": tool_id}
        if module_item_id:
            params.update({
                "launch_type": "module_item",
                "module_item_id": module_item_id,
                "url": external_url,
            })
        r = cli.get(
            f"{settings.canvas_base_url}/api/v1/courses/{course_id}/external_tools/sessionless_launch",
            headers={
                "Authorization": f"Bearer {settings.canvas_token}",
                "Accept": "application/json",
            },
            params=params,
        )
        r.raise_for_status()
        launch_url = r.json()["url"]

        r = cli.get(launch_url, headers={"Accept": "text/html"})
        m = re.search(r'<form[^>]*action="([^"]+)"[^>]*>(.*?)</form>',
                      r.text, re.S)
        if not m:
            return None
        inputs = dict(re.findall(
            r'<input[^>]*name="([^"]+)"[^>]*value="([^"]*)"',
            m.group(2),
        ))
        cli.post(m.group(1), data=inputs, headers={"Accept": "text/html"})

        return cli.cookies.get("xn_api_token")
    except Exception:
        return None
