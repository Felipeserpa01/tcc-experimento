"""Variáveis de contexto por requisição (IP do cliente e ID da requisição)."""

from contextvars import ContextVar

client_ip_var: ContextVar[str | None] = ContextVar("client_ip", default=None)
request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)
