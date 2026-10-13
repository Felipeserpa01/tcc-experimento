from datetime import date
from decimal import Decimal

import pytest

from app.services.fines import calculate_fine, days_overdue, from_cents, to_cents

DUE = date(2026, 3, 16)


@pytest.mark.parametrize(
    ("returned_on", "expected_days"),
    [
        (date(2026, 3, 10), 0),  # devolvido antes do prazo
        (date(2026, 3, 16), 0),  # devolvido no dia do vencimento
        (date(2026, 3, 17), 1),
        (date(2026, 3, 26), 10),
        (date(2026, 4, 2), 17),  # atravessa a virada do mês
    ],
)
def test_days_overdue(returned_on: date, expected_days: int) -> None:
    assert days_overdue(DUE, returned_on) == expected_days


@pytest.mark.parametrize(
    ("returned_on", "expected_fine"),
    [
        (date(2026, 3, 1), Decimal("0.00")),
        (DUE, Decimal("0.00")),
        (date(2026, 3, 17), Decimal("2.00")),
        (date(2026, 3, 26), Decimal("20.00")),
    ],
)
def test_calculate_fine_with_default_rate(returned_on: date, expected_fine: Decimal) -> None:
    assert calculate_fine(DUE, returned_on, Decimal("2.00")) == expected_fine


def test_calculate_fine_rounds_to_cents() -> None:
    assert calculate_fine(DUE, date(2026, 3, 19), Decimal("1.335")) == Decimal("4.01")


def test_calculate_fine_with_zero_rate_is_free() -> None:
    assert calculate_fine(DUE, date(2026, 12, 31), Decimal("0")) == Decimal("0.00")


def test_calculate_fine_rejects_negative_rate() -> None:
    with pytest.raises(ValueError):
        calculate_fine(DUE, date(2026, 3, 20), Decimal("-1"))


@pytest.mark.parametrize("amount", [Decimal("0.00"), Decimal("0.01"), Decimal("2.00"), Decimal("123.45")])
def test_cents_conversion_round_trip(amount: Decimal) -> None:
    assert from_cents(to_cents(amount)) == amount
