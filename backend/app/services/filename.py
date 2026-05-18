"""파일명/경로 안전화 + 색상 배정."""
from __future__ import annotations
import hashlib
import re
from pathlib import Path

_BAD = re.compile(r'[<>:"/\\|?*\x00-\x1f]')

# 사이드바 표시용 — 과목별 색상 토큰 (7색)
COURSE_COLORS = ["blue", "purple", "teal", "orange", "pink", "amber", "emerald"]


def safe(name: str, max_len: int = 120) -> str:
    s = _BAD.sub("_", name).strip().strip(".").strip()
    return s[:max_len] or "untitled"


_DEFAULT_EXT = {"pdf": "pdf", "movie": "mp4", "file": "bin"}


def build_target_path(root: Path, subject_name: str,
                      week_position: int | None, week_title: str,
                      file_name: str,
                      content_type: str | None = None,
                      extension: str | None = None) -> Path:
    week_folder = (
        f"{int(week_position):02d}주차" if week_position
        else safe(week_title)
    )
    # 확장자 결정: 1) 파일명에 이미 있음 → 유지, 2) extension 인자, 3) content_type 매핑
    has_ext = "." in file_name and not file_name.endswith(".")
    if has_ext:
        final = file_name
    else:
        ext = extension or _DEFAULT_EXT.get((content_type or "").lower(), "bin")
        final = f"{file_name}.{ext}"
    return root / safe(subject_name) / week_folder / safe(final)


def assign_colors(course_ids: list[int]) -> dict[int, str]:
    """과목 ID 리스트를 받아서 색상이 겹치지 않게 분배.
    7과목 < 5색 이면 어쩔 수 없이 일부는 같은 색이 됨.
    동일 입력에 대해 항상 같은 결과를 보장하려면 ID 순서대로 round-robin."""
    out: dict[int, str] = {}
    sorted_ids = sorted(course_ids)
    for i, cid in enumerate(sorted_ids):
        out[cid] = COURSE_COLORS[i % len(COURSE_COLORS)]
    return out


def color_for(index: int) -> str:
    return COURSE_COLORS[index % len(COURSE_COLORS)]
