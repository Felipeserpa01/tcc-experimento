"""Tratamento centralizado de erros -> respostas HTTP padronizadas."""

from __future__ import annotations

import logging

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError as PydanticValidationError
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.config import get_settings
from app.core.context import get_request_context
from app.core.exceptions import AppError

logger = logging.getLogger("clinica.errors")
settings = get_settings()

#: Codigos HTTP -> codigo de erro textual da API.
_HTTP_ERROR_CODES = {
    400: "bad_request",
    401: "authentication_failed",
    403: "permission_denied",
    404: "not_found",
    405: "method_not_allowed",
    409: "conflict",
    413: "payload_too_large",
    415: "unsupported_media_type",
    422: "validation_error",
    429: "too_many_requests",
    500: "internal_error",
}


def _build_response(
    status_code: int, code: str, message: str, details=None, headers: dict | None = None
) -> JSONResponse:
    payload = {"error": {"code": code, "message": message}}
    if details is not None:
        payload["error"]["details"] = details
    payload["error"]["request_id"] = get_request_context().request_id
    return JSONResponse(status_code=status_code, content=payload, headers=headers)


def _format_validation_errors(errors: list[dict]) -> list[dict]:
    """Converte erros do Pydantic em mensagens objetivas por campo."""
    formatted: list[dict] = []
    for error in errors:
        location = [str(part) for part in error.get("loc", [])]
        # Remove o prefixo da origem (body/query/path) para facilitar a leitura.
        field = ".".join(location[1:]) if len(location) > 1 else ".".join(location)
        formatted.append(
            {
                "field": field or "payload",
                "location": location[0] if location else "body",
                "message": error.get("msg", "Valor invalido."),
                "type": error.get("type", "value_error"),
            }
        )
    return formatted


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def handle_app_error(request: Request, exc: AppError) -> JSONResponse:
        if exc.status_code >= 500:
            logger.exception("Erro de aplicacao nao tratado: %s", exc.message)
        else:
            logger.info("%s: %s", exc.error_code, exc.message)
        headers = {"WWW-Authenticate": "Bearer"} if exc.status_code == 401 else None
        return _build_response(
            exc.status_code, exc.error_code, exc.message, exc.details, headers
        )

    @app.exception_handler(RequestValidationError)
    async def handle_request_validation(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        return _build_response(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "validation_error",
            "Os dados enviados sao invalidos. Verifique os campos indicados.",
            _format_validation_errors(exc.errors()),
        )

    @app.exception_handler(PydanticValidationError)
    async def handle_pydantic_validation(
        request: Request, exc: PydanticValidationError
    ) -> JSONResponse:
        return _build_response(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "validation_error",
            "Os dados enviados sao invalidos.",
            _format_validation_errors(exc.errors()),
        )

    @app.exception_handler(StarletteHTTPException)
    async def handle_http_exception(
        request: Request, exc: StarletteHTTPException
    ) -> JSONResponse:
        code = _HTTP_ERROR_CODES.get(exc.status_code, "http_error")
        message = exc.detail if isinstance(exc.detail, str) else "Erro na requisicao."
        return _build_response(exc.status_code, code, message, headers=exc.headers)

    @app.exception_handler(IntegrityError)
    async def handle_integrity_error(request: Request, exc: IntegrityError) -> JSONResponse:
        logger.warning("Violacao de integridade: %s", exc)
        return _build_response(
            status.HTTP_409_CONFLICT,
            "integrity_error",
            "A operacao viola uma restricao de integridade do banco de dados.",
            {"hint": "Verifique campos unicos e relacionamentos obrigatorios."},
        )

    @app.exception_handler(SQLAlchemyError)
    async def handle_database_error(request: Request, exc: SQLAlchemyError) -> JSONResponse:
        logger.exception("Erro de banco de dados: %s", exc)
        return _build_response(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "database_error",
            "Erro ao acessar o banco de dados.",
        )

    @app.exception_handler(ValueError)
    async def handle_value_error(request: Request, exc: ValueError) -> JSONResponse:
        # Validadores de dominio (CPF, telefone, UF) levantam ValueError.
        return _build_response(
            status.HTTP_422_UNPROCESSABLE_ENTITY, "validation_error", str(exc)
        )

    @app.exception_handler(Exception)
    async def handle_unexpected(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Erro inesperado: %s", exc)
        message = "Erro interno inesperado."
        details = {"exception": repr(exc)} if settings.debug else None
        return _build_response(
            status.HTTP_500_INTERNAL_SERVER_ERROR, "internal_error", message, details
        )
