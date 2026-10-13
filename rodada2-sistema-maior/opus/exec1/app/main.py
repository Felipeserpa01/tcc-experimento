"""Ponto de entrada da API da clinica medica."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import get_settings
from app.core.error_handlers import register_exception_handlers
from app.core.middleware import RequestContextMiddleware

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger("clinica")

settings = get_settings()

DESCRIPTION = """
API REST para gestao de uma clinica medica de medio porte.

**Modulos**

* Autenticacao e seguranca (JWT, 5 perfis, bloqueio de conta, auditoria)
* Pacientes e convenios
* Profissionais (medicos e enfermeiros) e agenda de disponibilidade
* Agendamento de consultas, lista de espera e agenda do dia
* Prontuario, prescricoes e exames com anexo de resultados
* Faturamento com desconto de convenio
* Relatorios e indicadores

**Perfis:** `admin`, `doctor`, `nurse`, `receptionist`, `patient`.
"""


@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.is_testing:
        # Em testes o schema e criado pelas fixtures do pytest.
        logger.info("Ambiente de testes: inicializacao automatica do banco desativada.")
    else:
        from app.db.init_db import init_db

        init_db()
        logger.info("Banco de dados pronto (%s).", settings.database_url)
    yield
    logger.info("Encerrando a aplicacao.")


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description=DESCRIPTION,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    app.add_middleware(RequestContextMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID"],
    )

    register_exception_handlers(app)
    app.include_router(api_router, prefix=settings.api_v1_prefix)

    @app.get("/health", tags=["Infraestrutura"], summary="Verificacao de saude do servico")
    def health() -> dict:
        return {
            "status": "ok",
            "application": settings.app_name,
            "version": settings.app_version,
            "environment": settings.environment,
        }

    @app.get("/", tags=["Infraestrutura"], summary="Informacoes basicas da API")
    def root() -> dict:
        return {
            "application": settings.app_name,
            "version": settings.app_version,
            "docs": "/docs",
            "api_prefix": settings.api_v1_prefix,
        }

    return app


app = create_app()
