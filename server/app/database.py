"""数据库引擎与会话。SQLite WAL 模式；时间统一存 naive UTC（见 02 文档 §5）。"""
import os

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker


class Base(DeclarativeBase):
    pass


def _ensure_sqlite_dir(url: str) -> None:
    # sqlite:///./data/app.db → 确保 ./data 目录存在
    prefix = "sqlite:///"
    if url.startswith(prefix):
        path = url[len(prefix):]
        if path and path != ":memory:":
            d = os.path.dirname(path)
            if d:
                os.makedirs(d, exist_ok=True)


def make_engine(url: str):
    _ensure_sqlite_dir(url)
    engine = create_engine(
        url,
        connect_args={"check_same_thread": False} if url.startswith("sqlite") else {},
    )

    @event.listens_for(engine, "connect")
    def _set_sqlite_pragma(dbapi_conn, _record):  # pragma: no cover
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.close()

    return engine


settings_url = os.environ.get("DATABASE_URL", "sqlite:///./data/app.db")
engine = make_engine(settings_url)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
