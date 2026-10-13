import logging

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError

from app.core.exceptions import AppError

logger = logging.getLogger(__name__)


def _error(status_code: int, detail: str, code: str, headers: dict[str, str] | None = None) -> JSONResponse:
    return JSONResponse(status_code=status_code, content={"detail": detail, "code": code}, headers=headers)


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def handle_app_error(_: Request, exc: AppError) -> JSONResponse:
        return _error(exc.status_code, exc.detail, exc.code, exc.headers)

    @app.exception_handler(IntegrityError)
    async def handle_integrity_error(_: Request, exc: IntegrityError) -> JSONResponse:
        logger.warning("Violação de integridade não tratada: %s", exc.orig)
        return _error(
            status.HTTP_409_CONFLICT,
            "A operação viola uma restrição de integridade dos dados",
            "integrity_error",
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_error(request: Request, _: Exception) -> JSONResponse:
        logger.exception("Erro inesperado em %s %s", request.method, request.url.path)
        return _error(status.HTTP_500_INTERNAL_SERVER_ERROR, "Erro interno do servidor", "internal_error")
