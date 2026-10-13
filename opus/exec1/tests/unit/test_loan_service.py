from datetime import date, timedelta
from decimal import Decimal

import pytest

from app.core.config import settings
from app.core.exceptions import BusinessRuleError, ConflictError, NotFoundError
from app.schemas.loan import LoanCreate, LoanStatus
from app.services import loan_service

TODAY = date(2026, 3, 2)


def borrow(db_session, book, reader, today=TODAY, **kwargs):
    return loan_service.create_loan(db_session, LoanCreate(book_id=book.id, reader_id=reader.id, **kwargs), today)


class TestCreateLoan:
    def test_creates_loan_with_default_due_date_and_decrements_availability(self, db_session, book_factory, reader):
        book = book_factory(total_quantity=2)

        loan = borrow(db_session, book, reader)

        assert loan.loan_date == TODAY
        assert loan.due_date == TODAY + timedelta(days=settings.loan_period_days)
        assert loan.return_date is None
        db_session.refresh(book)
        assert book.available_quantity == 1

    def test_accepts_custom_due_date(self, db_session, book_factory, reader):
        loan = borrow(db_session, book_factory(), reader, due_date=TODAY + timedelta(days=3))
        assert loan.due_date == date(2026, 3, 5)

    @pytest.mark.parametrize("days", [0, -1])
    def test_rejects_due_date_not_after_loan_date(self, db_session, book_factory, reader, days):
        with pytest.raises(BusinessRuleError):
            borrow(db_session, book_factory(), reader, due_date=TODAY + timedelta(days=days))

    def test_rejects_loan_when_no_copies_available(self, db_session, book_factory, reader, other_reader):
        book = book_factory(total_quantity=1)
        borrow(db_session, book, reader)

        with pytest.raises(ConflictError) as exc:
            borrow(db_session, book, other_reader)

        assert exc.value.code == "book_unavailable"
        db_session.refresh(book)
        assert book.available_quantity == 0

    def test_limits_reader_to_max_simultaneous_loans(self, db_session, book_factory, reader):
        for _ in range(settings.max_active_loans):
            borrow(db_session, book_factory(), reader)

        extra_book = book_factory()
        with pytest.raises(ConflictError) as exc:
            borrow(db_session, extra_book, reader)

        assert exc.value.code == "loan_limit_reached"
        db_session.refresh(extra_book)
        assert extra_book.available_quantity == extra_book.total_quantity

    def test_returned_loans_do_not_count_towards_limit(self, db_session, book_factory, reader):
        loans = [borrow(db_session, book_factory(), reader) for _ in range(settings.max_active_loans)]
        loan_service.return_loan(db_session, loans[0].id, TODAY)

        assert borrow(db_session, book_factory(), reader).return_date is None

    def test_only_readers_can_borrow(self, db_session, book_factory, librarian):
        with pytest.raises(BusinessRuleError) as exc:
            borrow(db_session, book_factory(), librarian)
        assert exc.value.code == "not_a_reader"

    def test_unknown_book_or_reader_raises_not_found(self, db_session, book_factory, reader):
        with pytest.raises(NotFoundError):
            loan_service.create_loan(db_session, LoanCreate(book_id=999, reader_id=reader.id), TODAY)
        with pytest.raises(NotFoundError):
            loan_service.create_loan(db_session, LoanCreate(book_id=book_factory().id, reader_id=999), TODAY)


class TestReturnLoan:
    def test_on_time_return_has_no_fine_and_restores_availability(self, db_session, book_factory, reader):
        book = book_factory(total_quantity=1)
        loan = borrow(db_session, book, reader)

        returned = loan_service.return_loan(db_session, loan.id, loan.due_date)

        assert returned.return_date == loan.due_date
        assert returned.fine_amount == Decimal("0.00")
        assert returned.book.available_quantity == 1

    def test_late_return_charges_fine_per_day(self, db_session, book_factory, reader):
        loan = borrow(db_session, book_factory(), reader)
        return_date = loan.due_date + timedelta(days=5)

        returned = loan_service.return_loan(db_session, loan.id, return_date)

        assert returned.fine_amount == settings.daily_fine * 5
        read = loan_service.build_loan_read(returned, today=return_date + timedelta(days=30))
        assert read.status == LoanStatus.RETURNED
        assert read.days_overdue == 5  # não continua crescendo após a devolução
        assert read.fine_amount == settings.daily_fine * 5

    def test_cannot_return_twice(self, db_session, book_factory, reader):
        book = book_factory(total_quantity=1)
        loan = borrow(db_session, book, reader)
        loan_service.return_loan(db_session, loan.id, TODAY)

        with pytest.raises(ConflictError):
            loan_service.return_loan(db_session, loan.id, TODAY)

        db_session.refresh(book)
        assert book.available_quantity == 1

    def test_unknown_loan_raises_not_found(self, db_session):
        with pytest.raises(NotFoundError):
            loan_service.return_loan(db_session, 999, TODAY)


class TestQueries:
    def test_active_fine_is_estimated_until_today(self, db_session, book_factory, reader):
        loan = borrow(db_session, book_factory(), reader)

        fine = loan_service.build_fine(loan, today=loan.due_date + timedelta(days=3))

        assert fine.days_overdue == 3
        assert fine.amount == settings.daily_fine * 3
        assert fine.is_final is False

    def test_list_active_loans_for_reader_excludes_returned_and_other_readers(
        self, db_session, book_factory, reader, other_reader
    ):
        active = borrow(db_session, book_factory(), reader)
        returned = borrow(db_session, book_factory(), reader)
        loan_service.return_loan(db_session, returned.id, TODAY)
        borrow(db_session, book_factory(), other_reader)

        loans = loan_service.list_active_loans_for_reader(db_session, reader.id)

        assert [loan.id for loan in loans] == [active.id]

    def test_list_overdue_loans(self, db_session, book_factory, reader):
        late = borrow(db_session, book_factory(), reader, due_date=TODAY + timedelta(days=1))
        borrow(db_session, book_factory(), reader, due_date=TODAY + timedelta(days=10))

        loans, total = loan_service.list_loans(db_session, TODAY + timedelta(days=5), overdue_only=True)

        assert total == 1
        assert loans[0].id == late.id
