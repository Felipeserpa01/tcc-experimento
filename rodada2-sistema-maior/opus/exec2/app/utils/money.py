"""Cálculos monetários com ``Decimal`` (arredondamento bancário comercial HALF_UP)."""

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

CENT = Decimal("0.01")
HUNDRED = Decimal("100")


def to_money(value: Decimal | int | str) -> Decimal:
    return Decimal(str(value)).quantize(CENT, rounding=ROUND_HALF_UP)


@dataclass(frozen=True)
class DiscountBreakdown:
    gross: Decimal
    percent: Decimal
    discount: Decimal
    net: Decimal


def apply_discount(gross: Decimal, percent: Decimal) -> DiscountBreakdown:
    """Aplica um percentual de desconto (0-100) sobre o valor bruto."""
    gross = to_money(gross)
    percent = to_money(percent)
    if gross <= 0:
        raise ValueError("O valor bruto deve ser positivo.")
    if not Decimal("0") <= percent <= HUNDRED:
        raise ValueError("O percentual de desconto deve estar entre 0 e 100.")
    discount = to_money(gross * percent / HUNDRED)
    return DiscountBreakdown(gross=gross, percent=percent, discount=discount, net=gross - discount)
