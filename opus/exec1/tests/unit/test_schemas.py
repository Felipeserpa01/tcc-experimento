from datetime import date

import pytest
from pydantic import ValidationError

from app.schemas.book import BookCreate, BookUpdate
from app.schemas.user import UserCreate

VALID_BOOK = {
    "title": "  Dom Casmurro  ",
    "author": "Machado de Assis",
    "isbn": "978-0-13-235088-4",
    "year": 1899,
    "total_quantity": 3,
}


class TestUserCreate:
    def test_email_is_lowercased_and_name_stripped(self):
        user = UserCreate(name="  Ana  ", email="Ana.Souza@Example.COM", password="abc12345")
        assert user.email == "ana.souza@example.com"
        assert user.name == "Ana"

    @pytest.mark.parametrize("password", ["curta1", "somenteletras", "1234567890"])
    def test_weak_passwords_are_rejected(self, password: str):
        with pytest.raises(ValidationError):
            UserCreate(name="Ana", email="ana@example.com", password=password)

    def test_invalid_email_is_rejected(self):
        with pytest.raises(ValidationError):
            UserCreate(name="Ana", email="nao-e-email", password="abc12345")


class TestBookCreate:
    def test_valid_book_is_normalized(self):
        book = BookCreate(**VALID_BOOK)
        assert book.title == "Dom Casmurro"
        assert book.isbn == "9780132350884"

    @pytest.mark.parametrize(
        "override",
        [
            {"title": ""},
            {"author": "   "},
            {"isbn": "123"},
            {"year": 0},
            {"year": date.today().year + 1},
            {"total_quantity": 0},
            {"total_quantity": -1},
        ],
    )
    def test_invalid_fields_are_rejected(self, override: dict):
        with pytest.raises(ValidationError):
            BookCreate(**{**VALID_BOOK, **override})


class TestBookUpdate:
    def test_only_sent_fields_are_set(self):
        update = BookUpdate(title="Novo título")
        assert update.model_dump(exclude_unset=True) == {"title": "Novo título"}

    def test_explicit_null_is_rejected(self):
        with pytest.raises(ValidationError):
            BookUpdate(title=None)
