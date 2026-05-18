"""카카오 OAuth + 메모(나에게 보내기) API.

문서:
- https://developers.kakao.com/docs/latest/ko/kakaologin/rest-api
- https://developers.kakao.com/docs/latest/ko/message/rest-api#default-template-msg-me
"""
from __future__ import annotations
import json
import logging
from datetime import datetime, timedelta
from urllib.parse import urlencode
import httpx
from sqlmodel import Session, select

from ..config import settings
from ..models import KakaoToken

log = logging.getLogger(__name__)

KAUTH = "https://kauth.kakao.com"
KAPI = "https://kapi.kakao.com"
SCOPE = "talk_message"


def auth_url() -> str:
    """OAuth 2.0 인증 페이지로 이동시킬 URL."""
    if not settings.kakao_rest_api_key:
        raise RuntimeError("KAKAO_REST_API_KEY 가 설정되지 않았습니다.")
    q = urlencode({
        "response_type": "code",
        "client_id": settings.kakao_rest_api_key,
        "redirect_uri": settings.kakao_redirect_uri,
        "scope": SCOPE,
        "prompt": "login",   # 매번 다시 로그인·동의 받도록 강제
    })
    return f"{KAUTH}/oauth/authorize?{q}"


def exchange_code(code: str) -> dict:
    r = httpx.post(
        f"{KAUTH}/oauth/token",
        data={
            "grant_type": "authorization_code",
            "client_id": settings.kakao_rest_api_key,
            "redirect_uri": settings.kakao_redirect_uri,
            "code": code,
        },
        timeout=20,
    )
    r.raise_for_status()
    return r.json()


def refresh(refresh_token: str) -> dict:
    r = httpx.post(
        f"{KAUTH}/oauth/token",
        data={
            "grant_type": "refresh_token",
            "client_id": settings.kakao_rest_api_key,
            "refresh_token": refresh_token,
        },
        timeout=20,
    )
    r.raise_for_status()
    return r.json()


def save_token(session: Session, token_payload: dict, fallback_refresh: str | None = None) -> KakaoToken:
    """토큰 응답을 DB에 upsert."""
    now = datetime.utcnow()
    expires_in = int(token_payload.get("expires_in", 21600))
    refresh_expires = token_payload.get("refresh_token_expires_in")
    refresh_token = token_payload.get("refresh_token") or fallback_refresh
    if not refresh_token:
        raise RuntimeError("refresh_token이 응답에 없음")

    existing = session.get(KakaoToken, 1)
    kw = dict(
        access_token=token_payload["access_token"],
        refresh_token=refresh_token,
        expires_at=now + timedelta(seconds=expires_in),
        refresh_expires_at=(now + timedelta(seconds=refresh_expires))
                          if refresh_expires else None,
        scope=token_payload.get("scope", SCOPE),
        updated_at=now,
    )
    if existing:
        for k, v in kw.items():
            setattr(existing, k, v)
        session.add(existing)
        out = existing
    else:
        out = KakaoToken(id=1, **kw)
        session.add(out)
    session.commit()
    return out


def get_valid_token(session: Session) -> str | None:
    """저장된 access_token. 만료 임박 시 자동 갱신."""
    row = session.get(KakaoToken, 1)
    if not row:
        return None
    if row.expires_at - datetime.utcnow() < timedelta(minutes=5):
        try:
            payload = refresh(row.refresh_token)
            row = save_token(session, payload, fallback_refresh=row.refresh_token)
        except Exception as e:
            log.warning("kakao refresh failed: %s", e)
            return None
    return row.access_token


def disconnect(session: Session) -> None:
    row = session.get(KakaoToken, 1)
    if row:
        session.delete(row)
        session.commit()


def send_memo(access_token: str, *, title: str, body: str,
              link_url: str | None = None) -> bool:
    """카톡 '나에게 보내기' — text 템플릿."""
    template = {
        "object_type": "text",
        "text": f"{title}\n\n{body}"[:200],
        "link": {"web_url": link_url or "https://lms.suwon.ac.kr",
                 "mobile_web_url": link_url or "https://lms.suwon.ac.kr"},
        "button_title": "LMS 열기",
    }
    r = httpx.post(
        f"{KAPI}/v2/api/talk/memo/default/send",
        headers={"Authorization": f"Bearer {access_token}"},
        data={"template_object": json.dumps(template, ensure_ascii=False)},
        timeout=20,
    )
    if r.status_code != 200:
        log.warning("kakao send fail %s: %s", r.status_code, r.text[:200])
        return False
    return True


def is_connected(session: Session) -> bool:
    return session.get(KakaoToken, 1) is not None
