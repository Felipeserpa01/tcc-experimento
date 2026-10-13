from datetime import date, timedelta

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session, joinedload

from app.core.config import settings
from app.core.exceptions import BusinessRuleError, ConflictError, NotFoundError
from app.models.book import Book
from app.models.loan import Loan
from app.models.user import User, UserRole
from app.schemas.book import BookSummary
from app.schemas.loan import LoanCreate, LoanOut, LoanStatus
from app.schemas.user import UserSummary
from app.services import book_service
from app.services.fines import calculate_fine, days_overdue, from_cents, to_cents


def get_loan(db: Session, loan_id: int) -> Loan:
    stmt = select(Loan).options(joinedload(Loan.book), joinedload(Loan.reader)).where(Loan.id == loan_id)
    loan = db.scalar(stmt)
    if loan is None:
        raise NotFoundError("Empréstimo não encontrado.")
    return loan


def count_active_loans_for_reader(db: Session, reader_id: int) -> int:
    stmt = select(func.count()).select_from(Loan).where(Loan.reader_id == reader_id, Loan.return_date.is_(None))
    return db.scalar(stmt) or 0


def list_loans(
    db: Session,
    *,
    today: date,
    reader_id: int | None = None,
    book_id: int | None = None,
    active_only: bool = False,
    overdue_only: bool = False,
    skip: int = 0,
    limit: int = 50,
) -> list[Loan]:
    stmt = select(Loan).options(joinedload(Loan.book), joinedload(Loan.reader))
    if reader_id is not None:
        stmt = stmt.where(Loan.reader_id == reader_id)
    if book_id is not None:
        stmt = stmt.where(Loan.book_id == book_id)
    if active_only or overdue_only:
        stmt = stmt.where(Loan.return_date.is_(None))
    if overdue_only:
        stmt = stmt.where(Loan.due_date < today)
    stmt = stmt.order_by(Loan.loan_date.desc(), Loan.id.desc()).offset(skip).limit(limit)
    return list(db.scalars(stmt))


def create_loan(db: Session, data: LoanCreate, today: date) -> Loan:
    book = book_service.get_book(db, data.book_id)

    reader = db.get(User, data.reader_id)
    if reader is None:
        raise NotFoundError("Leitor não encontrado.")
    if reader.role != UserRole.READER:
        raise BusinessRuleError("Empréstimos só podem ser registrados para usuários do tipo leitor.")

    active_loans = count_active_loans_for_reader(db, reader.id)
    if active_loans >= settings.MAX_ACTIVE_LOANS:
        raise ConflictError(
            f"O leitor atingiu o limite de {settings.MAX_ACTIVE_LOANS} empréstimos simultâneos."
        )

    # Decremento condicional e atômico: evita que duas requisições simultâneas
    # emprestem o último exemplar.
    reserved = db.execute(
        update(Book)
        .where(Book.id == book.id, Book.available_quantity > 0)
        .values(available_quantity=Book.available_quantity - 1)
        .execution_options(synchronize_session=False)
    )
    if reserved.rowcount == 0:
        raise ConflictError(f"Não há exemplares disponíveis do livro '{book.title}'.")

    loan_days = data.loan_days or settings.LOAN_PERIOD_DAYS
    loan = Loan(book=book, reader=reader, loan_date=today, due_date=today + timedelta(days=loan_days))
    db.add(loan)
    db.commit()
    db.refresh(book)
    return loan


def return_loan(db: Session, loan_id: int, today: date) -> Loan:
    loan = get_loan(db, loan_id)
    if not loan.is_active:
        raise ConflictError(f"Este empréstimo já foi devolvido em {loan.return_date:%d/%m/%Y}.")

    fine = calculate_fine(loan.due_date, today, settings.DAILY_FINE)
    # A condição "return_date IS NULL" impede que a mesma devolução seja registrada duas vezes.
    returned = db.execute(
        update(Loan)
        .where(Loan.id == loan.id, Loan.return_date.is_(None))
        .values(return_date=today, fine_cents=to_cents(fine))
        .execution_options(synchronize_session=False)
    )
    if returned.rowcount == 0:
        raise ConflictError("Este empréstimo já foi devolvido.")

    db.execute(
        update(Book)
        .where(Book.id == loan.book_id)
        .values(available_quantity=Book.available_quantity + 1)
        .execution_options(synchronize_session=False)
    )
    db.commit()
    db.refresh(loan)
    return loan


def build_loan_out(loan: Loan, today: date) -> LoanOut:
    """Monta a resposta do empréstimo, incluindo situação, dias de atraso e multa."""
    if loan.is_active:
        overdue = days_overdue(loan.due_date, today)
        fine = calculate_fine(loan.due_date, today, settings.DAILY_FINE)
        status = LoanStatus.OVERDUE if overdue > 0 else LoanStatus.ACTIVE
    else:
        overdue = days_overdue(loan.due_date, loan.return_date)
        fine = from_cents(loan.fine_cents)
        status = LoanStatus.RETURNED

    return LoanOut(
        id=loan.id,
        book=BookSummary.model_validate(loan.book),
        reader=UserSummary.model_validate(loan.reader),
        loan_date=loan.loan_date,
        due_date=loan.due_date,
        return_date=loan.return_date,
        status=status,
        days_overdue=overdue,
        fine_amount=fine,
    )
