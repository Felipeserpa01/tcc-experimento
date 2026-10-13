"""Tratamento centralizado de erros.

Formato padrão de resposta de erro::

    {"error": {"code": "...", "message": "...", "details": ...}}
"""

import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.exceptions import AppError, AuthenticationError

logger = logging.getLogger(__name__)

_VALIDATION_MESSAGES: dict[str, str] = {
    "missing": "Campo obrigatório.",
    "string_type": "Deve ser um texto.",
    "string_too_short": "Deve ter no mínimo {min_length} caractere(s).",
    "string_too_long": "Deve ter no máximo {max_length} caractere(s).",
    "string_pattern_mismatch": "Formato inválido.",
    "int_type": "Deve ser um número inteiro.",
    "int_parsing": "Deve ser um número inteiro.",
    "int_from_float": "Deve ser um número inteiro.",
    "float_type": "Deve ser um número.",
    "float_parsing": "Deve ser um número.",
    "decimal_type": "Deve ser um número decimal.",
    "decimal_parsing": "Deve ser um número decimal.",
    "decimal_max_digits": "Deve ter no máximo {max_digits} dígito(s).",
    "decimal_max_places": "Deve ter no máximo {decimal_places} casa(s) decimal(is).",
    "decimal_whole_digits": "Deve ter no máximo {whole_digits} dígito(s) antes da vírgula.",
    "greater_than": "Deve ser maior que {gt}.",
    "greater_than_equal": "Deve ser maior ou igual a {ge}.",
    "less_than": "Deve ser menor que {lt}.",
    "less_than_equal": "Deve ser menor ou igual a {le}.",
    "bool_type": "Deve ser verdadeiro ou falso.",
    "bool_parsing": "Deve ser verdadeiro ou falso.",
    "date_type": "Data inválida. Use o formato AAAA-MM-DD.",
    "date_parsing": "Data inválida. Use o formato AAAA-MM-DD.",
    "date_from_datetime_parsing": "Data inválida. Use o formato AAAA-MM-DD.",
    "date_from_datetime_inexact": "Informe apenas a data (AAAA-MM-DD).",
    "datetime_type": "Data/hora inválida. Use o formato AAAA-MM-DDTHH:MM.",
    "datetime_parsing": "Data/hora inválida. Use o formato AAAA-MM-DDTHH:MM.",
    "datetime_from_date_parsing": "Data/hora inválida. Use o formato AAAA-MM-DDTHH:MM.",
    "time_type": "Horário inválido. Use o formato HH:MM.",
    "time_parsing": "Horário inválido. Use o formato HH:MM.",
    "enum": "Valor inválido. Opções permitidas: {expected}.",
    "literal_error": "Valor inválido. Opções permitidas: {expected}.",
    "extra_forbidden": "Campo não permitido.",
    "list_type": "Deve ser uma lista.",
    "too_short": "Deve conter no mínimo {min_length} item(ns).",
    "too_long": "Deve conter no máximo {max_length} item(ns).",
    "dict_type": "Deve ser um objeto.",
    "model_type": "Deve ser um objeto.",
    "model_attributes_type": "Deve ser um objeto.",
    "json_invalid": "JSON malformado.",
    "json_type": "JSON inválido.",
}


def _error_body(code: str, message: str, details: Any = None) -> dict[str, Any]:
    body: dict[str, Any] = {"code": code, "message": message}
    if details is not None:
        body["details"] = details
    return {"error": body}


def _translate_validation_error(error: dict[str, Any]) -> dict[str, Any]:
    loc = list(error.get("loc", ()))
    location = str(loc[0]) if loc and loc[0] in ("body", "query", "path", "header", "cookie") else "body"
    field_parts = [str(part) for part in (loc[1:] if loc and loc[0] == location else loc)]
    error_type = error.get("type", "")
    ctx = error.get("ctx") or {}

    if error_type in ("value_error", "assertion_error"):
        raw = str(ctx.get("error", error.get("msg", "")))
        if "email" in raw.lower() and ("valid" in raw.lower() or "@" in raw):
            message = "E-mail inválido."
        else:
            message = raw.removeprefix("Value error, ").removeprefix("Assertion failed, ")
    else:
        template = _VALIDATION_MESSAGES.get(error_type)
        try:
            message = template.format(**ctx) if template else str(error.get("msg", "Valor inválido."))
        except (KeyError, IndexError):
            message = str(error.get("msg", "Valor inválido."))

    return {"location": location, "field": ".".join(field_parts) or None, "message": message, "type": error_type}


async def app_error_handler(_: Request, exc: AppError) -> JSONResponse:
    headers = {"WWW-Authenticate": "Bearer"} if isinstance(exc, AuthenticationError) else None
    return JSONResponse(
        status_code=exc.status_code,
        content=_error_body(exc.code, exc.message, exc.details),
        headers=headers,
    )


async def validation_error_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
    details = [_translate_validation_error(err) for err in exc.errors()]
    return JSONResponse(
        status_code=422,
        content=_error_body("dados_invalidos", "Os dados enviados são inválidos.", details),
    )


_HTTP_CODES = {
    401: "nao_autenticado",
    403: "acesso_negado",
    404: "nao_encontrado",
    405: "metodo_nao_permitido",
    413: "requisicao_muito_grande",
    415: "tipo_de_midia_nao_suportado",
}

_HTTP_MESSAGES = {
    404: "Recurso não encontrado.",
    405: "Método HTTP não permitido para este recurso.",
}


async def http_error_handler(_: Request, exc: StarletteHTTPException) -> JSONResponse:
    code = _HTTP_CODES.get(exc.status_code, "erro_http")
    message = _HTTP_MESSAGES.get(exc.status_code, str(exc.detail))
    return JSONResponse(
        status_code=exc.status_code,
        content=_error_body(code, message),
        headers=getattr(exc, "headers", None),
    )


async def integrity_error_handler(_: Request, exc: IntegrityError) -> JSONResponse:
    logger.warning("Violação de integridade: %s", exc.orig)
    return JSONResponse(
        status_code=409,
        content=_error_body(
            "conflito",
            "A operação viola uma restrição de integridade (registro duplicado ou referência inválida).",
        ),
    )


async def unhandled_error_handler(_: Request, exc: Exception) -> JSONResponse:
    logger.exception("Erro não tratado: %s", exc)
    return JSONResponse(
        status_code=500,
        content=_error_body("erro_interno", "Erro interno do servidor. Tente novamente mais tarde."),
    )


def register_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(AppError, app_error_handler)  # type: ignore[arg-type]
    app.add_exception_handler(RequestValidationError, validation_error_handler)  # type: ignore[arg-type]
    app.add_exception_handler(StarletteHTTPException, http_error_handler)  # type: ignore[arg-type]
    app.add_exception_handler(IntegrityError, integrity_error_handler)  # type: ignore[arg-type]
    app.add_exception_handler(Exception, unhandled_error_handler)
