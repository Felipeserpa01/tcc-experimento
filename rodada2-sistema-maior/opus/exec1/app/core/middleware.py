"""Middlewares: contexto de requisicao e log de acesso."""

from __future__ import annotations

import logging
import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from app.core.context import RequestContext, reset_request_context, set_request_context

logger = logging.getLogger("clinica.access")


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Popula o contexto usado pela auditoria e adiciona o cabecalho X-Request-ID."""

    async def dispatch(self, request: Request, call_next):
        client_host = request.client.host if request.client else None
        forwarded = request.headers.get("x-forwarded-for")
        ip_address = forwarded.split(",")[0].strip() if forwarded else client_host

        context = RequestContext(
            ip_address=ip_address,
            user_agent=request.headers.get("user-agent"),
            method=request.method,
            path=request.url.path,
        )
        token = set_request_context(context)
        started = time.perf_counter()
        try:
            response = await call_next(request)
        finally:
            elapsed_ms = (time.perf_counter() - started) * 1000
            reset_request_context(token)
            logger.info(
                "%s %s - %.1fms [%s]",
                request.method,
                request.url.path,
                elapsed_ms,
                context.request_id,
            )
        response.headers["X-Request-ID"] = context.request_id
        return response
