from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, ConfigDict, PlainSerializer, StringConstraints


class InputSchema(BaseModel):
    """Base dos schemas de entrada: rejeita campos desconhecidos (ex.: ``available_quantity``)."""

    model_config = ConfigDict(extra="forbid")


class OutputSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)


def trimmed_str(min_length: int, max_length: int) -> type[str]:
    return Annotated[str, StringConstraints(strip_whitespace=True, min_length=min_length, max_length=max_length)]


# Valores monetários são calculados com Decimal e expostos como número no JSON.
Money = Annotated[Decimal, PlainSerializer(float, return_type=float, when_used="json")]
