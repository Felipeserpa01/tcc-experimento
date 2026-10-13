"""Contexto por requisicao (IP, user-agent, request id) para a auditoria."""

from __future__ import annotations

import uuid
from contextvars import ContextVar
from dataclasses import dataclass, field


@dataclass
class RequestContext:
    request_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    ip_address: str | None = None
    user_agent: str | None = None
    method: str | None = None
    path: str | None = None


_request_context: ContextVar[RequestContext | None] = ContextVar("request_context", default=None)


def set_request_context(context: RequestContext):
    return _request_context.set(context)


def reset_request_context(token) -> None:
    _request_context.reset(token)


def get_request_context() -> RequestContext:
    context = _request_context.get()
    if context is None:
        context = RequestContext()
    return context
