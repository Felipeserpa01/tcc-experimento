from datetime import date, datetime
from typing import Annotated

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, StringConstraints, model_validator

from app.utils.isbn import normalize_isbn


def _not_in_future(year: int) -> int:
    current_year = date.today().year
    if year > current_year:
        raise ValueError(f"O ano não pode ser posterior a {current_year}")
    return year


Text = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=255)]
ISBN = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=10, max_length=17),
    AfterValidator(normalize_isbn),
    Field(description="ISBN-10 ou ISBN-13 (hífens opcionais). É armazenado como ISBN-13."),
]
PublicationYear = Annotated[int, Field(ge=1, strict=True), AfterValidator(_not_in_future)]
Quantity = Annotated[int, Field(ge=1, le=10_000, strict=True)]


class BookCreate(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "examples": [
                {
                    "title": "Dom Casmurro",
                    "author": "Machado de Assis",
                    "isbn": "978-0-306-40615-7",
                    "year": 1899,
                    "total_quantity": 3,
                }
            ]
        },
    )

    title: Text
    author: Text
    isbn: ISBN
    year: PublicationYear
    total_quantity: Quantity


class BookUpdate(BaseModel):
    """Atualização parcial: apenas os campos enviados são alterados."""

    model_config = ConfigDict(extra="forbid")

    title: Text | None = None
    author: Text | None = None
    isbn: ISBN | None = None
    year: PublicationYear | None = None
    total_quantity: Quantity | None = Field(
        default=None,
        description="A quantidade disponível é ajustada automaticamente conforme os exemplares emprestados.",
    )

    @model_validator(mode="after")
    def _validate_fields(self) -> "BookUpdate":
        if not self.model_fields_set:
            raise ValueError("Informe ao menos um campo para atualizar")
        null_fields = sorted(name for name in self.model_fields_set if getattr(self, name) is None)
        if null_fields:
            raise ValueError(f"Os campos não podem ser nulos: {', '.join(null_fields)}")
        return self


class BookRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    author: str
    isbn: str
    year: int
    total_quantity: int
    available_quantity: int
    created_at: datetime
    updated_at: datetime


class BookSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    author: str
    isbn: str
