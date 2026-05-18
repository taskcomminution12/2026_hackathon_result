"""DB 엔진 + 세션."""
from __future__ import annotations
import logging

from sqlalchemy import event, inspect, text
from sqlmodel import Session, SQLModel, create_engine

from .config import settings

log = logging.getLogger(__name__)

_is_sqlite = "sqlite" in settings.database_url

engine = create_engine(
    settings.database_url,
    echo=False,
    connect_args={"check_same_thread": False} if _is_sqlite else {},
)


# SQLite 동시성 개선 — WAL 모드 + busy_timeout
# 병렬 워커가 동시에 write 할 때 'database is locked' 회피
if _is_sqlite:
    @event.listens_for(engine, "connect")
    def _sqlite_pragmas(dbapi_conn, _):
        cur = dbapi_conn.cursor()
        cur.execute("PRAGMA journal_mode=WAL")     # 동시 read 와 write 가능
        cur.execute("PRAGMA busy_timeout=15000")   # 잠겼으면 최대 15초 대기 후 재시도
        cur.execute("PRAGMA synchronous=NORMAL")   # WAL 에선 충분히 안전
        cur.close()


def _auto_migrate() -> None:
    """간이 마이그레이션 — 모델에 있는데 테이블에 없는 컬럼을 ALTER ADD 로 추가."""
    insp = inspect(engine)
    for table_name, table in SQLModel.metadata.tables.items():
        if not insp.has_table(table_name):
            continue
        existing = {c["name"] for c in insp.get_columns(table_name)}
        for col in table.columns:
            if col.name in existing:
                continue
            # 타입은 모델 정의를 그대로 사용
            col_type = col.type.compile(engine.dialect)
            default = ""
            if col.default is not None and getattr(col.default, "is_scalar", False):
                default = f" DEFAULT {col.default.arg!r}"
            sql = f'ALTER TABLE "{table_name}" ADD COLUMN "{col.name}" {col_type}{default}'
            log.info("auto-migrate: %s", sql)
            with engine.begin() as conn:
                conn.execute(text(sql))


def init_db() -> None:
    # 모든 모델을 import 해서 SQLModel.metadata 에 테이블이 등록되게 한다.
    from . import models  # noqa: F401
    SQLModel.metadata.create_all(engine)
    _auto_migrate()


def get_session():
    with Session(engine) as session:
        yield session
