from pydantic import BaseModel


class Page[T](BaseModel):
    items: list[T]
    total: int
    skip: int
    limit: int


class ErrorResponse(BaseModel):
    detail: str
    code: str
