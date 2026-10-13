from pydantic import BaseModel, Field
from typing import Generic, TypeVar, List


T = TypeVar("T")


class PageParams(BaseModel):
    page: int = Field(default=1, ge=1)
    size: int = Field(default=20, ge=1, le=100)
    sort_by: str = Field(default="created_at")
    order: str = Field(default="desc")

    def get_offset(self) -> int:
        return (self.page - 1) * self.size

    def get_limit(self) -> int:
        return self.size


class PaginatedResponse(BaseModel, Generic[T]):
    total: int
    page: int
    size: int
    pages: int
    items: List[T]
