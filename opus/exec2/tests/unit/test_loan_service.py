"""Regras de empréstimo testadas diretamente na camada de serviço."""

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

import pytest

from app.core.config import settings
from app.core.exceptions import ConflictError, InvalidOperationError, NotFoundError
from app.models import Book, Loan, LoanStatus, UserRole
from app.schemas.loan import LoanCreate
from app.services import loan_service

NOW = datetime(2026, 3, 2, 12, 0, tzinfo=timezone.utc)


def borrow(db, book, reader, now=NOW, **kwargs):
    return loan_service.create_loan(db, LoanCreate(book_id=book.id, reader_id=reader.id, **kwargs), now)


def test_create_loan_decrements_availability_and_sets_due_date(db_session, make_book, make_user):
    book = make_book(total_quantity=2)
    reader = make_user()

    loan = borrow(db_session, book, reader)

    assert loan.returned_at is None
    assert loan.due_date == date(2026, 3, 2) + timedelta(days=settings.default_loan_days)
    db_session.refresh(book)
    assert book.available_quantity == 1


def test_custom_loan_period(db_session, make_book, make_user):
    loan = borrow(db_session, make_book(), make_user(), loan_days=7)
    assert loan.due_date == date(2026, 3, 9)


def test_cannot_borrow_without_available_copies(db_session, make_book, make_user):
    book = make_book(total_quantity=1)
    borrow(db_session, book, make_user())

    with pytest.raises(ConflictError) as exc:
        borrow(db_session, book, make_user())
    assert exc.value.code == "book_unavailable"


def test_reader_limited_to_three_simultaneous_loans(db_session, make_book, make_user):
    reader = make_user()
    for _ in range(3):
        borrow(db_session, make_book(), reader)

    book = make_book()
    with pytest.raises(ConflictError) as exc:
        borrow(db_session, book, reader)
    assert exc.value.code == "loan_limit_reached"
    db_session.refresh(book)
    assert book.available_quantity == 1  # nada foi alterado


def test_returned_loans_do_not_count_towards_limit(db_session, make_book, make_user):
    reader = make_user()
    loans = [borrow(db_session, make_book(), reader) for _ in range(3)]
    loan_service.return_loan(db_session, loans[0].id, NOW)

    assert borrow(db_session, make_book(), reader).id is not None
    assert loan_service.count_active_loans(db_session, reader.id) == 3


def test_only_readers_can_borrow(db_session, make_book, make_user):
    with pytest.raises(InvalidOperationError):
        borrow(db_session, make_book(), make_user(UserRole.LIBRARIAN))


def test_missing_book_or_reader(db_session, make_book, make_user):
    with pytest.raises(NotFoundError):
        loan_service.create_loan(db_session, LoanCreate(book_id=999, reader_id=make_user().id), NOW)
    with pytest.raises(NotFoundError):
        loan_service.create_loan(db_session, LoanCreate(book_id=make_book().id, reader_id=999), NOW)


def test_on_time_return_has_no_fine_and_restores_availability(db_session, make_book, make_user):
    book = make_book()
    loan = borrow(db_session, book, make_user())

    returned = loan_service.return_loan(db_session, loan.id, NOW + timedelta(days=5))

    assert returned.returned_at == NOW + timedelta(days=5)
    assert returned.fine_amount_cents == 0
    db_session.refresh(book)
    assert book.available_quantity == 1


def test_late_return_charges_fine_per_day(db_session, make_book, make_user):
    loan = borrow(db_session, make_book(), make_user(), loan_days=10)  # vence em 12/03

    returned = loan_service.return_loan(db_session, loan.id, datetime(2026, 3, 16, 15, 0, tzinfo=timezone.utc))

    view = loan_service.build_loan_read(returned, NOW)
    assert view.status == LoanStatus.RETURNED
    assert view.days_overdue == 4
    assert view.fine_amount == settings.daily_fine * 4


def test_cannot_return_twice(db_session, make_book, make_user):
    book = make_book(total_quantity=2)
    loan = borrow(db_session, book, make_user())
    loan_service.return_loan(db_session, loan.id, NOW)

    with pytest.raises(ConflictError):
        loan_service.return_loan(db_session, loan.id, NOW)
    db_session.refresh(book)
    assert book.available_quantity == 2  # estoque não foi incrementado duas vezes


def test_open_overdue_loan_shows_accrued_fine(db_session, make_book, make_user):
    loan = borrow(db_session, make_book(), make_user(), loan_days=1)

    view = loan_service.build_loan_read(loan, NOW + timedelta(days=4))

    assert view.status == LoanStatus.OVERDUE
    assert view.days_overdue == 3
    assert view.fine_amount == Decimal("6.00")


def test_concurrent_returns_do_not_restock_twice(session_factory, db_session, make_book, make_user):
    """Simula duas devoluções simultâneas: a sessão A carrega o empréstimo ainda
    em aberto, mas a sessão B conclui a devolução antes dela."""
    book = make_book(total_quantity=1)
    loan = borrow(db_session, book, make_user())

    with session_factory() as session_a, session_factory() as session_b:
        # Mantém a referência: o identity map guarda objetos por referência fraca.
        stale_loan = session_a.get(Loan, loan.id)
        loan_service.return_loan(session_b, loan.id, NOW)
        assert stale_loan.returned_at is None  # A ainda enxerga o empréstimo em aberto

        with pytest.raises(ConflictError):
            loan_service.return_loan(session_a, loan.id, NOW)

    db_session.refresh(book)
    assert book.available_quantity == 1


def test_concurrent_loans_cannot_take_the_same_last_copy(session_factory, db_session, make_book, make_user):
    book = make_book(total_quantity=1)
    first_reader, second_reader = make_user(), make_user()

    with session_factory() as session_a, session_factory() as session_b:
        stale_book = session_a.get(Book, book.id)
        borrow(session_b, book, first_reader)
        assert stale_book.available_quantity == 1  # A ainda enxerga 1 exemplar disponível

        with pytest.raises(ConflictError):
            borrow(session_a, book, second_reader)

    db_session.refresh(book)
    assert book.available_quantity == 0
    assert loan_service.count_active_loans(db_session, second_reader.id) == 0
