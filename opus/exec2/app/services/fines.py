"""Cálculo de multas por atraso (funções puras, sem acesso ao banco)."""

from datetime import date
from decimal import ROUND_HALF_UP, Decimal

CENT = Decimal("0.01")


def days_overdue(due_date: date, reference_date: date) -> int:
    """Dias de atraso entre a data prevista e a data de referência. Nunca é negativo."""
    return max(0, (reference_date - due_date).days)


def calculate_fine(due_date: date, return_date: date, daily_fine: Decimal) -> Decimal:
    """Multa = dias de atraso x valor diário. Devoluções até a data prevista não geram multa."""
    if daily_fine < 0:
        raise ValueError("O valor da multa diária não pode ser negativo")
    return (daily_fine * days_overdue(due_date, return_date)).quantize(CENT, rounding=ROUND_HALF_UP)


def to_cents(amount: Decimal) -> int:
    return int((amount * 100).to_integral_value(rounding=ROUND_HALF_UP))


def from_cents(cents: int) -> Decimal:
    return (Decimal(cents) / 100).quantize(CENT)
