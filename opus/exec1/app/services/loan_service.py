from datetime import date, timedelta

from sqlalchemy import Select, func, select, update
from sqlalchemy.orm import Session, selectinload

from app.core.config import settings
from app.core.exceptions import BusinessRuleError, ConflictError, NotFoundError
from app.models.book import Book
from app.models.loan import Loan
from app.models.user import UserRole
from app.schemas.book import BookSummary
from app.schemas.loan import FineRead, LoanCreate, LoanRead, LoanStatus
from app.schemas.user import UserSummary
from app.services import book_service, user_service
from app.services.fine_service import calculate_days_overdue, calculate_fine


def _with_relations(stmt: Select) -> Select:
    return stmt.options(selectinload(Loan.book), selectinload(Loan.reader))


def get_loan(db: Session, loan_id: int) -> Loan:
    loan = db.scalar(_with_relations(select(Loan).where(Loan.id == loan_id)))
    if loan is None:
        raise NotFoundError("Empréstimo não encontrado", code="loan_not_found")
    return loan


def count_active_loans(db: Session, reader_id: int) -> int:
    stmt = select(func.count()).where(Loan.reader_id == reader_id, Loan.return_date.is_(None))
    return db.scalar(stmt) or 0


def create_loan(db: Session, data: LoanCreate, today: date) -> Loan:
    book = book_service.get_book(db, data.book_id)
    reader = user_service.get_user(db, data.reader_id)

    if reader.role != UserRole.READER:
        raise BusinessRuleError("Empréstimos só podem ser registrados para leitores", code="not_a_reader")

    due_date = data.due_date or today + timedelta(days=settings.loan_period_days)
    if due_date <= today:
        raise BusinessRuleError(
            "A data prevista de devolução deve ser posterior à data do empréstimo", code="invalid_due_date"
        )

    active_loans = count_active_loans(db, reader.id)
    if active_loans >= settings.max_active_loans:
        raise ConflictError(
            f"O leitor já atingiu o limite de {settings.max_active_loans} empréstimos simultâneos",
            code="loan_limit_reached",
        )

    # Decremento condicional em um único UPDATE: se duas requisições disputarem o último
    # exemplar, apenas uma delas altera a linha.
    result = db.execute(
        update(Book)
        .where(Book.id == book.id, Book.available_quantity > 0)
        .values(available_quantity=Book.available_quantity - 1)
    )
    if result.rowcount == 0:
        db.rollback()
        raise ConflictError("Não há exemplares disponíveis deste livro", code="book_unavailable")

    loan = Loan(book_id=book.id, reader_id=reader.id, loan_date=today, due_date=due_date)
    db.add(loan)
    db.commit()
    return get_loan(db, loan.id)


def return_loan(db: Session, loan_id: int, today: date) -> Loan:
    loan = get_loan(db, loan_id)
    if not loan.is_active:
        raise ConflictError("Este empréstimo já foi devolvido", code="loan_already_returned")

    fine = calculate_fine(loan.due_date, today, settings.daily_fine)
    result = db.execute(
        update(Loan).where(Loan.id == loan.id, Loan.return_date.is_(None)).values(return_date=today, fine_amount=fine)
    )
    if result.rowcount == 0:
        db.rollback()
        raise ConflictError("Este empréstimo já foi devolvido", code="loan_already_returned")

    db.execute(update(Book).where(Book.id == loan.book_id).values(available_quantity=Book.available_quantity + 1))
    db.commit()
    db.refresh(loan)
    db.refresh(loan.book)
    return loan


def list_loans(
    db: Session,
    today: date,
    *,
    reader_id: int | None = None,
    status: LoanStatus | None = None,
    overdue_only: bool = False,
    skip: int = 0,
    limit: int = 20,
) -> tuple[list[Loan], int]:
    stmt = select(Loan)
    if reader_id is not None:
        stmt = stmt.where(Loan.reader_id == reader_id)
    if status == LoanStatus.ACTIVE:
        stmt = stmt.where(Loan.return_date.is_(None))
    elif status == LoanStatus.RETURNED:
        stmt = stmt.where(Loan.return_date.is_not(None))
    if overdue_only:
        stmt = stmt.where(Loan.return_date.is_(None), Loan.due_date < today)

    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    loans = db.scalars(
        _with_relations(stmt).order_by(Loan.loan_date.desc(), Loan.id.desc()).offset(skip).limit(limit)
    ).all()
    return list(loans), total


def list_active_loans_for_reader(db: Session, reader_id: int) -> list[Loan]:
    user_service.get_user(db, reader_id)
    stmt = _with_relations(
        select(Loan).where(Loan.reader_id == reader_id, Loan.return_date.is_(None)).order_by(Loan.due_date, Loan.id)
    )
    return list(db.scalars(stmt).all())


def build_fine(loan: Loan, today: date) -> FineRead:
    reference_date = loan.return_date or today
    amount = (
        loan.fine_amount
        if loan.fine_amount is not None
        else calculate_fine(loan.due_date, reference_date, settings.daily_fine)
    )
    return FineRead(
        loan_id=loan.id,
        due_date=loan.due_date,
        reference_date=reference_date,
        days_overdue=calculate_days_overdue(loan.due_date, reference_date),
        daily_fine=settings.daily_fine,
        amount=amount,
        is_final=not loan.is_active,
    )


def build_loan_read(loan: Loan, today: date) -> LoanRead:
    fine = build_fine(loan, today)
    return LoanRead(
        id=loan.id,
        book_id=loan.book_id,
        reader_id=loan.reader_id,
        loan_date=loan.loan_date,
        due_date=loan.due_date,
        return_date=loan.return_date,
        status=LoanStatus.ACTIVE if loan.is_active else LoanStatus.RETURNED,
        days_overdue=fine.days_overdue,
        fine_amount=fine.amount,
        book=BookSummary.model_validate(loan.book),
        reader=UserSummary.model_validate(loan.reader),
    )
