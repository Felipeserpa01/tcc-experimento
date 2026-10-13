from datetime import date, datetime
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.core.isbn import normalize_isbn

MIN_YEAR = 1


def _validate_year(value: int) -> int:
    if value > date.today().year:
        raise ValueError("O ano de publicação não pode estar no futuro")
    return value


class BookCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    title: str = Field(min_length=1, max_length=255)
    author: str = Field(min_length=1, max_length=255)
    isbn: str = Field(examples=["978-0-13-235088-4"])
    year: int = Field(ge=MIN_YEAR)
    total_quantity: int = Field(ge=1, le=10_000)

    @field_validator("isbn")
    @classmethod
    def _normalize_isbn(cls, value: str) -> str:
        return normalize_isbn(value)

    @field_validator("year")
    @classmethod
    def _check_year(cls, value: int) -> int:
        return _validate_year(value)


class BookUpdate(BaseModel):
    """Atualização parcial. A quantidade disponível é recalculada a partir da nova quantidade total."""

    model_config = ConfigDict(str_strip_whitespace=True)

    title: str | None = Field(default=None, min_length=1, max_length=255)
    author: str | None = Field(default=None, min_length=1, max_length=255)
    isbn: str | None = None
    year: int | None = Field(default=None, ge=MIN_YEAR)
    total_quantity: int | None = Field(default=None, ge=1, le=10_000)

    @field_validator("isbn")
    @classmethod
    def _normalize_isbn(cls, value: str | None) -> str | None:
        return normalize_isbn(value) if value is not None else None

    @field_validator("year")
    @classmethod
    def _check_year(cls, value: int | None) -> int | None:
        return _validate_year(value) if value is not None else None

    @model_validator(mode="after")
    def _reject_explicit_nulls(self) -> Self:
        nulls = [name for name in self.model_fields_set if getattr(self, name) is None]
        if nulls:
            raise ValueError(f"Os campos não podem ser nulos: {', '.join(sorted(nulls))}")
        return self


class BookSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    author: str
    isbn: str


class BookRead(BookSummary):
    year: int
    total_quantity: int
    available_quantity: int
    created_at: datetime
    updated_at: datetime
