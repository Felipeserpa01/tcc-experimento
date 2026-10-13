from collections.abc import Iterator
from typing import Any

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings
from app.db.base import Base
from app.utils.text import normalize_text


def build_engine(url: str, **kwargs: Any) -> Engine:
    connect_args: dict[str, Any] = {}
    if url.startswith("sqlite"):
        # O FastAPI executa rotas síncronas em threads diferentes.
        connect_args["check_same_thread"] = False

    engine = create_engine(url, connect_args=connect_args, **kwargs)

    if engine.dialect.name == "sqlite":

        @event.listens_for(engine, "connect")
        def _configure_sqlite(dbapi_connection: Any, _: Any) -> None:
            cursor = dbapi_connection.cursor()
            # O SQLite vem com chaves estrangeiras desativadas por padrão.
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()
            # lower() do SQLite só trata ASCII; esta função permite buscar
            # "jose saramago" e encontrar "José Saramago".
            dbapi_connection.create_function("normalize_text", 1, normalize_text, deterministic=True)

    return engine


def create_session_factory(bind: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=bind, autoflush=False, expire_on_commit=False)


engine = build_engine(settings.database_url)
SessionLocal = create_session_factory(engine)


def init_db(bind: Engine | None = None) -> None:
    import app.models  # noqa: F401  (registra os modelos no metadata)

    Base.metadata.create_all(bind=bind or engine)


def get_db() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
