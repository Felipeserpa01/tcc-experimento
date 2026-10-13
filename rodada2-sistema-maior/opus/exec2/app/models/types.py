"""Tipos de coluna customizados."""

from decimal import ROUND_HALF_UP, Decimal
from enum import Enum

from sqlalchemy import Enum as SAEnum
from sqlalchemy import Integer
from sqlalchemy.types import TypeDecorator

CENT = Decimal("0.01")


class _FixedPoint(TypeDecorator):
    """Decimal com 2 casas armazenado como inteiro (centésimos).

    O SQLite não possui tipo decimal nativo; guardar centésimos em INTEGER evita
    erros de arredondamento de ponto flutuante em somas e comparações.
    """

    impl = Integer
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        return int((Decimal(str(value)) * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        return (Decimal(int(value)) / Decimal(100)).quantize(CENT)


class Money(_FixedPoint):
    """Valor monetário em reais (armazenado em centavos)."""

    cache_ok = True


class Percentage(_FixedPoint):
    """Percentual com 2 casas decimais (armazenado em centésimos de ponto percentual)."""

    cache_ok = True


def enum_type(enum_cls: type[Enum]) -> SAEnum:
    """Persiste o *valor* do enum (ex.: ``"agendada"``) com CHECK constraint."""
    return SAEnum(
        enum_cls,
        values_callable=lambda members: [member.value for member in members],
        native_enum=False,
        create_constraint=True,
        validate_strings=True,
        length=max(len(member.value) for member in enum_cls),
        name=f"ck_{enum_cls.__name__.lower()}",
    )
