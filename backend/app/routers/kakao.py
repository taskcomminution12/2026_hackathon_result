from __future__ import annotations
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse, HTMLResponse
from sqlmodel import Session

from ..db import get_session
from ..models import KakaoToken
from ..services import kakao, notify
from ._serial import utc_iso

router = APIRouter()


@router.get("/kakao/status")
def status(session: Session = Depends(get_session)):
    row = session.get(KakaoToken, 1)
    if not row:
        return {"connected": False}
    return {
        "connected": True,
        "scope": row.scope,
        "expires_at": utc_iso(row.expires_at),
        "updated_at": utc_iso(row.updated_at),
    }


@router.get("/kakao/login")
def login():
    """카카오 인증 페이지로 리다이렉트."""
    try:
        return RedirectResponse(kakao.auth_url())
    except RuntimeError as e:
        raise HTTPException(400, str(e))


@router.get("/kakao/callback")
def callback(code: str = Query(""), error: str = Query(""),
             session: Session = Depends(get_session)):
    """카카오 OAuth 콜백 — 토큰 받아서 저장."""
    if error or not code:
        return HTMLResponse(f"<h2>카카오 인증 실패</h2><p>{error or 'code 없음'}</p>", 400)
    try:
        payload = kakao.exchange_code(code)
        kakao.save_token(session, payload)
    except Exception as e:
        return HTMLResponse(f"<h2>토큰 교환 실패</h2><pre>{e}</pre>", 500)
    return HTMLResponse(
        """<!doctype html><meta charset="utf-8">
        <title>카카오 연결 완료</title>
        <style>body{font-family:Inter,system-ui,sans-serif;display:grid;place-items:center;height:100vh;margin:0;background:#F5F7FB;color:#0F172A}
        .card{background:#fff;padding:32px 40px;border-radius:14px;box-shadow:0 12px 32px rgba(0,0,0,.08);text-align:center}
        h2{margin:0 0 8px;font-family:'Inter Tight',Inter}
        a{color:#2563EB;font-weight:600;text-decoration:none}</style>
        <div class="card">
          <h2>카카오톡 연결 완료</h2>
          <p>이제 과제 마감이 가까워지면 본인 카카오톡으로 알림이 옵니다.</p>
          <p><a href="/settings">설정으로 돌아가기</a></p>
        </div>"""
    )


@router.post("/kakao/disconnect")
def disconnect(session: Session = Depends(get_session)):
    kakao.disconnect(session)
    return {"connected": False}


@router.post("/kakao/test")
def test_send(session: Session = Depends(get_session)):
    """현재 토큰으로 테스트 메시지 발송."""
    token = kakao.get_valid_token(session)
    if not token:
        raise HTTPException(400, "카카오 연결 필요")
    ok = kakao.send_memo(
        token,
        title="[수원대 LMS Sync] 테스트",
        body="알림 연결이 정상입니다. 과제 마감이 임박하면 자동으로 알려드립니다.",
        link_url="https://lms.suwon.ac.kr",
    )
    return {"ok": ok}


@router.post("/kakao/notify-now")
def notify_now():
    """알림 잡 즉시 실행 (테스트용)."""
    notify.run_once()
    return {"ok": True}
