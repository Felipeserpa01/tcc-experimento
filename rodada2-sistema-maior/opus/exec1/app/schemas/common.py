"""Schemas utilitarios compartilhados."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.core.pagination import Page, PageMeta  # re-export

__all__ = ["ORMModel", "Page", "PageMeta", "MessageResponse", "ErrorDetail", "ErrorResponse"]


class ORMModel(BaseModel):
    """Base para schemas de saida construidos a partir de objetos do ORM."""

    model_config = ConfigDict(from_attributes=True)


class MessageResponse(BaseModel):
    message: str = Field(..., description="Mensagem legivel sobre o resultado da operacao")
    detail: Any | None = None


class ErrorDetail(BaseModel):
    code: str
    message: str
    details: Any | None = None


class ErrorResponse(BaseModel):
    """Formato unico de erro retornado pela API."""

    error: ErrorDetail
