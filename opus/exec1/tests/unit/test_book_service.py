from datetime import date

import pytest

from app.core.exceptions import ConflictError, NotFoundError
from app.schemas.book import BookCreate, BookUpdate
from app.schemas.loan import LoanCreate
from app.services import book_service, loan_service

TODAY = date(2026, 3, 2)


@pytest.fixture
def catalog(book_factory):
    return [
        book_factory(title="Dom Casmurro", author="Machado de Assis"),
        book_factory(title="Memórias Póstumas de Brás Cubas", author="Machado de Assis"),
        book_factory(title="O Cortiço", author="Aluísio Azevedo"),
        book_factory(title="100% Brasil", author="Vários"),
    ]


class TestSearch:
    def test_search_by_title_is_case_insensitive(self, db_session, catalog):
        books, total = book_service.list_books(db_session, title="dom CASMURRO")
        assert total == 1
        assert books[0].title == "Dom Casmurro"

    def test_search_by_author(self, db_session, catalog):
        books, total = book_service.list_books(db_session, author="machado")
        assert total == 2
        assert {b.title for b in books} == {"Dom Casmurro", "Memórias Póstumas de Brás Cubas"}

    def test_generic_query_matches_title_or_author(self, db_session, catalog):
        _, by_author = book_service.list_books(db_session, q="azevedo")
        _, by_title = book_service.list_books(db_session, q="cortiço")
        assert by_author == by_title == 1

    def test_like_wildcards_are_treated_literally(self, db_session, catalog):
        books, total = book_service.list_books(db_session, q="%")
        assert total == 1
        assert books[0].title == "100% Brasil"

    def test_pagination_returns_total_of_all_matches(self, db_session, catalog):
        books, total = book_service.list_books(db_session, skip=1, limit=2)
        assert total == 4
        assert len(books) == 2


class TestCreateAndUpdate:
    def test_new_book_starts_with_all_copies_available(self, book_factory):
        book = book_factory(total_quantity=5)
        assert book.available_quantity == 5

    def test_duplicate_isbn_is_rejected(self, db_session, book_factory):
        book = book_factory()
        data = BookCreate(title="Outro", author="Outro", isbn=book.isbn, year=2001, total_quantity=1)
        with pytest.raises(ConflictError):
            book_service.create_book(db_session, data)

    def test_changing_isbn_to_one_in_use_is_rejected(self, db_session, book_factory):
        first, second = book_factory(), book_factory()
        with pytest.raises(ConflictError):
            book_service.update_book(db_session, second.id, BookUpdate(isbn=first.isbn))

    def test_total_quantity_change_keeps_loaned_copies(self, db_session, book_factory, reader):
        book = book_factory(total_quantity=3)
        loan_service.create_loan(db_session, LoanCreate(book_id=book.id, reader_id=reader.id), TODAY)

        updated = book_service.update_book(db_session, book.id, BookUpdate(total_quantity=5))

        assert updated.total_quantity == 5
        assert updated.available_quantity == 4

    def test_total_quantity_cannot_drop_below_loaned_copies(self, db_session, book_factory, reader, other_reader):
        book = book_factory(total_quantity=3)
        for r in (reader, other_reader):
            loan_service.create_loan(db_session, LoanCreate(book_id=book.id, reader_id=r.id), TODAY)

        with pytest.raises(ConflictError) as exc:
            book_service.update_book(db_session, book.id, BookUpdate(total_quantity=1))
        assert exc.value.code == "total_below_loaned"

    def test_update_unknown_book_raises_not_found(self, db_session):
        with pytest.raises(NotFoundError):
            book_service.update_book(db_session, 999, BookUpdate(title="X"))


class TestDelete:
    def test_book_with_active_loan_cannot_be_deleted(self, db_session, book_factory, reader):
        book = book_factory()
        loan_service.create_loan(db_session, LoanCreate(book_id=book.id, reader_id=reader.id), TODAY)

        with pytest.raises(ConflictError):
            book_service.delete_book(db_session, book.id)

    def test_book_with_only_returned_loans_is_deleted_with_history(self, db_session, book_factory, reader):
        book = book_factory()
        loan = loan_service.create_loan(db_session, LoanCreate(book_id=book.id, reader_id=reader.id), TODAY)
        loan_service.return_loan(db_session, loan.id, TODAY)

        book_service.delete_book(db_session, book.id)

        with pytest.raises(NotFoundError):
            book_service.get_book(db_session, book.id)
        with pytest.raises(NotFoundError):
            loan_service.get_loan(db_session, loan.id)
