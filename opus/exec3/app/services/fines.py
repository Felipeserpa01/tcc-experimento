"""Cálculo de multas por atraso. Funções puras, sem acesso a banco, para facilitar os testes."""

from datetime import date
from decimal import ROUND_HALF_UP, Decimal

_CENT = Decimal("0.01")


def days_overdue(due_date: date, reference_date: date) -> int:
    """Dias corridos entre a data prevista e a data de referência; zero se não houver atraso."""
    return max(0, (reference_date - due_date).days)


def calculate_fine(due_date: date, return_date: date, daily_fine: Decimal) -> Decimal:
    """Multa = dias de atraso x valor diário, arredondada para centavos."""
    if daily_fine < 0:
        raise ValueError("O valor diário da multa não pode ser negativo.")
    return (daily_fine * days_overdue(due_date, return_date)).quantize(_CENT, rounding=ROUND_HALF_UP)


def to_cents(amount: Decimal) -> int:
    return int((amount * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def from_cents(cents: int) -> Decimal:
    return (Decimal(cents) / 100).quantize(_CENT)
