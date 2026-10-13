from datetime import date, datetime, timedelta

from sqlalchemy import ColumnElement, func, select, update
from sqlalchemy.orm import Session, joinedload

from app.core.config import settings
from app.core.exceptions import ConflictError, NotFoundError
from app.models import Book, Loan, LoanStatus, User
from app.schemas.book import BookSummary
from app.schemas.loan import LoanCreate, LoanRead
from app.schemas.user import UserSummary
from app.services import fines
from app.services.book_service import get_book
from app.services.user_service import get_reader
from app.utils.time import local_date


def count_active_loans(db: Session, reader_id: int) -> int:
    return (
        db.scalar(
            select(func.count()).select_from(Loan).where(Loan.reader_id == reader_id, Loan.returned_at.is_(None))
        )
        or 0
    )


def get_loan(db: Session, loan_id: int) -> Loan:
    loan = db.get(Loan, loan_id)
    if loan is None:
        raise NotFoundError("Empréstimo não encontrado", code="loan_not_found")
    return loan


def create_loan(db: Session, data: LoanCreate, now: datetime) -> Loan:
    book = get_book(db, data.book_id)
    reader = get_reader(db, data.reader_id)

    active_loans = count_active_loans(db, reader.id)
    if active_loans >= settings.max_active_loans:
        raise ConflictError(
            f"O leitor já atingiu o limite de {settings.max_active_loans} empréstimos simultâneos",
            code="loan_limit_reached",
        )

    # Decremento condicional em um único UPDATE: se duas requisições disputarem o
    # último exemplar, apenas uma consegue alterar a linha.
    result = db.execute(
        update(Book)
        .where(Book.id == book.id, Book.available_quantity > 0)
        .values(available_quantity=Book.available_quantity - 1)
        .execution_options(synchronize_session=False)
    )
    if result.rowcount == 0:
        raise ConflictError("Não há exemplares disponíveis deste livro", code="book_unavailable")

    loan_days = data.loan_days if data.loan_days is not None else settings.default_loan_days
    loan = Loan(
        book_id=book.id,
        reader_id=reader.id,
        loan_date=now,
        due_date=local_date(now) + timedelta(days=loan_days),
    )
    db.add(loan)
    db.commit()
    db.refresh(book)
    db.refresh(loan)
    return loan


def return_loan(db: Session, loan_id: int, now: datetime) -> Loan:
    loan = get_loan(db, loan_id)
    if loan.returned_at is not None:
        raise ConflictError("Este empréstimo já foi devolvido", code="loan_already_returned")

    fine = fines.calculate_fine(loan.due_date, local_date(now), settings.daily_fine)

    # A condição "returned_at IS NULL" impede que devoluções simultâneas do mesmo
    # empréstimo devolvam o exemplar ao estoque duas vezes.
    result = db.execute(
        update(Loan)
        .where(Loan.id == loan.id, Loan.returned_at.is_(None))
        .values(returned_at=now, fine_amount_cents=fines.to_cents(fine))
        .execution_options(synchronize_session=False)
    )
    if result.rowcount == 0:
        db.rollback()
        raise ConflictError("Este empréstimo já foi devolvido", code="loan_already_returned")

    db.execute(
        update(Book)
        .where(Book.id == loan.book_id)
        .values(available_quantity=Book.available_quantity + 1)
        .execution_options(synchronize_session=False)
    )
    db.commit()
    db.refresh(loan)
    db.refresh(loan.book)
    return loan


def list_loans(
    db: Session,
    *,
    today: date,
    reader_id: int | None = None,
    book_id: int | None = None,
    status: LoanStatus | None = None,
    skip: int = 0,
    limit: int = 20,
) -> tuple[list[Loan], int]:
    """Lista empréstimos. O filtro `active` inclui os atrasados, pois ambos estão em aberto."""
    filters: list[ColumnElement[bool]] = []
    if reader_id is not None:
        filters.append(Loan.reader_id == reader_id)
    if book_id is not None:
        filters.append(Loan.book_id == book_id)
    if status == LoanStatus.ACTIVE:
        filters.append(Loan.returned_at.is_(None))
    elif status == LoanStatus.OVERDUE:
        filters.extend([Loan.returned_at.is_(None), Loan.due_date < today])
    elif status == LoanStatus.RETURNED:
        filters.append(Loan.returned_at.is_not(None))

    total = db.scalar(select(func.count()).select_from(Loan).where(*filters)) or 0
    loans = db.scalars(
        select(Loan)
        .options(joinedload(Loan.book), joinedload(Loan.reader))
        .where(*filters)
        .order_by(Loan.loan_date.desc(), Loan.id.desc())
        .offset(skip)
        .limit(limit)
    ).all()
    return list(loans), total


def list_active_loans_for_reader(db: Session, reader: User) -> list[Loan]:
    loans = db.scalars(
        select(Loan)
        .options(joinedload(Loan.book), joinedload(Loan.reader))
        .where(Loan.reader_id == reader.id, Loan.returned_at.is_(None))
        .order_by(Loan.due_date, Loan.id)
    ).all()
    return list(loans)


def build_loan_read(loan: Loan, now: datetime) -> LoanRead:
    """Monta a resposta do empréstimo, incluindo atraso e multa.

    Para empréstimos devolvidos, usa a multa registrada na devolução; para os
    que estão em aberto, calcula a multa acumulada até a data atual.
    """
    today = local_date(now)
    if loan.returned_at is not None:
        overdue = fines.days_overdue(loan.due_date, local_date(loan.returned_at))
        fine = fines.from_cents(loan.fine_amount_cents)
    else:
        overdue = fines.days_overdue(loan.due_date, today)
        fine = fines.calculate_fine(loan.due_date, today, settings.daily_fine)

    return LoanRead(
        id=loan.id,
        book=BookSummary.model_validate(loan.book),
        reader=UserSummary.model_validate(loan.reader),
        loan_date=loan.loan_date,
        due_date=loan.due_date,
        returned_at=loan.returned_at,
        status=loan.status_on(today),
        days_overdue=overdue,
        fine_amount=fine,
    )
