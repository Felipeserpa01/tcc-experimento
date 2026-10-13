from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes import auth, books, loans, users
from app.core.config import settings
from app.core.exceptions import register_exception_handlers
from app.db.session import init_db

DESCRIPTION = """
API REST para gerenciamento de biblioteca.

* **Leitores** se cadastram em `/auth/register`, consultam o acervo e seus empréstimos.
* **Bibliotecários** gerenciam livros, usuários, empréstimos e devoluções.

Para testar pelo Swagger, faça login no botão **Authorize** usando o e-mail no campo *username*.
"""


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    init_db()
    yield


def create_app() -> FastAPI:
    app = FastAPI(title=settings.APP_NAME, version="1.0.0", description=DESCRIPTION, lifespan=lifespan)
    register_exception_handlers(app)

    app.include_router(auth.router)
    app.include_router(users.router)
    app.include_router(books.router)
    app.include_router(loans.router)

    @app.get("/health", tags=["Status"], summary="Verificação de saúde")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
