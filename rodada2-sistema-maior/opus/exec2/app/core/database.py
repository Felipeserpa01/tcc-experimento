"""Conexão com o banco SQLite via SQLAlchemy ORM."""

from collections.abc import Iterator

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import get_settings


class Base(DeclarativeBase):
    """Classe base de todos os modelos ORM."""


_engine: Engine | None = None
_session_factory: sessionmaker[Session] | None = None


def _configure_sqlite_connection(dbapi_connection, _connection_record) -> None:
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.execute("PRAGMA busy_timeout=5000")
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.close()


def create_db_engine(url: str, *, echo: bool = False) -> Engine:
    kwargs: dict = {"echo": echo}
    is_sqlite = url.startswith("sqlite")
    if is_sqlite:
        kwargs["connect_args"] = {"check_same_thread": False}
        if url in ("sqlite://", "sqlite:///:memory:"):
            kwargs["poolclass"] = StaticPool
    engine = create_engine(url, **kwargs)
    if is_sqlite:
        event.listen(engine, "connect", _configure_sqlite_connection)
    return engine


def set_engine(engine: Engine) -> None:
    """Define o engine global (usado na inicialização e nos testes)."""
    global _engine, _session_factory
    _engine = engine
    _session_factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_engine() -> Engine:
    if _engine is None:
        settings = get_settings()
        set_engine(create_db_engine(settings.database_url, echo=settings.database_echo))
    assert _engine is not None
    return _engine


def get_session_factory() -> sessionmaker[Session]:
    get_engine()
    assert _session_factory is not None
    return _session_factory


def get_db() -> Iterator[Session]:
    """Dependência FastAPI: uma sessão por requisição, sempre fechada ao final."""
    session = get_session_factory()()
    try:
        yield session
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def init_db() -> None:
    """Cria as tabelas que ainda não existem."""
    import app.models  # noqa: F401  (registra todos os modelos no metadata)

    Base.metadata.create_all(bind=get_engine())
