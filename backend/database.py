from pathlib import Path
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from sqlalchemy.pool import NullPool, QueuePool

from config import get_settings

settings = get_settings()

_BACKEND_DIR = Path(__file__).parent


def _resolve_db_url(url: str) -> str:
    """Convert sqlite:///relative.db to an absolute path anchored to backend/."""
    if url.startswith("sqlite:///") and not url.startswith("sqlite:////"):
        rel = url[len("sqlite:///"):]
        abs_path = (_BACKEND_DIR / rel).resolve()
        return f"sqlite:///{abs_path}"
    return url


_db_url = _resolve_db_url(settings.database_url)

_is_sqlite = _db_url.startswith("sqlite")

# NullPool: each request gets its own connection — no pool timeout during
# long-running pricing requests. WAL mode handles concurrent reads.
engine = create_engine(
    _db_url,
    connect_args={"check_same_thread": False, "timeout": 60} if _is_sqlite else {},
    poolclass=NullPool if _is_sqlite else QueuePool,
)

if _is_sqlite:
    @event.listens_for(engine, "connect")
    def _set_sqlite_pragmas(dbapi_conn, _):
        dbapi_conn.execute("PRAGMA journal_mode=WAL")
        dbapi_conn.execute("PRAGMA synchronous=NORMAL")
        dbapi_conn.execute("PRAGMA busy_timeout=30000")

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
