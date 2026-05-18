from __future__ import annotations
from fastapi import APIRouter, HTTPException
from ..services import canvas

router = APIRouter()


@router.get("/me")
def me():
    """현재 로그인 사용자 — 첫 인증/대시보드 인사말에 씀."""
    try:
        with canvas.make_client() as cli:
            data = canvas.get_self(cli)
        return {
            "id": data.get("id"),
            "name": data.get("name"),
            "login_id": data.get("login_id"),       # 학번
            "email": data.get("primary_email"),
            "avatar_url": data.get("avatar_url"),
        }
    except Exception as e:
        raise HTTPException(401, f"Canvas 인증 실패: {e}")
