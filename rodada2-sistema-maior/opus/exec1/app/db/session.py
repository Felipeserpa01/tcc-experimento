"""Engine, sessao e dependencia de banco de dados."""

from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import get_settings

settings = get_settings()


def _build_engine() -> Engine:
    url = settings.database_url
    connect_args: dict = {}
    kwargs: dict = {"echo": settings.database_echo, "future": True}

    if url.startswith("sqlite"):
        connect_args["check_same_thread"] = False
        if ":memory:" in url or url.endswith("sqlite://"):
            kwargs["poolclass"] = StaticPool

    return create_engine(url, connect_args=connect_args, **kwargs)


engine = _build_engine()


@event.listens_for(Engine, "connect")
def _configure_sqlite(dbapi_connection, connection_record) -> None:
    """SQLite nao aplica FK por padrao: habilitamos em toda conexao."""
    module_name = type(dbapi_connection).__module__ or ""
    if "sqlite" not in module_name:
        return
    cursor = dbapi_connection.cursor()
    try:
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA journal_mode=WAL")
    finally:
        cursor.close()


SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, expire_on_commit=False)


def get_db() -> Generator[Session, None, None]:
    """Dependencia FastAPI: uma sessao por requisicao, sempre encerrada."""
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
