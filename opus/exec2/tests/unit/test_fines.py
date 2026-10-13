from datetime import date
from decimal import Decimal

import pytest

from app.services.fines import calculate_fine, days_overdue, from_cents, to_cents

DUE = date(2026, 3, 16)


@pytest.mark.parametrize(
    ("returned", "expected_days"),
    [
        (date(2026, 3, 10), 0),  # adiantado
        (date(2026, 3, 16), 0),  # no dia previsto
        (date(2026, 3, 17), 1),
        (date(2026, 4, 15), 30),
    ],
)
def test_days_overdue(returned, expected_days):
    assert days_overdue(DUE, returned) == expected_days


def test_no_fine_when_returned_on_or_before_due_date():
    assert calculate_fine(DUE, date(2026, 3, 1), Decimal("2.00")) == Decimal("0.00")
    assert calculate_fine(DUE, DUE, Decimal("2.00")) == Decimal("0.00")


def test_fine_is_days_late_times_daily_rate():
    assert calculate_fine(DUE, date(2026, 3, 21), Decimal("2.00")) == Decimal("10.00")


def test_fine_crosses_month_boundary():
    assert calculate_fine(date(2026, 1, 30), date(2026, 2, 2), Decimal("1.75")) == Decimal("5.25")


def test_fine_rejects_negative_daily_rate():
    with pytest.raises(ValueError):
        calculate_fine(DUE, date(2026, 3, 20), Decimal("-1"))


def test_cents_round_trip():
    assert to_cents(Decimal("12.34")) == 1234
    assert from_cents(1234) == Decimal("12.34")
    assert from_cents(0) == Decimal("0.00")
