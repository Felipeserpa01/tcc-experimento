from datetime import date

import pytest
from pydantic import ValidationError

from app.schemas.book import BookCreate, BookUpdate, normalize_isbn
from app.schemas.user import UserRegister

VALID_BOOK = {"title": "Dom Casmurro", "author": "Machado de Assis", "isbn": "9780306406157", "year": 1899, "total_quantity": 3}


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("978-0-306-40615-7", "9780306406157"),
        ("978 0 306 40615 7", "9780306406157"),
        ("0-306-40615-2", "0306406152"),
        ("0-8044-2957-x", "080442957X"),
    ],
)
def test_normalize_valid_isbn(raw: str, expected: str) -> None:
    assert normalize_isbn(raw) == expected


@pytest.mark.parametrize("raw", ["9780306406158", "0306406153", "12345", "97803064061A7", "X804429570"])
def test_normalize_invalid_isbn(raw: str) -> None:
    with pytest.raises(ValueError):
        normalize_isbn(raw)


def test_book_create_strips_whitespace() -> None:
    book = BookCreate(**VALID_BOOK | {"title": "  Dom Casmurro  "})
    assert book.title == "Dom Casmurro"


@pytest.mark.parametrize(
    "override",
    [
        {"title": "   "},
        {"author": ""},
        {"isbn": "123"},
        {"year": 0},
        {"year": date.today().year + 1},
        {"total_quantity": 0},
        {"total_quantity": -5},
        {"available_quantity": 10},  # campo calculado pelo sistema, não aceito na entrada
    ],
)
def test_book_create_rejects_invalid_data(override: dict) -> None:
    with pytest.raises(ValidationError):
        BookCreate(**VALID_BOOK | override)


def test_book_update_accepts_partial_data() -> None:
    update = BookUpdate(title="Novo título")
    assert update.model_dump(exclude_unset=True) == {"title": "Novo título"}


def test_book_update_rejects_explicit_null() -> None:
    with pytest.raises(ValidationError):
        BookUpdate(title=None)


def test_user_register_normalizes_email() -> None:
    user = UserRegister(name="Ana", email="Ana.Souza@Example.COM", password="senha1234")
    assert user.email == "ana.souza@example.com"


@pytest.mark.parametrize("password", ["curta1", "somenteletras", "1234567890", "a1" * 65])
def test_user_register_rejects_weak_password(password: str) -> None:
    with pytest.raises(ValidationError):
        UserRegister(name="Ana", email="ana@example.com", password=password)
