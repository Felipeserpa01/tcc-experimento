"""Shared/generic schemas: pagination envelope and query params."""
from typing import Generic, Literal, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class PaginationParams(BaseModel):
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
    sort_by: str | None = None
    sort_order: Literal["asc", "desc"] = "asc"


class PaginatedResponse(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    page_size: int
    total_pages: int

    @classmethod
    def build(cls, items: list[T], total: int, page: int, page_size: int) -> "PaginatedResponse[T]":
        total_pages = (total + page_size - 1) // page_size if page_size else 0
        return cls(items=items, total=total, page=page, page_size=page_size, total_pages=total_pages)


class MessageResponse(BaseModel):
    message: str
