"""환경설정 로딩."""
from __future__ import annotations
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=Path(__file__).parent / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    canvas_base_url: str = "https://lms.suwon.ac.kr"
    canvas_token: str = ""

    download_root: Path = Path("./downloads")
    database_url: str = "sqlite:///./lms_sync.db"

    host: str = "127.0.0.1"
    port: int = 8765

    # 카카오 알림
    kakao_rest_api_key: str = ""
    kakao_redirect_uri: str = "http://127.0.0.1:8765/api/kakao/callback"

    # 알림 — N일 전 발송 (콤마 구분, 기본 D-7/3/1/0)
    notify_days_before: str = "7,3,1,0"


settings = Settings()
settings.download_root = Path(settings.download_root).expanduser().resolve()
settings.download_root.mkdir(parents=True, exist_ok=True)
