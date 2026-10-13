from datetime import date, datetime, timezone

import pytest
from pydantic import ValidationError

from app.schemas.book import BookCreate, BookUpdate
from app.schemas.loan import LoanCreate
from app.schemas.user import UserCreate
from app.utils.isbn import normalize_isbn
from app.utils.text import contains_pattern, normalize_text
from app.utils.time import local_date

VALID_BOOK = {"title": "Livro", "author": "Autor", "isbn": "9780306406157", "year": 2000, "total_quantity": 2}


class TestIsbn:
    def test_accepts_isbn13_with_separators(self):
        assert normalize_isbn("978-0-306-40615-7") == "9780306406157"

    def test_converts_isbn10_to_isbn13(self):
        assert normalize_isbn("0-306-40615-2") == "9780306406157"

    def test_accepts_isbn10_with_x_check_digit(self):
        assert normalize_isbn("0-8044-2957-X") == "9780804429573"

    @pytest.mark.parametrize("value", ["9780306406158", "0306406153", "12345", "97803064061ab", "１２３４５６７８９０"])
    def test_rejects_invalid_isbn(self, value):
        with pytest.raises(ValueError):
            normalize_isbn(value)


class TestUserCreate:
    def test_normalizes_email_and_name(self):
        user = UserCreate(name="  Ana  ", email="Ana@Example.COM", password="Senha123")
        assert user.name == "Ana"
        assert user.email == "ana@example.com"
        assert user.role == "reader"

    @pytest.mark.parametrize("password", ["curta1", "semnumeros", "12345678"])
    def test_rejects_weak_passwords(self, password):
        with pytest.raises(ValidationError):
            UserCreate(name="Ana", email="ana@example.com", password=password)

    def test_rejects_invalid_email(self):
        with pytest.raises(ValidationError):
            UserCreate(name="Ana", email="nao-e-email", password="Senha123")


class TestBookSchemas:
    def test_future_year_is_rejected(self):
        with pytest.raises(ValidationError):
            BookCreate(**{**VALID_BOOK, "year": date.today().year + 1})

    @pytest.mark.parametrize("quantity", [0, -1, "3", 2.5])
    def test_invalid_quantity_is_rejected(self, quantity):
        with pytest.raises(ValidationError):
            BookCreate(**{**VALID_BOOK, "total_quantity": quantity})

    def test_blank_title_is_rejected(self):
        with pytest.raises(ValidationError):
            BookCreate(**{**VALID_BOOK, "title": "   "})

    def test_available_quantity_cannot_be_set_directly(self):
        with pytest.raises(ValidationError):
            BookCreate(**VALID_BOOK, available_quantity=10)

    def test_update_requires_at_least_one_field(self):
        with pytest.raises(ValidationError):
            BookUpdate()

    def test_update_rejects_null_values(self):
        with pytest.raises(ValidationError):
            BookUpdate(title=None)

    def test_partial_update_keeps_only_sent_fields(self):
        update = BookUpdate(title="Novo título")
        assert update.model_dump(exclude_unset=True) == {"title": "Novo título"}


def test_loan_days_must_be_within_limits():
    with pytest.raises(ValidationError):
        LoanCreate(book_id=1, reader_id=1, loan_days=0)
    with pytest.raises(ValidationError):
        LoanCreate(book_id=1, reader_id=1, loan_days=61)


def test_text_normalization_ignores_case_and_accents():
    assert normalize_text("JOSÉ Saramago") == "jose saramago"
    assert contains_pattern("100%_") == "%100\\%\\_%"


def test_local_date_uses_library_timezone():
    # 01h30 UTC do dia 11 ainda é dia 10 em São Paulo (UTC-3).
    assert local_date(datetime(2026, 3, 11, 1, 30, tzinfo=timezone.utc)) == date(2026, 3, 10)
    with pytest.raises(ValueError):
        local_date(datetime(2026, 3, 11, 1, 30))
