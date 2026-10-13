from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.error_handlers import register_exception_handlers
from app.api.routes import auth, books, loans, users
from app.core.config import settings
from app.db.session import init_db

DESCRIPTION = """
API REST para gerenciamento de biblioteca: usuários (bibliotecários e leitores),
acervo de livros e empréstimos com cálculo de multa por atraso.

**Autenticação:** obtenha um token em `/auth/login` (JSON) ou pelo botão *Authorize*
(e-mail no campo `username`) e envie-o no cabeçalho `Authorization: Bearer <token>`.
"""


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    init_db()
    yield


def create_app() -> FastAPI:
    app = FastAPI(title=settings.app_name, version="1.0.0", description=DESCRIPTION, lifespan=lifespan)
    register_exception_handlers(app)

    app.include_router(auth.router)
    app.include_router(users.router)
    app.include_router(books.router)
    app.include_router(loans.router)

    @app.get("/health", tags=["Saúde"], summary="Verificação de saúde")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
