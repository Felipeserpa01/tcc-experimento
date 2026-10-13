import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes import auth, books, loans, users
from app.core.config import settings
from app.core.exceptions import register_exception_handlers
from app.db.base import Base
from app.db.session import SessionLocal, engine
from app.services import user_service

logging.basicConfig(level=logging.INFO)


def init_db() -> None:
    import app.models  # noqa: F401  (registra os modelos no metadata)

    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        user_service.ensure_first_librarian(db)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    init_db()
    yield


def create_app(*, initialize_database: bool = True) -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        version="1.0.0",
        description="API REST para gerenciamento de biblioteca: usuários, livros e empréstimos.",
        lifespan=lifespan if initialize_database else None,
    )
    register_exception_handlers(app)

    app.include_router(auth.router)
    app.include_router(users.router)
    app.include_router(books.router)
    app.include_router(loans.router)

    @app.get("/health", tags=["Saúde"])
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
