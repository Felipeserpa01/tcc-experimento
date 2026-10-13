from decimal import Decimal
from typing import Annotated, Generic, TypeVar

from pydantic import BaseModel, PlainSerializer

T = TypeVar("T")

# Valores monetários são calculados com Decimal e expostos no JSON como número.
Money = Annotated[Decimal, PlainSerializer(float, return_type=float, when_used="json")]


class Page(BaseModel, Generic[T]):
    items: list[T]
    total: int
    skip: int
    limit: int


class ErrorResponse(BaseModel):
    detail: str
    code: str
