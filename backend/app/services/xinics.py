"""Xinics 다운로드.

신형: LearningX commons/contents API → download_url 직접 사용.
구형: xn_media_content2013 query (PDF 전용 폴백).
"""
from __future__ import annotations
import hashlib
from pathlib import Path
from urllib.parse import quote
import httpx


def build_legacy_pdf_url(content_id: str, file_name: str) -> str:
    """폴백 — xn_media_content2013 직접 호출 (PDF만)."""
    base_name = file_name.rsplit(".", 1)[0] if "." in file_name else file_name
    return (
        "https://xinics.suwon.ac.kr/index.php"
        "?module=xn_media_content2013"
        "&act=dispXn_media_content2013DownloadWebFile"
        "&site_id=suwonl1011"
        f"&content_id={content_id}"
        "&web_storage_id=5"
        "&file_subpath=" + quote("contents\\web_files\\original.pdf", safe="") +
        "&file_name=" + quote(base_name, safe="")
    )


# 호환 alias
build_url = build_legacy_pdf_url


def sha256_of(path: Path, chunk: int = 1024 * 1024) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            b = f.read(chunk)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def _accept_content(content: bytes, content_type: str) -> bool:
    """다운받은 바이트가 의도한 자료인지 빠른 시그니처 체크."""
    ct = (content_type or "").lower()
    if not content:
        return False
    if ct == "pdf":
        return content[:4] == b"%PDF"
    if ct == "file":
        # zip / 7z / pptx(zip) 등 — PK 시그니처 또는 이진 그냥 통과
        return True
    if ct == "movie":
        # mp4 등 — 너무 작으면 에러 페이지일 가능성
        return len(content) > 1024
    return True


def download_via_url(cli: httpx.Client, url: str, target: Path,
                     expected_type: str = "file") -> tuple[str, int, str | None]:
    """직접 download URL로 받기. 보통 commons API의 download_url을 받음.
    반환: (status, size, sha256)  status: ok | skip | fail"""
    target.parent.mkdir(parents=True, exist_ok=True)
    try:
        r = cli.get(url, headers={"Referer": "https://xinics.suwon.ac.kr/"},
                    timeout=180)
    except Exception:
        return "fail", 0, None

    if r.status_code != 200:
        return "fail", 0, None
    if not _accept_content(r.content, expected_type):
        return "fail", 0, None

    new_hash = hashlib.sha256(r.content).hexdigest()
    if target.exists() and sha256_of(target) == new_hash:
        return "skip", target.stat().st_size, new_hash

    target.write_bytes(r.content)
    return "ok", len(r.content), new_hash


def download(cli: httpx.Client, content_id: str, file_name: str,
             target: Path) -> tuple[str, int, str | None]:
    """레거시 PDF 전용 — 호환 유지."""
    return download_via_url(cli, build_legacy_pdf_url(content_id, file_name),
                            target, expected_type="pdf")
