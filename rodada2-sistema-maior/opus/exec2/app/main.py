"""Ponto de entrada da aplicação FastAPI."""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.api.router import api_router
from app.core.config import get_settings
from app.core.database import get_session_factory, init_db
from app.core.error_handlers import register_error_handlers
from app.core.logging import configure_logging
from app.core.middleware import RequestContextMiddleware
from app.services.user_service import UserService

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    init_db()
    with get_session_factory()() as session:
        if UserService(session).ensure_initial_admin():
            logger.info("Administrador inicial criado a partir das variáveis de ambiente.")
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.log_level)

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description=(
            "API de gestão de clínica médica: autenticação JWT com 5 perfis, pacientes, profissionais, "
            "agendamento com lista de espera, prontuário, prescrições, exames, faturamento e relatórios."
        ),
        lifespan=lifespan,
        docs_url="/docs" if settings.docs_enabled else None,
        redoc_url="/redoc" if settings.docs_enabled else None,
        openapi_url="/openapi.json" if settings.docs_enabled else None,
    )

    app.add_middleware(RequestContextMiddleware)
    if settings.cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_origins,
            allow_credentials=True,
            allow_methods=["GET", "POST", "PATCH", "DELETE"],
            allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
        )

    register_error_handlers(app)
    app.include_router(api_router, prefix=settings.api_prefix)

    @app.get("/health", tags=["Infraestrutura"], summary="Verificação de saúde")
    def health() -> dict[str, str]:
        with get_session_factory()() as session:
            session.execute(text("SELECT 1"))
        return {"status": "ok", "version": settings.app_version}

    return app


app = create_app()
