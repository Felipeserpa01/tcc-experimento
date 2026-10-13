from datetime import date
from decimal import ROUND_HALF_UP, Decimal

CENTS = Decimal("0.01")


def calculate_days_overdue(due_date: date, reference_date: date) -> int:
    """Dias corridos entre a data prevista e a data de referência (0 se não houver atraso)."""
    return max(0, (reference_date - due_date).days)


def calculate_fine(due_date: date, reference_date: date, daily_fine: Decimal) -> Decimal:
    """Multa = dias de atraso x valor diário, arredondada para centavos."""
    days = calculate_days_overdue(due_date, reference_date)
    return (daily_fine * days).quantize(CENTS, rounding=ROUND_HALF_UP)
