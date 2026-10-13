"""Paginacao, ordenacao e envelope padrao de listagem."""

from __future__ import annotations

from math import ceil
from typing import Generic, Sequence, TypeVar

from fastapi import Query
from pydantic import BaseModel, Field

from app.core.config import get_settings
from app.core.exceptions import BadRequestError

T = TypeVar("T")

_settings = get_settings()


class PageMeta(BaseModel):
    total: int = Field(..., description="Total de registros encontrados")
    page: int = Field(..., description="Pagina atual (1-based)")
    size: int = Field(..., description="Tamanho da pagina")
    pages: int = Field(..., description="Quantidade total de paginas")
    has_next: bool
    has_previous: bool


class Page(BaseModel, Generic[T]):
    items: list[T]
    meta: PageMeta

    @classmethod
    def create(cls, items: Sequence[T], total: int, page: int, size: int) -> "Page[T]":
        pages = ceil(total / size) if size else 0
        return cls(
            items=list(items),
            meta=PageMeta(
                total=total,
                page=page,
                size=size,
                pages=pages,
                has_next=page < pages,
                has_previous=page > 1 and total > 0,
            ),
        )


class PaginationParams:
    """Dependencia de paginacao/ordenacao reutilizada em todas as listagens."""

    def __init__(
        self,
        page: int = Query(1, ge=1, description="Pagina desejada (1-based)"),
        size: int = Query(
            _settings.default_page_size,
            ge=1,
            le=_settings.max_page_size,
            description="Quantidade de itens por pagina",
        ),
        sort_by: str | None = Query(None, description="Campo usado na ordenacao"),
        sort_order: str = Query("desc", pattern="^(?:asc|desc|ASC|DESC)$", description="asc ou desc"),
    ) -> None:
        self.page = page
        self.size = min(size, _settings.max_page_size)
        self.sort_by = sort_by
        self.sort_order = sort_order.lower()

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.size

    @property
    def descending(self) -> bool:
        return self.sort_order == "desc"

    def resolve_sort(self, allowed: dict[str, object], default: str) -> tuple[object, bool]:
        """Valida `sort_by` contra a lista branca de colunas do recurso."""
        field_name = self.sort_by or default
        if field_name not in allowed:
            raise BadRequestError(
                f"Campo de ordenacao '{field_name}' e invalido.",
                details={"allowed_sort_fields": sorted(allowed.keys())},
            )
        return allowed[field_name], self.descending
