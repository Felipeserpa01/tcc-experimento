"""Middleware ASGI: contexto da requisição e cabeçalhos de segurança."""

import re
import uuid

from starlette.datastructures import MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.core.context import client_ip_var, request_id_var

_REQUEST_ID_RE = re.compile(r"^[A-Za-z0-9-]{8,64}$")

_SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    "Cache-Control": "no-store",
}


class RequestContextMiddleware:
    """Registra IP/ID da requisição em ``ContextVar`` e adiciona cabeçalhos de segurança."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        incoming = dict(scope.get("headers") or []).get(b"x-request-id", b"").decode("latin-1")
        request_id = incoming if _REQUEST_ID_RE.match(incoming) else uuid.uuid4().hex
        client = scope.get("client")
        ip_token = client_ip_var.set(client[0] if client else None)
        rid_token = request_id_var.set(request_id)

        async def send_with_headers(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = MutableHeaders(scope=message)
                headers["X-Request-ID"] = request_id
                for name, value in _SECURITY_HEADERS.items():
                    if name not in headers:
                        headers[name] = value
            await send(message)

        try:
            await self.app(scope, receive, send_with_headers)
        finally:
            client_ip_var.reset(ip_token)
            request_id_var.reset(rid_token)
