import re
from datetime import date
from typing import Annotated

from pydantic import AfterValidator, Field, field_validator

from app.schemas.common import InputSchema, OutputSchema, trimmed_str

Title = trimmed_str(1, 255)
Author = trimmed_str(1, 255)
Quantity = Annotated[int, Field(ge=1, le=10_000)]


def normalize_isbn(value: str) -> str:
    """Remove hífens/espaços e valida o dígito verificador de ISBN-10 ou ISBN-13."""
    cleaned = re.sub(r"[\s-]", "", value).upper()

    if re.fullmatch(r"[0-9]{9}[0-9X]", cleaned):
        digits = [10 if ch == "X" else int(ch) for ch in cleaned]
        if sum((10 - i) * d for i, d in enumerate(digits)) % 11 == 0:
            return cleaned
    elif re.fullmatch(r"[0-9]{13}", cleaned):
        if sum(int(ch) * (1 if i % 2 == 0 else 3) for i, ch in enumerate(cleaned)) % 10 == 0:
            return cleaned

    raise ValueError("ISBN inválido: informe um ISBN-10 ou ISBN-13 com dígito verificador correto.")


def _check_year(value: int) -> int:
    if value > date.today().year:
        raise ValueError("O ano de publicação não pode estar no futuro.")
    return value


ISBN = Annotated[str, Field(min_length=10, max_length=17), AfterValidator(normalize_isbn)]
Year = Annotated[int, Field(ge=1), AfterValidator(_check_year)]


class BookCreate(InputSchema):
    title: Title
    author: Author
    isbn: ISBN
    year: Year
    total_quantity: Quantity


class BookUpdate(InputSchema):
    """Atualização parcial. A quantidade disponível é recalculada automaticamente."""

    title: Title | None = None
    author: Author | None = None
    isbn: ISBN | None = None
    year: Year | None = None
    total_quantity: Quantity | None = None

    @field_validator("*", mode="before")
    @classmethod
    def _reject_explicit_null(cls, value):
        if value is None:
            raise ValueError("O campo não pode ser nulo; omita-o para mantê-lo inalterado.")
        return value


class BookOut(OutputSchema):
    id: int
    title: str
    author: str
    isbn: str
    year: int
    total_quantity: int
    available_quantity: int


class BookSummary(OutputSchema):
    id: int
    title: str
    author: str
    isbn: str
