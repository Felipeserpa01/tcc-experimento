"""Estruturas de paginação e ordenação compartilhadas entre as camadas."""

import math
from dataclasses import dataclass
from enum import StrEnum
from typing import Generic, TypeVar

T = TypeVar("T")


class SortOrder(StrEnum):
    ASC = "asc"
    DESC = "desc"


@dataclass(frozen=True)
class PageParams:
    page: int = 1
    page_size: int = 20

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size


@dataclass(frozen=True)
class SortParams:
    field: str
    order: SortOrder = SortOrder.ASC

    @property
    def descending(self) -> bool:
        return self.order == SortOrder.DESC


class PageResult(Generic[T]):
    """Resultado paginado (classe simples para ser validada via ``from_attributes``)."""

    __slots__ = ("items", "page", "page_size", "total")

    def __init__(self, items: list[T], total: int, params: PageParams) -> None:
        self.items = items
        self.total = total
        self.page = params.page
        self.page_size = params.page_size

    @property
    def pages(self) -> int:
        return math.ceil(self.total / self.page_size) if self.total else 0
