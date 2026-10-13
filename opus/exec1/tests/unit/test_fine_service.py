from datetime import date
from decimal import Decimal

import pytest

from app.services.fine_service import calculate_days_overdue, calculate_fine

DUE = date(2026, 3, 16)


@pytest.mark.parametrize(
    ("reference", "expected_days"),
    [
        (date(2026, 3, 10), 0),  # devolvido antes do prazo
        (date(2026, 3, 16), 0),  # devolvido no dia previsto
        (date(2026, 3, 17), 1),
        (date(2026, 4, 15), 30),
    ],
)
def test_days_overdue(reference: date, expected_days: int):
    assert calculate_days_overdue(DUE, reference) == expected_days


def test_no_fine_when_returned_on_time():
    assert calculate_fine(DUE, date(2026, 3, 16), Decimal("2.00")) == Decimal("0.00")


def test_fine_is_days_overdue_times_daily_rate():
    assert calculate_fine(DUE, date(2026, 3, 21), Decimal("2.00")) == Decimal("10.00")


def test_fine_crosses_month_and_year_boundaries():
    assert calculate_fine(date(2026, 12, 30), date(2027, 1, 2), Decimal("1.50")) == Decimal("4.50")


def test_fine_is_rounded_to_cents():
    assert calculate_fine(DUE, date(2026, 3, 19), Decimal("0.333")) == Decimal("1.00")
    assert calculate_fine(DUE, date(2026, 3, 17), Decimal("0.125")) == Decimal("0.13")


def test_zero_daily_rate_means_no_fine():
    assert calculate_fine(DUE, date(2026, 5, 1), Decimal("0")) == Decimal("0.00")
