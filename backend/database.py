from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

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

engine = create_engine(
    _db_url,
    connect_args={"check_same_thread": False} if _db_url.startswith("sqlite") else {},
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
